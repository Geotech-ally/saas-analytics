"""
JWT validation for FastAPI — verifies tokens issued by Django's SimpleJWT.
Django signs tokens with JWT_SIGNING_SECRET. FastAPI verifies using the same secret.
Service-to-service authentication uses FASTAPI_SERVICE_SECRET via internal JWT.
"""
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from schemas.analytics import TokenClaims

bearer_scheme = HTTPBearer()

JWT_SIGNING_SECRET = os.environ.get("JWT_SIGNING_SECRET")
if not JWT_SIGNING_SECRET:
    raise RuntimeError("JWT_SIGNING_SECRET environment variable is required.")

JWT_ALGORITHM = "HS256"
FASTAPI_SERVICE_SECRET = os.environ.get("FASTAPI_SERVICE_SECRET")
if not FASTAPI_SERVICE_SECRET:
    raise RuntimeError("FASTAPI_SERVICE_SECRET environment variable is required.")

SERVICE_TOKEN_LIFETIME_SECONDS = int(os.environ.get("SERVICE_TOKEN_LIFETIME_SECONDS", "300"))


def _decode_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(token, JWT_SIGNING_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenClaims(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> TokenClaims:
    return _decode_token(credentials.credentials)


def require_org_admin(claims: TokenClaims = Depends(get_current_user)) -> TokenClaims:
    if claims.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )
    return claims


def require_org_member(claims: TokenClaims = Depends(get_current_user)) -> TokenClaims:
    if not claims.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to an organization.",
        )
    return claims


def _make_service_token() -> str:
    """Generate a short-lived internal JWT for service-to-service auth."""
    import time

    now = int(time.time())
    payload = {
        "service_name": "django-backend",
        "iat": now,
        "exp": now + SERVICE_TOKEN_LIFETIME_SECONDS,
        "nbf": now,
    }
    return jwt.encode(payload, FASTAPI_SERVICE_SECRET, algorithm=JWT_ALGORITHM)


def verify_service_key(x_service_key: Optional[str] = None) -> bool:
    """Validates the internal service token on internal endpoints.

    Accepts either a legacy static key (for compatibility) or a JWT-signed
    service token.  The static key is read from INTERNAL_SERVICE_KEY for
    backward compatibility but is deprecated in production.
    """
    if x_service_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service key or internal token is required.",
        )

    # Check legacy static key first (backward compatibility)
    legacy_key = os.environ.get("INTERNAL_SERVICE_KEY")
    if legacy_key and x_service_key == legacy_key:
        return True

    # Verify JWT service token
    try:
        payload = jwt.decode(x_service_key, FASTAPI_SERVICE_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("service_name") != "django-backend":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid service token.",
            )
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service token expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid service token.",
        )
