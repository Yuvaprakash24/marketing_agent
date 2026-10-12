import logging
import os
import threading
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from core.models import Business, KnowledgeBase, SocialMediaAccount, User
from core.storage_backends import PublicMediaStorage, staging_storage
from utils.ai_agents.knowledge_base_summarizer import summarize_knowledge_base
from utils.background_process.business_creation import business_background_processor

from .models import BusinessProcessingStatus, BusinessUser
from .serializers import (
    BusinessProcessingStatusSerializer,
    BusinessSerializer,
    BusinessUpdateSerializer,
    BusinessUserSerializer,
    KnowledgeBaseSerializer,
    SocialMediaAccountSerializer,
    SystemPromptSerializer,
)

logger = logging.getLogger(__name__)


def user_can_access(business, user):
    """A business is accessible to its creator and to any invited team member."""
    return (
        business.created_by_id == user.id
        or BusinessUser.objects.filter(business=business, user=user).exists()
    )


class IsBusinessOwner(BasePermission):
    """Only allow members of a business to touch its data."""

    def has_permission(self, request, view):
        business_id = request.query_params.get('business_id') or request.data.get('business_id')
        if not business_id:
            return False
        business = get_object_or_404(Business, id=business_id)
        return user_can_access(business, request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_business(request):
    """Create a business and build its knowledge base in the background."""
    try:
        business_data = {
            'name': request.POST.get('name'),
            'industry': request.POST.get('industry'),
            'description': request.POST.get('description'),
            'website_url': request.POST.get('website_url'),
            'twitter_url': request.POST.get('twitter_url', ''),
            'facebook_url': request.POST.get('facebook_url', ''),
            'instagram_url': request.POST.get('instagram_url', ''),
            'linkedin_url': request.POST.get('linkedin_url', ''),
        }

        request_id = str(uuid.uuid4())
        storage = PublicMediaStorage()

        logo_file = request.FILES.get('logo')
        if logo_file:
            business_data['logo'] = storage.save(
                f"business_logos/{request_id}_{logo_file.name}", logo_file
            )

        files = request.FILES.getlist('knowledge_base')
        logger.info("Business processing requested by user %s", request.user.id)

        request_dir = f'business_processing/{request_id}'
        os.makedirs(os.path.join(settings.MEDIA_ROOT, request_dir), exist_ok=True)

        files_data = []
        for file in files:
            file_path = os.path.join(request_dir, file.name)
            with staging_storage.open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            files_data.append({'name': file.name, 'path': file_path})

        logger.info("Staged %s knowledge base files", len(files_data))

        processing_status = BusinessProcessingStatus.objects.create(
            status='pending',
            message='Initializing processing...',
        )

        thread = threading.Thread(
            target=business_background_processor.process_business,
            kwargs={
                'request_id': processing_status.id,
                'business_data': business_data,
                'files_data': files_data,
                'user_id': request.user.id,
            },
        )
        thread.daemon = True
        thread.start()

        return Response({
            'status': 'success',
            'message': 'Business processing started',
            'request_id': processing_status.id,
        })

    except Exception as exc:  # noqa: BLE001
        logger.error("Error in process_business: %s", exc, exc_info=True)
        return Response(
            {'status': 'error', 'message': f'Error initializing processing: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_processing_status(request, request_id):
    """Poll the status of a business creation request."""
    try:
        processing_status = BusinessProcessingStatus.objects.get(id=request_id)
        serializer = BusinessProcessingStatusSerializer(processing_status)
        return Response(serializer.data)
    except BusinessProcessingStatus.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Processing status not found'},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_businesses(request):
    """Businesses the user created plus the ones they were invited to."""
    owned = Business.objects.filter(created_by=request.user)
    member_of = Business.objects.filter(businessuser__user=request.user)

    businesses = (owned | member_of).distinct().order_by('-updated_at')
    return Response(BusinessSerializer(businesses, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_business(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(BusinessSerializer(business).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_business(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = BusinessUpdateSerializer(business, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_knowledge_base(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    knowledge_base = KnowledgeBaseSerializer(business.knowledge_base.all(), many=True).data
    # Entry 0 is the rolled-up summary the post generator actually reads.
    summary = {
        'id': 0,
        'name': "Summary",
        'content': business.knowledge_base_summary,
        'created_at': business.created_at,
        'updated_at': business.updated_at,
    }
    return Response([summary, *knowledge_base])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_knowledge_base_entry(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    knowledge_base = KnowledgeBase.objects.create(
        name=request.data.get('name'),
        content=request.data.get('content'),
    )

    business.knowledge_base.add(knowledge_base)
    business.knowledge_base_summary = summarize_knowledge_base(
        business.knowledge_base.all(), business
    )
    business.save()
    return Response(KnowledgeBaseSerializer(knowledge_base).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_knowledge_base_entry(request, business_id, entry_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    knowledge_base = get_object_or_404(
        KnowledgeBase, id=entry_id, businesses_knowledge_base=business
    )
    knowledge_base.name = request.data.get('name', knowledge_base.name)
    knowledge_base.content = request.data.get('content', knowledge_base.content)
    knowledge_base.save()

    business.knowledge_base_summary = summarize_knowledge_base(
        business.knowledge_base.all(), business
    )
    business.save()
    return Response(KnowledgeBaseSerializer(knowledge_base).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_knowledge_base_entry(request, business_id, entry_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    knowledge_base = get_object_or_404(
        KnowledgeBase, id=entry_id, businesses_knowledge_base=business
    )
    knowledge_base.delete()

    business.knowledge_base_summary = summarize_knowledge_base(
        business.knowledge_base.all(), business
    )
    business.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_system_prompt(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not business.system_prompt:
        return Response({'social_media_system_prompt': '', 'research_system_prompt': ''})

    return Response(SystemPromptSerializer(business.system_prompt).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_system_prompt(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = SystemPromptSerializer(
        business.system_prompt, data=request.data, partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_business_users(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    users = BusinessUser.objects.filter(business=business)
    return Response(BusinessUserSerializer(users, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_business_user(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    user = User.objects.filter(email=request.data.get('email')).first()
    if not user:
        return Response(
            {'error': 'User not found. Please ask them to sign up first.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    _business_user, created = BusinessUser.objects.get_or_create(
        business=business,
        user=user,
        defaults={'role': request.data.get('role', 'user')},
    )
    if not created:
        return Response(
            {'error': 'User is already part of this business'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_business_user(request, business_id, user_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    business_user = get_object_or_404(BusinessUser, business=business, id=user_id)
    business_user.role = request.data.get('role', business_user.role)
    business_user.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_business_user(request, business_id, user_id):
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    business_user = get_object_or_404(BusinessUser, business=business, id=user_id)
    business_user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def get_social_media_accounts(request):
    """Connected publishing accounts for a business."""
    business_id = request.query_params.get('business_id')
    business = get_object_or_404(Business, id=business_id)
    accounts = SocialMediaAccount.objects.filter(business=business)
    return Response(SocialMediaAccountSerializer(accounts, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_logo(request, business_id):
    """Upload a business logo to Supabase storage."""
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    logo_file = request.FILES.get('logo')
    if not logo_file:
        return Response({'error': 'No logo file provided'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/svg+xml']
    if logo_file.content_type not in allowed_types:
        return Response(
            {'error': 'Invalid file type. Only JPEG, PNG, GIF, and SVG files are allowed'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    max_size = 5 * 1024 * 1024
    if logo_file.size > max_size:
        return Response(
            {'error': 'File size too large. Maximum size is 5MB'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage = PublicMediaStorage()

        file_extension = os.path.splitext(logo_file.name)[1]
        unique_filename = f"business_logos/{business_id}_{uuid.uuid4().hex}{file_extension}"

        if business.logo:
            try:
                old_logo_path = str(business.logo)
                if old_logo_path.startswith('http'):
                    old_logo_path = old_logo_path.split('/storage/v1/object/public/media/')[-1]
                if storage.exists(old_logo_path):
                    storage.delete(old_logo_path)
            except Exception as exc:  # noqa: BLE001 - a stale file should not block the upload
                logger.warning("Could not delete previous logo: %s", exc)

        saved_path = storage.save(unique_filename, logo_file)
        business.logo = saved_path
        business.save()

        return Response({
            'success': True,
            'message': 'Logo uploaded successfully',
            'logo_url': storage.url(saved_path),
            'logo_path': saved_path,
        })

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to upload logo: %s", exc, exc_info=True)
        return Response(
            {'error': f'Failed to upload logo: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_logo(request, business_id):
    """Remove a business logo from Supabase storage."""
    business = get_object_or_404(Business, id=business_id)
    if not user_can_access(business, request.user):
        return Response(
            {'error': 'You do not have access to this business'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not business.logo:
        return Response({'error': 'No logo to delete'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        storage = PublicMediaStorage()
        logo_path = str(business.logo)
        if logo_path.startswith('http'):
            logo_path = logo_path.split('/storage/v1/object/public/media/')[-1]
        if storage.exists(logo_path):
            storage.delete(logo_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not delete logo from storage: %s", exc)

    business.logo = None
    business.save()

    return Response({'success': True, 'message': 'Logo deleted successfully'})
