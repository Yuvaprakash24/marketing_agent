import json
import logging

import tweepy
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.models import Business, SocialMediaAccount

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def twitter_login(request):
    """Start the Twitter OAuth 1.0a flow and cache the request token."""
    business_id = request.query_params.get('business_id')
    if not business_id:
        return Response(
            {'error': 'business_id parameter required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        oauth1_user_handler = tweepy.OAuth1UserHandler(
            settings.TWITTER_CONSUMER_KEY,
            settings.TWITTER_CONSUMER_SECRET,
            callback=settings.TWITTER_CALLBACK_URI,
        )

        try:
            redirect_url = oauth1_user_handler.get_authorization_url()
        except tweepy.errors.TweepyException as exc:
            logger.error("Error generating Twitter OAuth URL: %s", exc)
            return Response(
                {'error': f'Twitter API error: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        request_token = oauth1_user_handler.request_token['oauth_token']
        request_token_secret = oauth1_user_handler.request_token['oauth_token_secret']

        # The callback is unauthenticated, so the business is carried in the cache.
        cache.set(
            f'twitter_oauth_{request_token}',
            {
                'oauth_token_secret': request_token_secret,
                'business_id': business_id,
            },
            timeout=7200,
        )

        return Response({
            'url': redirect_url,
            'oauth_token': request_token,
            'business_id': business_id,
        })

    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error in twitter_login: %s", exc)
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def twitter_callback(request):
    """Complete the Twitter OAuth flow and store the access token pair."""
    oauth_token = request.query_params.get('oauth_token')
    oauth_verifier = request.query_params.get('oauth_verifier')

    if not oauth_token or not oauth_verifier:
        return Response(
            {'error': 'Missing oauth parameters'}, status=status.HTTP_400_BAD_REQUEST
        )

    cache_key = f'twitter_oauth_{oauth_token}'
    cached_data = cache.get(cache_key)

    if not cached_data:
        logger.error("No cached Twitter request token for %s", oauth_token)
        return Response(
            {'error': 'Authentication session expired. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    oauth_token_secret = cached_data.get('oauth_token_secret')
    business_id = cached_data.get('business_id')

    if not business_id:
        return Response(
            {'error': 'Business ID missing. Please start the connection again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        auth = tweepy.OAuth1UserHandler(
            settings.TWITTER_CONSUMER_KEY,
            settings.TWITTER_CONSUMER_SECRET,
        )
        auth.request_token = {
            'oauth_token': oauth_token,
            'oauth_token_secret': oauth_token_secret,
        }

        access_token, access_token_secret = auth.get_access_token(oauth_verifier)

        api = tweepy.API(auth)
        user = api.verify_credentials()

        business = get_object_or_404(Business, id=business_id)
        account_data = {
            'oauth_token': access_token,
            'oauth_token_secret': access_token_secret,
            'user_id': user.id_str,
            'screen_name': user.screen_name,
        }

        SocialMediaAccount.objects.update_or_create(
            business=business,
            platform='twitter',
            defaults={
                'access_token': json.dumps(account_data),
                'platform_account_id': account_data['user_id'],
                'account_username': account_data['screen_name'],
                'account_url': f"https://twitter.com/{user.screen_name}",
                'profile_picture_url': getattr(user, 'profile_image_url_https', None),
                'is_active': True,
                'last_used_at': timezone.now(),
            },
        )

        cache.delete(cache_key)

        return Response(
            {'message': 'Twitter connected successfully. Return to the app and refresh the page.'},
            status=status.HTTP_200_OK,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Error in twitter_callback: %s", exc, exc_info=True)
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
