from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

PLATFORM_CHOICES = [
    ('twitter', 'Twitter'),
    ('instagram', 'Instagram'),
    ('facebook', 'Facebook'),
    ('linkedin', 'LinkedIn'),
]


class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if password is None:
            raise ValueError('Superuser must have a password')

        return self.create_user(email, name, password, **extra_fields)


class User(AbstractUser):
    supabase_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)

    username = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    class Meta:
        db_table = 'core_user'
        swappable = 'AUTH_USER_MODEL'


class KnowledgeBase(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        businesses = ', '.join(
            business.name for business in self.businesses_knowledge_base.all()
        )
        return f"{self.name} - {businesses}"


class SystemPrompt(models.Model):
    social_media_system_prompt = models.TextField()
    research_system_prompt = models.TextField()

    def __str__(self):
        return f"System prompt #{self.pk}"


class Business(models.Model):
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    description = models.TextField()
    logo = models.ImageField(upload_to='business_logos/', null=True, blank=True)

    facebook_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)

    website_url = models.URLField(null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)

    primary_color = models.CharField(max_length=255, null=True, blank=True, default="purple")

    knowledge_base = models.ManyToManyField(
        KnowledgeBase, related_name='businesses_knowledge_base'
    )
    knowledge_base_summary = models.TextField(null=True, blank=True)

    system_prompt = models.ForeignKey(
        SystemPrompt,
        on_delete=models.CASCADE,
        related_name='businesses_system_prompt',
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='businesses_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.created_by.name}"


class SocialMediaAccount(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name='social_accounts'
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    account_username = models.CharField(max_length=255)
    account_url = models.URLField(max_length=1000)

    # OAuth tokens and credentials, stored as a JSON blob per platform
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    platform_account_id = models.CharField(max_length=255, null=True, blank=True)
    profile_picture_url = models.URLField(null=True, blank=True, max_length=1000)

    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['business', 'platform']
        ordering = ['platform']

    def __str__(self):
        return f"{self.business.name} - {self.get_platform_display()}"
