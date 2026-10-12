from rest_framework import serializers

from core.models import Business, KnowledgeBase, SocialMediaAccount, SystemPrompt

from .models import BusinessProcessingStatus, BusinessUser


class SystemPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemPrompt
        fields = '__all__'


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = '__all__'


class BusinessUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            'name',
            'industry',
            'description',
            'website_url',
            'logo',
            'phone',
            'primary_color',
        ]


class BusinessProcessingStatusSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)

    class Meta:
        model = BusinessProcessingStatus
        fields = '__all__'


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBase
        fields = '__all__'


class BusinessUserSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'email': obj.user.email,
            'name': obj.user.name,
        }

    class Meta:
        model = BusinessUser
        fields = '__all__'


class SocialMediaAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaAccount
        # access_token/refresh_token hold live publishing credentials.
        exclude = ['access_token', 'refresh_token']
