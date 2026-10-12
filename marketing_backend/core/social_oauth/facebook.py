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

# Scopes needed to list pages and publish to a page feed (and Instagram via the page).
FACEBOOK_SCOPES = (
    'email,public_profile,pages_show_list,business_management,'
    'pages_read_engagement,pages_manage_posts'
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def facebook_login(request):
    """Generate the Facebook OAuth URL for a business."""
    business_id = request.query_params.get('business_id')
    if not business_id:
        return Response(
            {'error': 'business_id parameter required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    base_url = 'https://www.facebook.com/v19.0/dialog/oauth'
    params = {
        'client_id': settings.FACEBOOK_APP_ID,
        'redirect_uri': settings.FACEBOOK_REDIRECT_URI,
        'state': business_id,
        'scope': FACEBOOK_SCOPES,
        'response_type': 'code',
    }
    oauth_url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    return Response({'url': oauth_url})


@api_view(['GET'])
@permission_classes([AllowAny])
def facebook_callback(request):
    """Handle the Facebook OAuth callback and store the long-lived token."""
    code = request.query_params.get('code')
    business_id = request.query_params.get('state')

    if not code or not business_id:
        return Response(
            {'error': 'Missing code or state parameter'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # 1. Exchange the code for a short-lived access token.
        token_response = requests.get(
            'https://graph.facebook.com/v19.0/oauth/access_token',
            params={
                'client_id': settings.FACEBOOK_APP_ID,
                'client_secret': settings.FACEBOOK_APP_SECRET,
                'redirect_uri': settings.FACEBOOK_REDIRECT_URI,
                'code': code,
            },
            timeout=30,
        )
        token_data = token_response.json()

        if 'error' in token_data:
            logger.error("Facebook token exchange failed: %s", token_data['error'])
            return Response(
                {'error': token_data['error']['message']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in')

        # 2. Swap it for a long-lived token so publishing keeps working.
        long_token_response = requests.get(
            'https://graph.facebook.com/v19.0/oauth/access_token',
            params={
                'grant_type': 'fb_exchange_token',
                'client_id': settings.FACEBOOK_APP_ID,
                'client_secret': settings.FACEBOOK_APP_SECRET,
                'fb_exchange_token': access_token,
            },
            timeout=30,
        )
        long_access_token = long_token_response.json()['access_token']

        # 3. Fetch the profile the token belongs to.
        user_response = requests.get(
            'https://graph.facebook.com/v19.0/me',
            params={'access_token': long_access_token, 'fields': 'id,name,email'},
            timeout=30,
        )
        user_data = user_response.json()

        picture_response = requests.get(
            f"https://graph.facebook.com/v19.0/{user_data['id']}/picture",
            params={
                'access_token': long_access_token,
                'redirect': 'false',
                'type': 'large',
            },
            timeout=30,
        )
        picture_data = picture_response.json()

        business = get_object_or_404(Business, id=business_id)
        account_data = {
            'user_token': long_access_token,
            'token_expiry': expires_in,
            'user_id': user_data['id'],
            'user_name': user_data['name'],
            'user_email': user_data.get('email'),
        }

        social_account, created = SocialMediaAccount.objects.update_or_create(
            business=business,
            platform='facebook',
            defaults={
                'access_token': json.dumps(account_data),
                'refresh_token': long_access_token,
                'platform_account_id': user_data['id'],
                'account_username': user_data['name'],
                'account_url': f"https://www.facebook.com/{user_data['id']}",
                'profile_picture_url': picture_data.get('data', {}).get('url'),
                'token_expires_at': (
                    timezone.now() + timezone.timedelta(seconds=int(expires_in))
                    if expires_in
                    else None
                ),
                'is_active': True,
                'last_used_at': timezone.now(),
            },
        )
        logger.info(
            "Facebook account %s for business %s",
            'created' if created else 'updated',
            social_account.id,
        )

        return Response(
            {'message': 'Facebook connected successfully. Return to the app and refresh the page.'},
            status=status.HTTP_200_OK,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Error in facebook_callback: %s", exc, exc_info=True)
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
