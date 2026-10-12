"""Platform-specific publishing.

Every method returns a ``(post_url, error)`` tuple so callers can record either a
live permalink or the reason publishing failed, without raising.
"""

import json
import logging
import os
import tempfile
import time

import requests
import tweepy
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_API = "https://graph.facebook.com/v19.0"


class SocialMediaPoster:
    @staticmethod
    def post_to_instagram(image_urls, caption, account_data):
        """Publish to the Instagram Business account linked to the user's first page."""
        try:
            access_token = account_data.get('user_token')

            if not image_urls:
                return None, "Instagram requires at least one image for posting"

            pages_response = requests.get(
                f'{GRAPH_API}/me/accounts',
                params={
                    'access_token': access_token,
                    'fields': 'instagram_business_account,access_token',
                },
                timeout=30,
            )
            pages = pages_response.json().get('data', [])
            if not pages:
                return None, 'No connected Facebook pages found'

            page = next((p for p in pages if p.get('instagram_business_account')), None)
            if not page:
                return None, 'No page with a linked Instagram Business account was found'

            page_token = page['access_token']
            ig_account_id = page['instagram_business_account']['id']

            # Instagram publishing is a two-step flow: build a container, then publish it.
            container_response = requests.post(
                f'{GRAPH_API}/{ig_account_id}/media',
                params={
                    'access_token': page_token,
                    'image_url': image_urls[0],
                    'caption': caption,
                },
                timeout=60,
            )
            if container_response.status_code != 200:
                error = container_response.json().get('error', {}).get('message', 'Unknown error')
                logger.error("Instagram container creation failed: %s", error)
                return None, f"Container creation failed: {error}"

            container_id = container_response.json().get('id')
            if not container_id:
                return None, "No container ID returned from Instagram"

            publish_response = requests.post(
                f'{GRAPH_API}/{ig_account_id}/media_publish',
                params={'access_token': page_token, 'creation_id': container_id},
                timeout=60,
            )
            if publish_response.status_code != 200:
                error = publish_response.json().get('error', {}).get('message', 'Unknown error')
                logger.error("Instagram publishing failed: %s", error)
                return None, f"Publishing failed: {error}"

            post_id = publish_response.json().get('id')
            if not post_id:
                return None, "No post ID returned from Instagram"

            return f"https://www.instagram.com/p/{post_id}/", None

        except Exception as exc:  # noqa: BLE001
            logger.error("Instagram post error: %s", exc)
            return None, str(exc)

    @staticmethod
    def post_to_facebook_page(image_urls, caption, account_data):
        """Publish to the first Facebook Page the connected user administers."""
        try:
            access_token = account_data.get('user_token')

            pages_response = requests.get(
                f'{GRAPH_API}/me/accounts',
                params={'access_token': access_token},
                timeout=30,
            )
            if pages_response.status_code != 200:
                logger.error("Failed to list Facebook pages: %s", pages_response.text)
                return None, 'Failed to get Facebook pages'

            pages = pages_response.json().get('data', [])
            if not pages:
                return None, 'No Facebook pages found'

            page = pages[0]
            page_id = page['id']
            page_token = page['access_token']

            post_data = {'message': caption}

            if image_urls:
                # Images are uploaded unpublished, then attached to the feed post.
                photo_ids = []
                for image_url in image_urls:
                    upload_response = requests.post(
                        f"{GRAPH_API}/{page_id}/photos",
                        params={
                            'url': image_url,
                            'access_token': page_token,
                            'published': 'false',
                        },
                        timeout=60,
                    )
                    if upload_response.status_code == 200:
                        photo_ids.append(upload_response.json()['id'])
                    else:
                        logger.warning("Facebook photo upload failed: %s", upload_response.text)

                if photo_ids:
                    post_data['attached_media'] = json.dumps(
                        [{'media_fbid': pid} for pid in photo_ids]
                    )

            response = requests.post(
                f"{GRAPH_API}/{page_id}/feed",
                params={'access_token': page_token},
                data=post_data,
                timeout=60,
            )

            if response.status_code != 200:
                return None, response.json().get('error', {}).get(
                    'message', 'Facebook post failed'
                )

            return f"https://facebook.com/{response.json().get('id')}", None

        except Exception as exc:  # noqa: BLE001
            logger.error("Facebook post error: %s", exc)
            return None, str(exc)

    @staticmethod
    def post_to_linkedin(image_urls, caption, account_data):
        """Publish a UGC post, attaching the first image when one is present."""
        try:
            headers = {
                'Authorization': f'Bearer {account_data["access_token"]}',
                'LinkedIn-Version': '202402',
                'X-Restli-Protocol-Version': '2.0.0',
                'Content-Type': 'application/json',
            }

            author = account_data.get('platform_account_id')

            post_data = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": caption},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            if image_urls:
                # LinkedIn requires registering the upload, PUTting the bytes, then
                # referencing the returned asset URN on the post.
                upload_response = requests.post(
                    'https://api.linkedin.com/v2/assets?action=registerUpload',
                    headers=headers,
                    json={
                        "registerUploadRequest": {
                            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                            "owner": author,
                            "serviceRelationships": [
                                {
                                    "relationshipType": "OWNER",
                                    "identifier": "urn:li:userGeneratedContent",
                                }
                            ],
                        }
                    },
                    timeout=30,
                )

                if upload_response.status_code == 200:
                    upload_data = upload_response.json()
                    asset = upload_data['value']['asset']
                    upload_url = upload_data['value']['uploadMechanism'][
                        'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest'
                    ]['uploadUrl']

                    put_response = requests.put(
                        upload_url,
                        data=requests.get(image_urls[0], timeout=30).content,
                        headers={'Content-Type': 'image/jpeg'},
                        timeout=60,
                    )

                    if put_response.status_code == 201:
                        share_content = post_data['specificContent'][
                            'com.linkedin.ugc.ShareContent'
                        ]
                        share_content['shareMediaCategory'] = 'IMAGE'
                        share_content['media'] = [
                            {
                                "status": "READY",
                                "description": {"text": caption[:200]},
                                "media": asset,
                                "title": {"text": "Post Image"},
                            }
                        ]
                    else:
                        logger.warning(
                            "LinkedIn image upload failed (%s); posting text only",
                            put_response.status_code,
                        )
                else:
                    logger.warning(
                        "LinkedIn registerUpload failed: %s; posting text only",
                        upload_response.text,
                    )

            response = requests.post(
                'https://api.linkedin.com/v2/ugcPosts',
                headers=headers,
                json=post_data,
                timeout=60,
            )

            if response.status_code not in (200, 201):
                return None, response.json().get('message', 'LinkedIn post failed')

            return f"https://linkedin.com/feed/update/{response.json().get('id')}/", None

        except Exception as exc:  # noqa: BLE001
            logger.error("LinkedIn post error: %s", exc)
            return None, str(exc)

    @staticmethod
    def post_to_twitter(media_urls, media_type, caption, account_data):
        """Publish a tweet, uploading up to four media items first."""
        temp_files = []
        try:
            oauth_token = account_data.get('oauth_token')
            oauth_token_secret = account_data.get('oauth_token_secret')
            screen_name = account_data.get('screen_name')

            if not oauth_token or not oauth_token_secret:
                return None, "Twitter credentials are missing. Please reconnect your account."

            auth = tweepy.OAuth1UserHandler(
                consumer_key=settings.TWITTER_CONSUMER_KEY,
                consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                access_token=oauth_token,
                access_token_secret=oauth_token_secret,
            )

            # v1.1 handles media uploads; v2 creates the tweet.
            api = tweepy.API(auth)

            try:
                api.verify_credentials()
            except tweepy.errors.Unauthorized:
                return None, "Twitter authentication failed. Please reconnect your account."
            except tweepy.errors.TweepyException as exc:
                return None, f"Twitter error: {exc}"

            client = tweepy.Client(
                consumer_key=settings.TWITTER_CONSUMER_KEY,
                consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                access_token=oauth_token,
                access_token_secret=oauth_token_secret,
            )

            media_ids = []
            is_video = bool(media_type) and media_type.lower() in ('video', 'animated_gif')

            for media_url in (media_urls or [])[:4]:
                try:
                    media_response = requests.get(media_url, timeout=30)
                    if media_response.status_code != 200:
                        logger.error(
                            "Failed to download media %s (status %s)",
                            media_url,
                            media_response.status_code,
                        )
                        continue

                    suffix = '.mp4' if is_video else '.jpg'
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    temp_files.append(temp_file.name)
                    with temp_file:
                        temp_file.write(media_response.content)
                        temp_file.flush()

                    if is_video:
                        media = api.media_upload(
                            filename=temp_file.name,
                            media_category=(
                                'tweet_video' if media_type.lower() == 'video' else 'tweet_gif'
                            ),
                        )
                        # Video needs server-side processing before it can be attached.
                        upload_status = api.get_media_upload_status(media.media_id)
                        while (
                            upload_status.processing_info
                            and upload_status.processing_info['state']
                            in ('pending', 'in_progress')
                        ):
                            time.sleep(upload_status.processing_info.get('check_after_secs', 3))
                            upload_status = api.get_media_upload_status(media.media_id)
                    else:
                        media = api.media_upload(filename=temp_file.name)

                    media_ids.append(media.media_id)
                except Exception as exc:  # noqa: BLE001 - skip one bad asset, keep the rest
                    logger.error("Error processing media %s: %s", media_url, exc)
                    continue

            try:
                if media_ids:
                    response = client.create_tweet(text=caption, media_ids=media_ids)
                else:
                    response = client.create_tweet(text=caption)

                tweet_id = response.data['id']
                return f"https://twitter.com/{screen_name}/status/{tweet_id}", None

            except tweepy.errors.BadRequest as exc:
                return None, f"Twitter rejected this post: {exc}"
            except tweepy.errors.Unauthorized:
                return None, "Twitter authorization error. Please reconnect your account."
            except tweepy.errors.Forbidden:
                return None, "Twitter refused this post. Please check your content and try again."
            except tweepy.errors.TooManyRequests:
                return None, "Twitter rate limit exceeded. Please try again later."
            except tweepy.errors.TweepyException as exc:
                return None, f"Twitter API error: {exc}"

        except Exception as exc:  # noqa: BLE001
            logger.error("Twitter post error: %s", exc)
            return None, f"Twitter posting error: {exc}"
        finally:
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except OSError:
                    pass
