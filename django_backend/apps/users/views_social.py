from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class SocialTokenExchangeView(APIView):
    """Return JWT tokens after a successful allauth social login.

    allauth completes the OAuth handshake and authenticates the user in the Django session.
    The React app then calls this endpoint to obtain JWTs.
    """

    # We rely on Django session authentication established by allauth.
    # No JWT auth is required.
    authentication_classes = []
    permission_classes = []


    def get(self, request):
        # allauth should have already logged the user in.
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(request.user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        # IMPORTANT: Do NOT place tokens in a redirect URL; return JSON to the frontend.
        return Response({"access": access, "refresh": refresh_token})


