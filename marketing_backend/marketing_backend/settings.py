"""
Django settings for marketing_backend project.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os

import dotenv
from django.utils.functional import SimpleLazyObject

dotenv.load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-production-0d8f2a1c4b6e9f3a7d5c",
)

DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".vercel.app",
    ".onrender.com",
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "storages",
    "rest_framework",
    "core",
    "business",
    "social_media",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "marketing_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "marketing_backend.wsgi.application"
ASGI_APPLICATION = "marketing_backend.asgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if os.getenv("USE_SQLITE", "true").lower() == "true":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT"),
        }
    }


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = "core.User"

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # Only for development
CORS_ALLOW_CREDENTIALS = True

# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.auth_backend.SupabaseTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Facebook OAuth settings
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
FACEBOOK_REDIRECT_URI = os.getenv(
    "FACEBOOK_REDIRECT_URI", "http://localhost:8000/api/auth/facebook/callback/"
)

# Twitter OAuth settings
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_CALLBACK_URI = os.getenv(
    "TWITTER_CALLBACK_URI", "http://localhost:8000/api/auth/twitter/callback/"
)

# LinkedIn OAuth settings
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/auth/linkedin/callback/"
)

# LLM configuration
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-r1-0528:free")

# Built on first access so management commands still run without an API key.
LLM = SimpleLazyObject(lambda: _build_llm())


def _build_llm():
    from utils.chat_openrouter import get_llm

    return get_llm(model_name=LLM_MODEL)


# Search providers
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Supabase S3-compatible storage credentials
AWS_ACCESS_KEY_ID = os.getenv("SUPABASE_S3_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("SUPABASE_S3_SECRET_KEY")
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
# Supabase ignores the region but boto3 needs one to sign the request.
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")

# Buckets
AWS_STORAGE_BUCKET_NAME = "media"
AWS_STATIC_BUCKET_NAME = "static"

USE_SUPABASE_STORAGE = bool(
    AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_ENDPOINT_URL
)

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# Also the scratch directory for documents uploaded during onboarding.
MEDIA_ROOT = os.path.join(BASE_DIR, "mediafiles")

if USE_SUPABASE_STORAGE:
    STORAGES = {
        "default": {"BACKEND": "core.storage_backends.PublicMediaStorage"},
        "staticfiles": {"BACKEND": "core.storage_backends.PublicStaticStorage"},
    }
    STATIC_URL = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/static/"
    MEDIA_URL = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/media/"
else:
    # Serve from disk so the app still runs before Supabase storage is configured.
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
    STATIC_URL = "/static/"
    MEDIA_URL = "/media/"
