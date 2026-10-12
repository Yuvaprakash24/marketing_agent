"""URL configuration for marketing_backend project."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    """Simple health check endpoint for container healthchecks."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/auth/", include("core.urls")),
    path("api/business/", include("business.urls")),
    path("api/social-media/", include("social_media.urls")),
    path("api/health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
]
