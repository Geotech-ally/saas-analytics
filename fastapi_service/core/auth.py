"""
JWT validation for FastAPI — verifies tokens issued by Django's SimpleJWT.
Django signs tokens with JWT_SIGNING_SECRET. FastAPI verifies using the same secret.
Service-to-service authentication uses FASTAPI_SERVICE_SECRET via internal JWT.
"""
import os
from typing import Optional

import jwt
import redis
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

JWT_ISSUER = os.environ.get("JWT_ISSUER", "datalens-backend")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "datalens-api")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis_client = None

SERVICE_TOKEN_LIFETIME_SECONDS = int(os.environ.get("SERVICE_TOKEN_LIFETIME_SECONDS", "300"))


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Revocation service unavailable.",
            )
    return _redis_client


def _is_jti_revoked(jti: str) -> bool:
    """Check whether a token jti has been revoked in Redis."""
    if not jti:
        return False
    try:
        client = _get_redis()
        return client.get(f"revoked_jti:{jti}") is not None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Revocation service unavailable.",
        )


def _decode_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            JWT_SIGNING_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "sub"]},
        )

        jti = payload.get("jti")
        if jti and _is_jti_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
            )

        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token required.",
            )
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
    import uuid

    now = int(time.time())
    payload = {
        "sub": "django-backend",
        "jti": str(uuid.uuid4()),
        "token_type": "service",
        "iat": now,
        "exp": now + SERVICE_TOKEN_LIFETIME_SECONDS,
        "nbf": now,
        "iss": JWT_ISSUER,
        "aud": "fastapi-service",
    }
    return jwt.encode(payload, FASTAPI_SERVICE_SECRET, algorithm=JWT_ALGORITHM)


def verify_service_key(x_service_key: Optional[str] = None) -> bool:
    """Validates the internal service token on internal endpoints.

    Only accepts a short-lived JWT-signed service token.
    """
    if x_service_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service token is required.",
        )

    try:
        payload = jwt.decode(x_service_key, FASTAPI_SERVICE_SECRET, algorithms=[JWT_ALGORITHM], audience="fastapi-service", issuer=JWT_ISSUER, options={"require": ["exp", "iat", "sub", "jti"]})
        if payload.get("sub") != "django-backend":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid service token.",
            )
        if payload.get("token_type") != "service":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token type.",
            )
        if payload.get("iss") != JWT_ISSUER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token issuer.",
            )
        if payload.get("aud") != JWT_AUDIENCE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token audience.",
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
