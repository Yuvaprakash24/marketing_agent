import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .supabase_config import supabase

logger = logging.getLogger(__name__)

User = get_user_model()


class SupabaseAuthBackend(BaseBackend):
    def authenticate(self, request, token=None):
        if not token:
            return None

        try:
            user_data = supabase.auth.get_user(token).user

            if not user_data:
                return None

            user, _created = User.objects.get_or_create(
                supabase_id=user_data.id,
                defaults={
                    'email': user_data.email,
                    'name': user_data.user_metadata.get('name', ''),
                },
            )

            return user

        except Exception as exc:  # noqa: BLE001 - surfaced to the caller as "no user"
            logger.warning("Supabase token verification failed: %s", exc)
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class SupabaseTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            # Expected format: "Bearer <token>"
            auth_parts = auth_header.split()
            if len(auth_parts) != 2 or auth_parts[0].lower() != 'bearer':
                return None

            token = auth_parts[1]

            auth_backend = SupabaseAuthBackend()
            user = auth_backend.authenticate(request, token)

            if user:
                return (user, token)
            return None

        except Exception as exc:  # noqa: BLE001
            raise AuthenticationFailed('Invalid token') from exc
