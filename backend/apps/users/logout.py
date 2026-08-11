import hashlib

from django.core.cache import cache
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

CACHE_KEY_PREFIX = "blacklisted_token:"
CACHE_TTL = 60 * 60 * 24 * 30  # 30 days (max token lifetime)


def _token_fingerprint(token_str: str) -> str:
    return hashlib.sha256(token_str.encode()).hexdigest()


def _blacklist_token(token_str: str) -> None:
    fp = _token_fingerprint(token_str)
    ttl = CACHE_TTL
    cache.set(f"{CACHE_KEY_PREFIX}{fp}", True, timeout=ttl)


def _is_token_blacklisted(token_str: str) -> bool:
    fp = _token_fingerprint(token_str)
    return cache.get(f"{CACHE_KEY_PREFIX}{fp}") is True


class LogoutView(APIView):
    """Secure JWT logout with token blacklisting."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        access_token = request.data.get("access")

        if not refresh_token and not access_token:
            return Response(
                {"detail": "At least one of refresh or access token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Blacklist the refresh token
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                _blacklist_token(str(token))
            except Exception:
                pass

        # Blacklist the access token
        if access_token:
            _blacklist_token(access_token)

        # Flush Django session if one exists
        if request.user and request.user.is_authenticated:
            request.session.flush()

        return Response(
            {"detail": "Logged out. All tokens invalidated."},
            status=status.HTTP_200_OK,
        )


def is_token_blacklisted(token_str: str) -> bool:
    """Check if a token has been blacklisted (for middleware use)."""
    return _is_token_blacklisted(token_str)

