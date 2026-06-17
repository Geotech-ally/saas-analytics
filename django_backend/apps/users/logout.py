from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutView(APIView):
    """Best-effort JWT logout.

    Requires the client to send a refresh token in the request body.
    We blacklist it so it can no longer be used.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            # Blacklist if blacklist app is enabled.
            # Token will have a unique jti; store it.
            # SimpleJWT BlacklistedToken expects a token instance (its jti)
            BlacklistedToken.objects.get_or_create(token=token)

        except Exception:
            # Even if token is invalid, we don't leak details.
            pass

        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)

