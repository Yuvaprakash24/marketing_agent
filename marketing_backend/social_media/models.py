from django.db import models

from core.models import PLATFORM_CHOICES, Business, SocialMediaAccount


class SocialMediaPost(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Scheduled', 'Scheduled'),
        ('Published', 'Published'),
        ('Failed', 'Failed'),
    ]

    FEEDBACK_CHOICES = [
        ('Good', 'Good'),
        ('Bad', 'Bad'),
        ('Neutral', 'Neutral'),
    ]

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name='social_media_posts'
    )
    post_text = models.TextField()
    post_images_urls = models.JSONField(default=list, blank=True)
    post_video_urls = models.JSONField(default=list, blank=True)
    posted_link = models.URLField(null=True, blank=True)
    hashtags = models.JSONField(default=list, blank=True)

    image_prompt = models.TextField(null=True, blank=True)

    post_platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    post_platform_account = models.ForeignKey(
        SocialMediaAccount,
        on_delete=models.SET_NULL,
        related_name='social_media_posts',
        null=True,
        blank=True,
    )

    # Where the research for this post came from, when research was enabled.
    source = models.CharField(max_length=100, null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)

    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='Draft')
    feedback = models.CharField(max_length=100, choices=FEEDBACK_CHOICES, default='Neutral')

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        handle = (
            f"@{self.post_platform_account.account_username}"
            if self.post_platform_account
            else self.post_platform
        )
        return f"{self.business.name} - {handle} - {self.post_text[:30]}"
