import logging

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .claims import extract_jti

logger = logging.getLogger(__name__)


class LogoutView(APIView):
    """JWT logout.

    Requires the client to send a refresh token in the request body.
    Optionally accepts an ``access`` token to revoke the current session
    immediately rather than waiting for the short-lived access token to
    expire.

    Revocation works by storing each token's ``jti`` in Redis.  The
    ``TokenBlacklistMiddleware`` then rejects any request presenting a
    revoked ``jti``.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        access_token = request.data.get("access")

        if not refresh_token and not access_token:
            return Response(
                {"detail": "Refresh token or access token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        revoked_jtis = set()

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                jti = token.get("jti")
                if jti:
                    revoked_jtis.add(jti)
                token.blacklist()
            except TokenError:
                pass
            except Exception:
                logger.exception("Unexpected error blacklisting refresh token on logout.")
                return Response(
                    {"detail": "Could not process logout. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        if access_token:
            jti = extract_jti(access_token)
            if jti:
                revoked_jtis.add(jti)

        if revoked_jtis:
            self._store_revoked_jtis(revoked_jtis)

        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)

    def _store_revoked_jtis(self, jtis):
        """Persist revoked jti values in Redis with a safe TTL."""
        try:
            from django.core.cache import cache
            for jti in jtis:
                cache.set(f"revoked_jti:{jti}", True, timeout=60 * 60 * 24 * 7)
        except Exception:
            logger.exception("Failed to persist revoked jti values in cache.")
