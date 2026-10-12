from django.urls import path

from . import views
from .social_oauth import facebook, linkedin, twitter

urlpatterns = [
    path('login/', views.login_user, name='login_user'),
    path('supabase/', views.supabase_auth, name='supabase_auth'),
    path('refresh/', views.refresh_token, name='refresh_token'),
    path('logout/', views.logout_user, name='logout_user'),
    path('profile/', views.get_user_profile, name='user_profile'),

    path('linkedin/login/', linkedin.linkedin_login, name='linkedin-login'),
    path('linkedin/callback/', linkedin.linkedin_callback, name='linkedin-callback'),
    path('facebook/login/', facebook.facebook_login, name='facebook-login'),
    path('facebook/callback/', facebook.facebook_callback, name='facebook-callback'),
    path('twitter/login/', twitter.twitter_login, name='twitter-login'),
    path('twitter/callback/', twitter.twitter_callback, name='twitter-callback'),
]
