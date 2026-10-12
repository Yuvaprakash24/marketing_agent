from django.contrib.auth import login, logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .auth_backend import SupabaseAuthBackend
from .supabase_config import supabase


@api_view(['POST'])
@permission_classes([AllowAny])
def supabase_auth(request):
    token = request.data.get('token')
    if not token:
        return Response({'error': 'No token provided'}, status=status.HTTP_400_BAD_REQUEST)

    auth_backend = SupabaseAuthBackend()
    user = auth_backend.authenticate(request, token)

    if user:
        login(request, user)
        return Response({
            'message': 'Authentication successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
            },
        })

    return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_token(request):
    try:
        token = request.data.get('refresh_token')
        if not token:
            return Response(
                {'error': 'No refresh token provided'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = supabase.auth.refresh_session(token)

        return Response({
            'access_token': session.access_token,
            'refresh_token': session.refresh_token,
            'expires_at': session.expires_at,
        })

    except Exception as exc:  # noqa: BLE001
        return Response({'error': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    try:
        logout(request)
        return Response({'message': 'Successfully logged out'})
    except Exception as exc:  # noqa: BLE001
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    return Response({
        'id': request.user.id,
        'email': request.user.email,
        'name': request.user.name,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        auth_response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password,
        })

        if not auth_response or not auth_response.user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        auth_backend = SupabaseAuthBackend()
        user = auth_backend.authenticate(request, auth_response.session.access_token)

        if user:
            login(request, user)
            return Response({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                },
                'tokens': {
                    'access_token': auth_response.session.access_token,
                    'refresh_token': auth_response.session.refresh_token,
                    'expires_at': auth_response.session.expires_at,
                },
            })

        return Response(
            {'error': 'Failed to create/update user'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    except Exception as exc:  # noqa: BLE001
        return Response({'error': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
