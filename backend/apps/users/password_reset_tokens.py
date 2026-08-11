"""Token utilities for password reset.

Features:
- Cryptographically secure token generation
- Hashed token storage (never store raw tokens)
- Short expiration (<= 15 minutes)
- Single-use enforcement
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

TOKEN_BYTES = 32
TOKEN_HASH_ALGORITHM = "sha256"
RESET_TOKEN_TTL = timedelta(minutes=15)


def generate_secure_token() -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for safe storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_is_expired(created_at) -> bool:
    """Check if a token has expired based on TTL."""
    expiry_time = created_at + RESET_TOKEN_TTL
    return timezone.now() > expiry_time

