# DataLens — SaaS Analytics Platform

A production-ready, multi-tenant SaaS analytics system built with Django, FastAPI, React, and PostgreSQL.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (React)                     │
│   Auth & CRUD → Django        Analytics → FastAPI       │
└────────────┬───────────────────────────┬────────────────┘
             │ JWT                        │ JWT (dedicated signing secret)
             ▼                           ▼
┌────────────────────┐      ┌────────────────────────────┐
│   Django (DRF)     │      │   FastAPI (Analytics)      │
│                    │      │                            │
│  • Custom User     │ JWT  │  • KPI calculations        │
│  • Organizations   │─────▶│  • Trend detection         │
│  • RBAC (Admin/    │      │  • Anomaly detection       │
│    User)           │      │  • Insight generation      │
│  • Dataset upload  │      │                            │
│  • JWT issuance    │      │  Validates Django JWTs     │
└────────┬───────────┘      └───────────┬────────────────┘
         │                              │
         ▼                              │ (reads shared volume)
┌────────────────────┐                  │
│    PostgreSQL      │                  │
│                    │                  │
│  users / orgs /    │                  │
│  datasets          │                  │
└────────────────────┘                  │
         │                              │
         └──── /app/media ◀─────────────┘
                (shared Docker volume)
```

## Request Flow

1. **Login** → `POST /api/v1/auth/token/` (Django) → JWT with `role`, `org_id`, `email` claims
2. **Upload dataset** → `POST /api/v1/datasets/` (Django) → stored to PostgreSQL + media volume → triggers FastAPI processing
3. **View analytics** → `GET /api/v1/analytics/{id}` (FastAPI directly from browser) — JWT validated using the shared secret
4. **Django→FastAPI proxy** (optional) → `GET /api/v1/datasets/{id}/analytics/` — Django acts as gateway, forwards user JWT

## Security Model

| Concern | Implementation |
|---|---|
| Authentication | Django SimpleJWT — signed HS256 tokens |
| Claims in token | `email`, `role`, `org_id` embedded at issue time |
| FastAPI validation | PyJWT decodes with dedicated `JWT_SIGNING_SECRET`, never `DJANGO_SECRET_KEY` |
| Inter-service auth | Short-lived signed `X-Service-Key` service JWT (issuer, subject, audience, jti, expiry) |
| Tenant isolation | All queries filtered by `organization_id` |
| RBAC | `IsOrganizationAdmin` / `IsOrganizationMember` permission classes |

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd saas-analytics
cp .env.example .env
# Edit .env — set distinct strong values for DJANGO_SECRET_KEY, JWT_SIGNING_SECRET, and FASTAPI_SERVICE_SECRET.
```

### 2. Generate secrets

```bash
# Django secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Internal service key
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start services

```bash
docker compose up --build
```

Services start in dependency order: PostgreSQL → Django (runs migrations) → FastAPI → Frontend.

| Service | URL |
|---|---|
| React App | http://localhost |
| Django API | http://localhost/api/django |
| FastAPI | http://localhost/api/analytics |
| Django Admin | http://localhost/api/django/admin |
| FastAPI Docs | http://localhost:8001/docs |

### 4. Create first organization & admin user

```bash
docker compose exec django python manage.py shell -c "
from apps.organizations.models import Organization
from apps.users.models import User

org = Organization.objects.create(name='Acme Corp', slug='acme', plan='pro')
user = User.objects.create_superuser(email='admin@acme.com', password='SecurePass123!')
user.organization = org
user.role = 'admin'
user.save()
print('Done')
"
```

---

## Project Structure

```
saas-analytics/
├── django_backend/
│   ├── apps/
│   │   ├── users/          # Custom User model, auth views
│   │   ├── organizations/  # Multi-tenant org model
│   │   └── datasets/       # File upload, FastAPI proxy
│   ├── core/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── permissions.py  # RBAC permission classes
│   │   └── fastapi_client.py  # HTTP client to FastAPI
│   └── requirements.txt
│
├── fastapi_service/
│   ├── main.py             # App entry point
│   ├── core/auth.py        # JWT validation middleware
│   ├── routes/analytics.py # API endpoints
│   ├── services/
│   │   ├── analytics_service.py  # KPI, trends, anomalies
│   │   └── data_loader.py        # CSV/Excel/JSON loading
│   ├── schemas/analytics.py      # Pydantic models
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── services/api.ts        # Axios clients + service layer
│       ├── hooks/                 # useAuth, useDatasets, useAnalytics
│       ├── components/
│       │   ├── auth/Login.tsx
│       │   └── dashboard/Dashboard.tsx
│       └── types/index.ts
│
├── docker/
│   ├── Dockerfile.django
│   ├── Dockerfile.fastapi
│   └── Dockerfile.frontend
│
├── docker-compose.yml
└── .env.example
```

---

## API Reference

### Django (Auth & Data)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register/` | None | Register user |
| POST | `/api/v1/auth/token/` | None | Login → JWT |
| POST | `/api/v1/auth/token/refresh/` | Refresh token | Rotate token |
| GET | `/api/v1/users/me/` | JWT | Current user profile |
| PATCH | `/api/v1/users/me/` | JWT | Update profile |
| POST | `/api/v1/users/change_password/` | JWT | Change password |
| GET/POST | `/api/v1/datasets/` | JWT | List / upload datasets |
| GET | `/api/v1/datasets/{id}/analytics/` | JWT | Proxied analytics |
| GET | `/api/v1/datasets/{id}/insights/` | JWT | Proxied insights |

### FastAPI (Analytics)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/analytics/{id}` | JWT | Full analytics report |
| GET | `/api/v1/analytics/{id}/kpi` | JWT | KPI summary only |
| GET | `/api/v1/analytics/{id}/insights` | JWT | Insight items |
| POST | `/api/v1/datasets/{id}/process` | JWT + Service Key | Trigger processing |
| GET | `/health` | None | Health check |

---

## Scaling Notes

- **Workers**: Django uses `gthread` workers (CPU+IO bound); FastAPI uses `uvloop` + `httptools` for high throughput
- **Database**: Connection pooling via `CONN_MAX_AGE=60`; add PgBouncer for 100+ concurrent users
- **Media**: Replace shared Docker volume with S3 in production — update `data_loader.py` to use `boto3`
- **Processing**: Replace `trigger_processing` sync call with Celery + Redis for true async dataset processing
- **Caching**: Add Redis cache layer in FastAPI for repeated analytics calls on the same dataset

## Operations

Dataset uploads create an organization-scoped processing job and return immediately. Run the Django API, a Celery worker, and Celery Beat together; Beat dispatches the Saturday job, which generates exactly one immutable report for each organization for the previous completed Monday–Sunday period. Delivery records make email retry-safe.

Useful worktree recovery commands:

```bash
git worktree list
git worktree add ../feature/name -b feature/name
git worktree remove ../feature/name
git worktree prune
```

For an abandoned worktree, confirm it is no longer needed, remove it with `git worktree remove`, then run `git worktree prune`. Resolve merge conflicts in the affected worktree, stage the resolution, and continue the rebase; never delete a worktree directory manually.
