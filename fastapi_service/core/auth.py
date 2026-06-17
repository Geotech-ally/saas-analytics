"""
JWT validation for FastAPI — verifies tokens issued by Django's SimpleJWT.
Both the Django secret key and the internal service key are required.
"""
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from schemas.analytics import TokenClaims

bearer_scheme = HTTPBearer()

JWT_SECRET = os.environ["DJANGO_SECRET_KEY"]
JWT_ALGORITHM = "HS256"
INTERNAL_SERVICE_KEY = os.environ["INTERNAL_SERVICE_KEY"]


def _decode_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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


def verify_service_key(x_service_key: Optional[str] = None) -> bool:
    """Validates the inter-service key on internal endpoints."""
    if x_service_key != INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid service key.",
        )
    return True
