.PHONY: help up down build logs seed test-django test-fastapi test-all migrate shell-django shell-db

help:
	@echo ""
	@echo "  DataLens — Available Commands"
	@echo "  ────────────────────────────────────────"
	@echo "  make up            Start all services (detached)"
	@echo "  make down          Stop and remove containers"
	@echo "  make build         Rebuild all Docker images"
	@echo "  make logs          Tail logs from all services"
	@echo "  make seed          Seed demo org + users"
	@echo "  make migrate       Run Django migrations"
	@echo "  make test-django   Run Django test suite"
	@echo "  make test-fastapi  Run FastAPI test suite"
	@echo "  make test-all      Run all tests"
	@echo "  make shell-django  Django shell"
	@echo "  make shell-db      psql shell"
	@echo ""

up:
	docker compose up -d
	@echo "Services running. Frontend → http://localhost"

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec django python manage.py migrate --noinput

seed:
	docker compose exec django python manage.py seed_demo

test-django:
	docker compose exec django python manage.py test tests --verbosity=2

test-fastapi:
	docker compose exec fastapi pytest tests/ -v

test-all: test-django test-fastapi
	@echo "All tests complete."

shell-django:
	docker compose exec django python manage.py shell

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

# Local dev (without Docker)
dev-django:
	cd django_backend && python manage.py runserver 0.0.0.0:8000

dev-fastapi:
	cd fastapi_service && uvicorn main:app --reload --port 8001

dev-frontend:
	cd frontend && npm run dev
