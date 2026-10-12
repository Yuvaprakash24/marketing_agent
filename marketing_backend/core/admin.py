from django.contrib import admin

from .models import Business, KnowledgeBase, SocialMediaAccount, SystemPrompt, User

admin.site.register(User)
admin.site.register(Business)
admin.site.register(KnowledgeBase)
admin.site.register(SystemPrompt)
admin.site.register(SocialMediaAccount)
