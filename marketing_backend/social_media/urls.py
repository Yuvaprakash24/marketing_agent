from django.urls import path

from . import views

urlpatterns = [
    path('social-media-posts/', views.get_social_media_posts, name='get_social_media_posts'),
    path(
        'social-media-posts/create/',
        views.create_social_media_post,
        name='create_social_media_post',
    ),
    path('post-creation-status/', views.get_post_creation_status, name='get_post_creation_status'),

    path('generate-ai-image/', views.generate_ai_image, name='generate_ai_image'),

    path(
        'social-media-accounts/',
        views.get_social_media_accounts,
        name='get_social_media_accounts',
    ),
    path(
        'posts/<int:post_id>/publish/',
        views.publish_social_media_post,
        name='publish_social_media_post',
    ),
    path(
        'social-media-posts/delete/<int:post_id>/',
        views.delete_social_media_post,
        name='delete_social_media_post',
    ),
    path(
        'social-media-posts/update/<int:post_id>/',
        views.update_social_media_post,
        name='update_social_media_post',
    ),
    path(
        'social-media-posts/<int:post_id>/',
        views.get_social_media_post,
        name='get_social_media_post',
    ),
]
