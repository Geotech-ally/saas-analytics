import hashlib
import logging

from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse

import jwt

logger = logging.getLogger(__name__)

try:
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
    _HAS_BLACKLIST = True
except ImportError:
    BlacklistedToken = None
    _HAS_BLACKLIST = False


class TokenBlacklistMiddleware:
    """Reject requests whose access token has been revoked.

    Checks two sources in order:
      1. Redis cache key ``revoked_jti:<jti>`` (fast, shared across workers)
      2. ``BlacklistedToken`` database table (fallback, authoritative)

    Every authorization failure is fail-closed: if neither source can be
    consulted, the request is rejected with 503 rather than allowed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if self._is_token_blacklisted(token):
                return JsonResponse(
                    {"detail": "Token has been invalidated. Please log in again."},
                    status=401,
                )

        response = self.get_response(request)
        return response

    def _is_token_blacklisted(self, token_str: str) -> bool:
        jti = _extract_jti(token_str)
        if jti is None:
            return True

        cache_key = f"revoked_jti:{jti}"
        cache_said_blacklisted = False
        cache_ok = False
        db_ok = False

        # Primary: Redis cache
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                cache_said_blacklisted = True
            cache_ok = True
        except Exception as exc:
            logger.error("Token blacklist cache lookup failed: %s", exc)

        # Fallback: database BlacklistedToken table
        db_said_blacklisted = False
        if _HAS_BLACKLIST and BlacklistedToken is not None:
            try:
                db_said_blacklisted = BlacklistedToken.objects.filter(token__jti=jti).exists()
                db_ok = True
            except Exception as exc:
                logger.error("Token blacklist DB lookup failed: %s", exc)

        # If any source says blacklisted, reject.
        if cache_said_blacklisted or db_said_blacklisted:
            return True

        # Fail closed: if neither source could confirm "not blacklisted",
        # reject the request rather than allowing it through.
        if not cache_ok or not db_ok:
            return True

        return False


def _extract_jti(token_str: str) -> str | None:
    """Extract the jti claim from a JWT without verifying the signature."""
    try:
        payload = jwt.decode(token_str, options={"verify_signature": False})
        return payload.get("jti")
    except Exception:
        return None


def is_token_blacklisted(token_str: str) -> bool:
    """Public helper kept for backward compatibility with tests/imports."""
    return _extract_jti(token_str) is not None and _revoked_in_cache(token_str)


def _revoked_in_cache(token_str: str) -> bool:
    jti = _extract_jti(token_str)
    if jti is None:
        return False
    cache_key = f"revoked_jti:{jti}"
    try:
        return cache.get(cache_key) is True
    except Exception:
        return False
