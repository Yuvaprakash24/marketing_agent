import json
import logging

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.models import Business, SocialMediaAccount

logger = logging.getLogger(__name__)

LINKEDIN_API_URL = "https://api.linkedin.com/v2"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def linkedin_login(request):
    """Generate the LinkedIn OAuth URL for a business."""
    business_id = request.query_params.get('business_id')
    if not business_id:
        return Response(
            {'error': 'business_id parameter required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    params = {
        'response_type': 'code',
        'client_id': settings.LINKEDIN_CLIENT_ID,
        'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
        'state': business_id,
        'scope': 'openid profile email w_member_social',
    }
    oauth_url = (
        'https://www.linkedin.com/oauth/v2/authorization?'
        f"{'&'.join(f'{k}={v}' for k, v in params.items())}"
    )
    return Response({'url': oauth_url})


@api_view(['GET'])
@permission_classes([AllowAny])
def linkedin_callback(request):
    """Handle the LinkedIn OAuth callback and store the posting credentials."""
    code = request.query_params.get('code')
    business_id = request.query_params.get('state')

    if not code or not business_id:
        return Response(
            {'error': 'Missing code or state parameter'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token_response = requests.post(
            'https://www.linkedin.com/oauth/v2/accessToken',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
                'client_id': settings.LINKEDIN_CLIENT_ID,
                'client_secret': settings.LINKEDIN_CLIENT_SECRET,
            },
            timeout=30,
        )
        token_data = token_response.json()

        if 'error' in token_data:
            return Response(
                {'error': token_data.get('error_description', token_data['error'])},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 0)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        userinfo_response = requests.get(
            f'{LINKEDIN_API_URL}/userinfo', headers=headers, timeout=30
        )
        userinfo_data = userinfo_response.json()

        if not userinfo_data.get('sub'):
            return Response(
                {'error': 'Failed to get user info'}, status=status.HTTP_400_BAD_REQUEST
            )

        # Prefer posting as an organization when the member administers one.
        platform_account_id = None
        try:
            org_response = requests.get(
                f'{LINKEDIN_API_URL}/organizationalEntityAcls?q=roleAssignee',
                headers=headers,
                timeout=30,
            )
            org_data = org_response.json()
            if org_data.get('elements'):
                platform_account_id = org_data['elements'][0].get('organizationalTarget')
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not read LinkedIn organizations: %s", exc)

        if not platform_account_id:
            platform_account_id = f"urn:li:person:{userinfo_data['sub']}"

        account_data = {
            'access_token': access_token,
            'expires_in': expires_in,
            'user_id': userinfo_data['sub'],
            'user_name': userinfo_data.get('name'),
            'user_email': userinfo_data.get('email'),
            'platform_account_id': platform_account_id,
            'given_name': userinfo_data.get('given_name'),
            'family_name': userinfo_data.get('family_name'),
            'locale': userinfo_data.get('locale'),
            'email_verified': userinfo_data.get('email_verified', False),
        }

        business = get_object_or_404(Business, id=business_id)

        SocialMediaAccount.objects.update_or_create(
            business=business,
            platform='linkedin',
            defaults={
                'access_token': json.dumps(account_data),
                # LinkedIn does not issue a separate refresh token for this scope set.
                'refresh_token': access_token,
                'platform_account_id': platform_account_id,
                'account_username': userinfo_data.get('name'),
                'account_url': f"https://www.linkedin.com/in/{userinfo_data['sub']}/",
                'profile_picture_url': userinfo_data.get('picture'),
                'token_expires_at': timezone.now() + timezone.timedelta(seconds=expires_in),
                'is_active': True,
                'last_used_at': timezone.now(),
            },
        )

        return Response(
            {'message': 'LinkedIn connected successfully. Return to the app and refresh the page.'},
            status=status.HTTP_200_OK,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Error in linkedin_callback: %s", exc, exc_info=True)
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
