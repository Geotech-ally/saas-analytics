"""
Secure HTTP client for Django → FastAPI service communication.
Uses the user's JWT for identity and a short-lived internal JWT for
service-to-service authentication.
"""
import logging
import time
import uuid
from typing import Any, Dict

import jwt
import requests
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)

FASTAPI_BASE_URL = getattr(settings, "FASTAPI_BASE_URL", "http://fastapi:8001")
REQUEST_TIMEOUT = 10  # seconds

SERVICE_TOKEN_LIFETIME = int(getattr(settings, "SERVICE_TOKEN_LIFETIME_SECONDS", "300"))


class FastAPIClientError(Exception):
    pass


def _make_service_token() -> str:
    now = int(time.time())
    payload = {
        "iss": settings.JWT_ISSUER,
        "sub": "django-backend",
        "aud": "fastapi-service",
        "jti": str(uuid.uuid4()),
        "token_type": "service",
        "iat": now,
        "exp": now + SERVICE_TOKEN_LIFETIME,
        "nbf": now,
    }
    return jwt.encode(payload, settings.FASTAPI_SERVICE_SECRET, algorithm="HS256")


class FastAPIClient:
    def __init__(self, user):
        token = AccessToken.for_user(user)
        token["role"] = user.role
        token["org_id"] = str(user.organization_id) if user.organization_id else None
        self._headers = {
            "Authorization": f"Bearer {str(token)}",
            "Content-Type": "application/json",
            "X-Service-Key": _make_service_token(),
        }

    def _get(self, path: str, params: Dict = None) -> Any:
        url = f"{FASTAPI_BASE_URL}{path}"
        try:
            resp = requests.get(url, headers=self._headers, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("FastAPI GET %s failed: %s", path, exc)
            raise FastAPIClientError(str(exc)) from exc

    def _post(self, path: str, payload: Dict = None) -> Any:
        url = f"{FASTAPI_BASE_URL}{path}"
        try:
            resp = requests.post(url, headers=self._headers, json=payload or {}, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("FastAPI POST %s failed: %s", path, exc)
            raise FastAPIClientError(str(exc)) from exc

    def trigger_processing(self, dataset_id: str) -> Dict:
        return self._post(f"/api/v1/datasets/{dataset_id}/process")

    def get_analytics(self, dataset_id: str) -> Dict:
        return self._get(f"/api/v1/analytics/{dataset_id}")

    def get_insights(self, dataset_id: str) -> Dict:
        return self._get(f"/api/v1/analytics/{dataset_id}/insights")
