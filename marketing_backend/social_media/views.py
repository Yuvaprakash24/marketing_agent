import json
import logging
import threading

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from business.views import IsBusinessOwner
from core.models import Business, SocialMediaAccount
from social_media.serializers import (
    SocialMediaAccountSerializer,
    SocialMediaPostEditSerializer,
    SocialMediaPostSerializer,
)
from utils.ai_agents.social_media_post_creator import SocialMediaPostCreator
from utils.image_gen import AiImageGen

from .models import SocialMediaPost
from .posting import SocialMediaPoster

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ('facebook', 'instagram', 'twitter', 'linkedin')


def combine_post_text_with_hashtags(post_text: str, hashtags: list) -> str:
    """Hashtags are stored separately so they can be edited; publishing needs them inline."""
    if not hashtags:
        return post_text

    hashtag_str = ' '.join(f"#{str(tag).lstrip('#')}" for tag in hashtags)

    if post_text and not post_text.endswith((' ', '\n')):
        return f"{post_text}\n\n{hashtag_str}"
    return f"{post_text}{hashtag_str}"


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def get_social_media_posts(request):
    """All posts for a business, newest first."""
    business_id = request.query_params.get('business_id')
    business = get_object_or_404(Business, id=business_id)
    posts = SocialMediaPost.objects.filter(business=business, is_deleted=False)
    return Response(SocialMediaPostSerializer(posts, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def create_social_media_post(request):
    """Kick off AI post generation in the background and return immediately."""
    business_id = request.data.get('business_id')
    topic = request.data.get('topic')
    platform = request.data.get('platform')
    num_posts = request.data.get('num_posts', 1)
    is_research_needed = request.data.get('is_research_needed', True)

    if not topic or not platform:
        return Response(
            {'error': 'topic and platform are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if platform.lower() not in SUPPORTED_PLATFORMS:
        return Response(
            {'error': f"Unsupported platform. Supported: {', '.join(SUPPORTED_PLATFORMS)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        num_posts = max(1, min(10, int(num_posts)))
    except (TypeError, ValueError):
        return Response(
            {'error': 'num_posts must be a number between 1 and 10'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    business = get_object_or_404(Business, id=business_id)
    post_creator = SocialMediaPostCreator(business)

    # Generation calls an LLM once per post plus an image model, so it cannot
    # finish inside the request. The client polls post-creation-status instead.
    thread = threading.Thread(
        target=post_creator.create_posts,
        args=(topic, num_posts, platform, is_research_needed),
    )
    thread.daemon = True
    thread.start()

    return Response(
        {
            'message': 'Social media post creation started',
            'business_id': business_id,
            'topic': topic,
            'platform': platform,
            'num_posts': num_posts,
            'status': 'processing',
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def get_post_creation_status(request):
    """Report posts created in the last hour so the UI can show generation results."""
    business_id = request.query_params.get('business_id')
    business = get_object_or_404(Business, id=business_id)

    recent_time = timezone.now() - timezone.timedelta(hours=1)
    recent_posts = SocialMediaPost.objects.filter(
        business=business,
        is_deleted=False,
        created_at__gte=recent_time,
    )

    if recent_posts.exists():
        return Response({
            'status': 'completed',
            'recent_posts': SocialMediaPostSerializer(recent_posts, many=True).data,
            'count': recent_posts.count(),
        })

    return Response({
        'status': 'no_recent_posts',
        'message': 'No posts created in the last hour',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def publish_social_media_post(request, post_id):
    """Publish a draft post to its platform and record the permalink."""
    business = get_object_or_404(Business, id=request.query_params.get('business_id'))
    post = get_object_or_404(SocialMediaPost, id=post_id, business=business)

    platform = post.post_platform.lower()

    # Instagram publishing runs through the connected Facebook page.
    account_platform = 'facebook' if platform == 'instagram' else platform

    account = SocialMediaAccount.objects.filter(
        platform=account_platform, business=business, is_active=True
    ).first()
    if not account or not account.access_token:
        return Response(
            {'error': f'No {account_platform} account connected for this business'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        account_data = json.loads(account.access_token)
    except (TypeError, ValueError):
        return Response(
            {'error': f'Stored {account_platform} credentials are invalid. Please reconnect.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    full_post_text = combine_post_text_with_hashtags(post.post_text, post.hashtags)

    try:
        if platform == 'facebook':
            post_url, error = SocialMediaPoster.post_to_facebook_page(
                post.post_images_urls, full_post_text, account_data
            )
        elif platform == 'instagram':
            post_url, error = SocialMediaPoster.post_to_instagram(
                post.post_images_urls, full_post_text, account_data
            )
        elif platform == 'linkedin':
            post_url, error = SocialMediaPoster.post_to_linkedin(
                post.post_images_urls, full_post_text, account_data
            )
        elif platform == 'twitter':
            if post.post_video_urls:
                post_url, error = SocialMediaPoster.post_to_twitter(
                    post.post_video_urls, 'video', full_post_text, account_data
                )
            else:
                post_url, error = SocialMediaPoster.post_to_twitter(
                    post.post_images_urls, 'image', full_post_text, account_data
                )
        else:
            return Response(
                {'error': 'Unsupported platform'}, status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Error publishing post %s: %s", post.id, exc, exc_info=True)
        post.status = 'Failed'
        post.save(update_fields=['status', 'updated_at'])
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if error:
        logger.error("Publishing post %s to %s failed: %s", post.id, platform, error)
        post.status = 'Failed'
        post.save(update_fields=['status', 'updated_at'])
        return Response({'error': error}, status=status.HTTP_502_BAD_GATEWAY)

    post.status = 'Published'
    post.posted_link = post_url
    post.post_platform_account = account
    post.save(update_fields=['status', 'posted_link', 'post_platform_account', 'updated_at'])

    account.last_used_at = timezone.now()
    account.save(update_fields=['last_used_at', 'updated_at'])

    return Response({
        'message': 'Post published successfully',
        'platform': platform,
        'post_url': post.posted_link,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def get_social_media_accounts(request):
    """Connected publishing accounts for a business."""
    business_id = request.query_params.get('business_id')
    business = get_object_or_404(Business, id=business_id)
    accounts = SocialMediaAccount.objects.filter(business=business)
    return Response(SocialMediaAccountSerializer(accounts, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def get_social_media_post(request, post_id):
    business = get_object_or_404(Business, id=request.query_params.get('business_id'))
    post = get_object_or_404(SocialMediaPost, id=post_id, business=business)
    return Response(SocialMediaPostSerializer(post).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def update_social_media_post(request, post_id):
    """Edit copy, hashtags, images or feedback on a post."""
    business = get_object_or_404(Business, id=request.query_params.get('business_id'))
    post = get_object_or_404(SocialMediaPost, id=post_id, business=business)

    serializer = SocialMediaPostEditSerializer(post, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsBusinessOwner])
def delete_social_media_post(request, post_id):
    business = get_object_or_404(Business, id=request.query_params.get('business_id'))
    post = get_object_or_404(SocialMediaPost, id=post_id, business=business)

    post.delete()
    return Response({'message': 'Social media post deleted successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_ai_image(request):
    """Generate a post image from a prompt and return its public URL."""
    prompt = request.data.get('prompt')
    if not prompt:
        return Response({'error': 'prompt is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        image_url = AiImageGen().generate_image(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.error("AI image generation failed: %s", exc)
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not image_url:
        return Response(
            {'error': 'Image generation did not return an image'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({'image_url': image_url})
