"""Custom JWT authentication for Django REST Framework.

Extends SimpleJWT's JWTAuthentication to enforce that only access tokens
(not refresh tokens) are accepted on API endpoints.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken


class AccessTokenOnlyAuthentication(JWTAuthentication):
    """Accept only access tokens; reject refresh tokens."""

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        token_type = token.get("token_type")
        if token_type != "access":
            raise InvalidToken("Access token required.")
        return token
