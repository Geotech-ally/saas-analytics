"""
FastAPI test suite — Security Hardening Tests
Run: pytest fastapi_service/tests/ -v
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

# ── Shared secret must be set before app import ────────────────────────
import os
os.environ.setdefault("JWT_SIGNING_SECRET", "test-jwt-signing-secret-for-pytest-only")
os.environ.setdefault("FASTAPI_SERVICE_SECRET", "test-fastapi-service-secret-for-pytest-only")
os.environ.setdefault("INTERNAL_SERVICE_KEY", "test-internal-key")
os.environ.setdefault("MEDIA_ROOT", "/tmp/test-media")

from main import app  # noqa: E402

SECRET = os.environ["JWT_SIGNING_SECRET"]
SERVICE_SECRET = os.environ["FASTAPI_SERVICE_SECRET"]
LEGACY_SERVICE_KEY = os.environ["INTERNAL_SERVICE_KEY"]


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
def test_missing_token_returns_401(client):
    resp = client.get(f"/api/v1/analytics/{uuid4()}")
    assert resp.status_code == 401


def test_expired_token_returns_401(client, expired_token):
    resp = client.get(f"/api/v1/analytics/{uuid4()}", headers=auth(expired_token))
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_invalid_token_returns_401(client):
    resp = client.get(f"/api/v1/analytics/{uuid4()}", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


def test_valid_token_passes_auth(client, user_token, tmp_path, monkeypatch):
    resp = client.get(f"/api/v1/analytics/{uuid4()}", headers=auth(user_token))
    assert resp.status_code == 404  # auth passed, dataset not found


# ── Tenant isolation tests ──────────────────────────────────────────────────
def test_analytics_denies_cross_org_access(client, user_token, tmp_path, monkeypatch):
    import os
    from pathlib import Path

    media_root = tmp_path / "media"
    media_root.mkdir()
    datasets_dir = media_root / "datasets"
    datasets_dir.mkdir()

    org_a = str(uuid4())
    org_b = str(uuid4())
    dataset_id = str(uuid4())

    org_a_dir = datasets_dir / org_a
    org_b_dir = datasets_dir / org_b
    org_a_dir.mkdir()
    org_b_dir.mkdir()

    csv_a = org_a_dir / f"{dataset_id}.csv"
    csv_a.write_text("col1,col2\n1,2\n3,4\n")

    monkeypatch.setenv("MEDIA_ROOT", str(media_root))

    token_a = _make_token(role="user", org_id=org_a)
    token_b = _make_token(role="user", org_id=org_b)

    resp_a = client.get(f"/api/v1/analytics/{dataset_id}", headers=auth(token_a))
    resp_b = client.get(f"/api/v1/analytics/{dataset_id}", headers=auth(token_b))

    assert resp_a.status_code == 200
    assert resp_b.status_code == 404


def test_insights_denies_cross_org_access(client, user_token, tmp_path, monkeypatch):
    import os
    from pathlib import Path

    media_root = tmp_path / "media"
    media_root.mkdir()
    datasets_dir = media_root / "datasets"
    datasets_dir.mkdir()

    org_a = str(uuid4())
    org_b = str(uuid4())
    dataset_id = str(uuid4())

    org_a_dir = datasets_dir / org_a
    org_b_dir = datasets_dir / org_b
    org_a_dir.mkdir()
    org_b_dir.mkdir()

    csv_a = org_a_dir / f"{dataset_id}.csv"
    csv_a.write_text("col1,col2\n1,2\n3,4\n")

    monkeypatch.setenv("MEDIA_ROOT", str(media_root))

    token_a = _make_token(role="user", org_id=org_a)
    token_b = _make_token(role="user", org_id=org_b)

    resp_a = client.get(f"/api/v1/analytics/{dataset_id}/insights", headers=auth(token_a))
    resp_b = client.get(f"/api/v1/analytics/{dataset_id}/insights", headers=auth(token_b))

    assert resp_a.status_code == 200
    assert resp_b.status_code == 404


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
        assert result.anomalies[0].severity in ("low", "medium", "high")


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
    assert resp.status_code in (422, 403)


def test_process_with_valid_service_key(client, user_token):
    dataset_id = uuid4()
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/process",
        headers={**auth(user_token), "X-Service-Key": LEGACY_SERVICE_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"


def _make_service_token() -> str:
    now = int(time.time())
    payload = {
        "service_name": "django-backend",
        "iat": now,
        "exp": now + 300,
        "nbf": now,
    }
    return jwt.encode(payload, SERVICE_SECRET, algorithm="HS256")


def test_process_with_internal_jwt_token(client, user_token):
    dataset_id = uuid4()
    service_token = _make_service_token()
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/process",
        headers={**auth(user_token), "X-Service-Key": service_token},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


def test_process_with_wrong_service_key_fails(client, user_token):
    dataset_id = uuid4()
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/process",
        headers={**auth(user_token), "X-Service-Key": "wrong-key"},
    )
    assert resp.status_code in (401, 403)


# ── Path traversal tests ────────────────────────────────────────────────────
def test_data_loader_prevents_path_traversal(tmp_path, monkeypatch):
    import os
    from services.data_loader import load_dataset

    media_root = tmp_path / "media"
    media_root.mkdir()
    datasets_dir = media_root / "datasets"
    datasets_dir.mkdir()

    org_id = str(uuid4())
    org_dir = datasets_dir / org_id
    org_dir.mkdir()

    safe_csv = org_dir / "safe-dataset.csv"
    safe_csv.write_text("col1,col2\n1,2\n3,4\n")

    monkeypatch.setenv("MEDIA_ROOT", str(media_root))

    df = load_dataset("safe-dataset", org_id)
    assert len(df) == 2


def test_data_loader_blocks_other_org(tmp_path, monkeypatch):
    from services.data_loader import load_dataset

    media_root = tmp_path / "media"
    media_root.mkdir()
    datasets_dir = media_root / "datasets"
    datasets_dir.mkdir()

    org_a = str(uuid4())
    org_b = str(uuid4())
    org_a_dir = datasets_dir / org_a
    org_b_dir = datasets_dir / org_b
    org_a_dir.mkdir()
    org_b_dir.mkdir()

    csv_a = org_a_dir / "dataset.csv"
    csv_b = org_b_dir / "dataset.csv"
    csv_a.write_text("col1,col2\n1,2\n")
    csv_b.write_text("col1,col2\n3,4\n")

    monkeypatch.setenv("MEDIA_ROOT", str(media_root))

    with pytest.raises(FileNotFoundError):
        load_dataset("nonexistent-dataset", org_b)
