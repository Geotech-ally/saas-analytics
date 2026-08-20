import logging
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .claims import issue_user_tokens

logger = logging.getLogger(__name__)

User = get_user_model()


class SocialTokenExchangeView(APIView):
    """Return JWT tokens after a successful social OAuth login.

    Accepts a Google OAuth access_token (POST) or, for backward
    compatibility, returns tokens for an allauth-session-authenticated
    user (GET).  Designed for decoupled SPAs that obtain a Google token
    on the frontend and exchange it here for JWTs.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request: HttpRequest):
        # Backward-compatible path: caller already has a Django session.
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Not authenticated."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return self._issue_tokens(request.user)

    def post(self, request: HttpRequest):
        """Exchange a Google OAuth access token for JWTs.

        The frontend sends the Google OAuth token obtained via the Google
        Identity Services SDK (or equivalent).  This view verifies the token
        against Google's tokeninfo endpoint, finds or creates the matching
        Django user, and returns access + refresh JWTs.
        """
        access_token = request.data.get("access_token")
        if not access_token:
            return Response(
                {"detail": "access_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = self._verify_google_token(access_token)
        if user is None:
            return Response(
                {"detail": "Invalid Google token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return self._issue_tokens(user)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _issue_tokens(self, user: User) -> Response:
        if not user.is_active:
            return Response(
                {"detail": "Account is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        access, refresh = issue_user_tokens(user)
        return Response(
            {
                "access": str(access),
                "refresh": str(refresh),
            },
        )

    def _verify_google_token(self, access_token: str):
        """Verify a Google OAuth token and return the matching User."""
        try:
            import requests

            # Verify the token with Google's tokeninfo endpoint.
            resp = requests.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
                timeout=10,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.warning("Google token verification failed: %s", exc)
            return None

        google_sub = payload.get("sub")
        email = payload.get("email")
        if not google_sub or not email:
            return None

        # Try to find an existing SocialAccount for this Google user.
        from allauth.socialaccount.models import SocialAccount

        try:
            social_account = SocialAccount.objects.get(
                provider="google",
                uid=google_sub,
            )
            return social_account.user
        except SocialAccount.DoesNotExist:
            pass

        # Fall back to finding a user by email (first‑party registered users
        # that later linked their Google account, or users imported via
        # allauth's auto-signup that stored the email match).
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None