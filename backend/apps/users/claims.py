"""Shared JWT claim helpers for Django and FastAPI authentication.

All authentication flows (password, social, service) must build claims
through these helpers so that token shape, required fields, and
revocation identifiers stay consistent across the codebase.
"""
from rest_framework_simplejwt.tokens import RefreshToken


def build_user_claims(user):
    """Return the canonical claim set for a user JWT."""
    return {
        "email": user.email,
        "role": user.role,
        "org_id": str(user.organization_id) if user.organization_id else None,
    }


def issue_user_tokens(user):
    """Create access + refresh tokens with consistent custom claims.

    Adds:
      - email, role, org_id (via build_user_claims)
      - token_type = "access" on the access token
      - jti on both tokens (provided by SimpleJWT)
      - iss / aud from settings
    """
    refresh = RefreshToken.for_user(user)
    claims = build_user_claims(user)

    for key, value in claims.items():
        refresh[key] = value
        refresh.access_token[key] = value

    refresh["token_type"] = "refresh"
    refresh.access_token["token_type"] = "access"

    from django.conf import settings
    refresh["iss"] = getattr(settings, "JWT_ISSUER", "datalens-backend")
    refresh.access_token["iss"] = getattr(settings, "JWT_ISSUER", "datalens-backend")
    refresh["aud"] = getattr(settings, "JWT_AUDIENCE", "datalens-api")
    refresh.access_token["aud"] = getattr(settings, "JWT_AUDIENCE", "datalens-api")

    return refresh.access_token, refresh


def extract_jti(token_str: str) -> str | None:
    """Decode a JWT without verification and return its jti claim."""
    import jwt
    try:
        payload = jwt.decode(token_str, options={"verify_signature": False})
        return payload.get("jti")
    except Exception:
        return None
