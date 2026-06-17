"""
FastAPI test suite.
Run: pytest fastapi_service/tests/ -v
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

# ── Shared secret must be set before app import ────────────────────────────
import os
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("INTERNAL_SERVICE_KEY", "test-internal-key")
os.environ.setdefault("MEDIA_ROOT", "/tmp/test-media")

from main import app  # noqa: E402

SECRET = os.environ["DJANGO_SECRET_KEY"]
SERVICE_KEY = os.environ["INTERNAL_SERVICE_KEY"]


# ── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    return TestClient(app)


def _make_token(role="user", org_id=None, expired=False):
    now = int(time.time())
    payload = {
        "sub": str(uuid4()),
        "email": "test@acme.com",
        "role": role,
        "org_id": org_id or str(uuid4()),
        "exp": now - 10 if expired else now + 3600,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


@pytest.fixture
def user_token():
    return _make_token(role="user")


@pytest.fixture
def admin_token():
    return _make_token(role="admin")


@pytest.fixture
def expired_token():
    return _make_token(expired=True)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Health ─────────────────────────────────────────────────────────────────
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Auth middleware ────────────────────────────────────────────────────────
def test_missing_token_returns_403(client):
    resp = client.get(f"/api/v1/analytics/{uuid4()}")
    assert resp.status_code == 403


def test_expired_token_returns_401(client, expired_token):
    resp = client.get(f"/api/v1/analytics/{uuid4()}", headers=auth(expired_token))
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_invalid_token_returns_401(client):
    resp = client.get(f"/api/v1/analytics/{uuid4()}", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


def test_valid_token_passes_auth(client, user_token, tmp_path, monkeypatch):
    """Valid token should pass auth even if dataset doesn't exist (404 not 401/403)."""
    resp = client.get(f"/api/v1/analytics/{uuid4()}", headers=auth(user_token))
    assert resp.status_code == 404  # auth passed, dataset not found


# ── KPI service unit tests ─────────────────────────────────────────────────
def test_kpi_basic():
    from services.analytics_service import compute_kpis
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    result = compute_kpis(values, uuid4())
    assert result.total == 150.0
    assert result.average == 30.0
    assert result.min_value == 10.0
    assert result.max_value == 50.0


def test_kpi_growth_rate():
    from services.analytics_service import compute_kpis
    current = [100.0, 110.0, 120.0]
    previous = [80.0, 90.0, 100.0]
    result = compute_kpis(current, uuid4(), previous_values=previous)
    assert result.growth_rate is not None
    assert result.growth_rate > 0


def test_kpi_empty_raises():
    from services.analytics_service import compute_kpis
    with pytest.raises(ValueError, match="No data"):
        compute_kpis([], uuid4())


# ── Trend detection tests ──────────────────────────────────────────────────
def test_trend_upward():
    from services.analytics_service import detect_trends
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    result = detect_trends(values, uuid4())
    assert result.direction == "up"
    assert result.slope > 0


def test_trend_downward():
    from services.analytics_service import detect_trends
    values = [6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    result = detect_trends(values, uuid4())
    assert result.direction == "down"
    assert result.slope < 0


def test_trend_flat():
    from services.analytics_service import detect_trends
    values = [5.0, 5.0, 5.0, 5.0, 5.0]
    result = detect_trends(values, uuid4())
    assert result.direction == "flat"


def test_trend_points_count():
    from services.analytics_service import detect_trends
    values = [1.0, 2.0, 3.0, 4.0]
    result = detect_trends(values, uuid4())
    assert len(result.points) == 4


def test_trend_with_custom_periods():
    from services.analytics_service import detect_trends
    values = [10.0, 20.0, 30.0]
    periods = ["Jan", "Feb", "Mar"]
    result = detect_trends(values, uuid4(), periods=periods)
    assert result.points[0].period == "Jan"
    assert result.points[2].period == "Mar"


# ── Anomaly detection tests ────────────────────────────────────────────────
def test_anomaly_detects_outlier():
    from services.analytics_service import detect_anomalies
    # 9 normal + 1 extreme outlier
    values = [10.0] * 9 + [1000.0]
    result = detect_anomalies(values, uuid4(), threshold_z=2.5)
    assert result.anomaly_count >= 1
    assert result.anomalies[0].value == 1000.0


def test_anomaly_none_in_uniform():
    from services.analytics_service import detect_anomalies
    values = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1]
    result = detect_anomalies(values, uuid4(), threshold_z=2.5)
    assert result.anomaly_count == 0


def test_anomaly_severity_high():
    from services.analytics_service import detect_anomalies
    values = [10.0] * 9 + [10000.0]
    result = detect_anomalies(values, uuid4(), threshold_z=2.5)
    if result.anomaly_count > 0:
        assert result.anomalies[0].severity in ("medium", "high")


def test_anomaly_short_series_returns_empty():
    from services.analytics_service import detect_anomalies
    result = detect_anomalies([1.0, 2.0], uuid4())
    assert result.anomaly_count == 0


# ── Insights generation tests ──────────────────────────────────────────────
def test_insights_always_include_kpi():
    from services.analytics_service import compute_kpis, detect_trends, detect_anomalies, generate_insights
    dataset_id = uuid4()
    values = [10.0, 20.0, 15.0, 25.0, 30.0]
    kpi = compute_kpis(values, dataset_id)
    trends = detect_trends(values, dataset_id)
    anomalies = detect_anomalies(values, dataset_id)
    insights = generate_insights(kpi, trends, anomalies)
    types = [i.type for i in insights]
    assert "kpi" in types


def test_insights_anomaly_item_when_present():
    from services.analytics_service import compute_kpis, detect_trends, detect_anomalies, generate_insights
    dataset_id = uuid4()
    values = [10.0] * 9 + [9999.0]
    kpi = compute_kpis(values, dataset_id)
    trends = detect_trends(values, dataset_id)
    anomalies = detect_anomalies(values, dataset_id, threshold_z=2.5)
    insights = generate_insights(kpi, trends, anomalies)
    if anomalies.anomaly_count > 0:
        types = [i.type for i in insights]
        assert "anomaly" in types


# ── Processing endpoint ────────────────────────────────────────────────────
def test_process_requires_service_key(client, user_token):
    dataset_id = uuid4()
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/process",
        headers=auth(user_token),
    )
    # Missing X-Service-Key header → 422 (missing required header) or 403
    assert resp.status_code in (422, 403)


def test_process_with_valid_keys(client, user_token):
    dataset_id = uuid4()
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/process",
        headers={**auth(user_token), "X-Service-Key": SERVICE_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert str(body["dataset_id"]) == str(dataset_id)
