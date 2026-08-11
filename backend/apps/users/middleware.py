from django.core.cache import cache


class TokenBlacklistMiddleware:
    """Checks if the request's JWT access token has been blacklisted.

    Looks for the token in the Authorization header and checks
    the Django cache (Redis) for a blacklist entry.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if is_token_blacklisted(token):
                from rest_framework.response import Response
                from rest_framework import status

                return Response(
                    {"detail": "Token has been invalidated. Please log in again."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        response = self.get_response(request)
        return response


def is_token_blacklisted(token_str):
    """Check if a token fingerprint exists in the blacklist cache."""
    import hashlib

    fp = hashlib.sha256(token_str.encode()).hexdigest()
    return cache.get(f"blacklisted_token:{fp}") is True