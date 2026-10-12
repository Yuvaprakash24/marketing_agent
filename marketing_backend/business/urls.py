from django.urls import path

from . import views

urlpatterns = [
    path('process/', views.process_business, name='process_business'),
    path(
        'process/status/<uuid:request_id>/',
        views.get_processing_status,
        name='get_processing_status',
    ),
    path('', views.get_all_businesses, name='get_all_businesses'),
    path('social-media-accounts/', views.get_social_media_accounts, name='get_social_media_accounts'),

    path('<int:business_id>/', views.get_business, name='get_business'),
    path('<int:business_id>/update/', views.update_business, name='update_business'),
    path('<int:business_id>/logo/', views.upload_logo, name='upload_logo'),
    path('<int:business_id>/logo/delete/', views.delete_logo, name='delete_logo'),

    path('knowledge-base/<int:business_id>/', views.get_knowledge_base, name='get_knowledge_base'),
    path(
        'knowledge-base/<int:business_id>/add/',
        views.add_knowledge_base_entry,
        name='add_knowledge_base_entry',
    ),
    path(
        'knowledge-base/<int:business_id>/edit/<int:entry_id>/',
        views.edit_knowledge_base_entry,
        name='edit_knowledge_base_entry',
    ),
    path(
        'knowledge-base/<int:business_id>/delete/<int:entry_id>/',
        views.delete_knowledge_base_entry,
        name='delete_knowledge_base_entry',
    ),

    path('system-prompt/<int:business_id>/', views.get_system_prompt, name='get_system_prompt'),
    path(
        'system-prompt/<int:business_id>/update/',
        views.update_system_prompt,
        name='update_system_prompt',
    ),

    path('business-user/<int:business_id>/', views.get_business_users, name='get_business_users'),
    path(
        'business-user/<int:business_id>/add/',
        views.add_business_user,
        name='add_business_user',
    ),
    path(
        'business-user/<int:business_id>/edit/<int:user_id>/',
        views.edit_business_user,
        name='edit_business_user',
    ),
    path(
        'business-user/<int:business_id>/delete/<int:user_id>/',
        views.delete_business_user,
        name='delete_business_user',
    ),
]
