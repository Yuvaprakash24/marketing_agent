from rest_framework import serializers

from core.models import SocialMediaAccount
from social_media.models import SocialMediaPost


class SocialMediaPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaPost
        fields = [
            'id',
            'post_text',
            'post_images_urls',
            'post_video_urls',
            'posted_link',
            'hashtags',
            'image_prompt',
            'post_platform',
            'source',
            'source_url',
            'status',
            'feedback',
            'is_deleted',
            'created_at',
            'updated_at',
        ]


class SocialMediaPostEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaPost
        fields = ['post_text', 'hashtags', 'feedback', 'image_prompt', 'post_images_urls']

    def validate_hashtags(self, value):
        """Hashtags are stored bare; the '#' is added when a post is published."""
        return [str(tag).lstrip('#').strip() for tag in value if str(tag).strip('# ')]


class SocialMediaAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaAccount
        exclude = ['access_token', 'refresh_token']
