from pathlib import Path
from dotenv import load_dotenv
import os
import secrets
import sys
from datetime import timedelta

# ─────────────────────────────────────────────────────────────
# Base setup
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

DJANGO_ENV = os.getenv("DJANGO_ENV", "development")

# Load environment variables
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", secrets.token_urlsafe(64))
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost 127.0.0.1 testserver"
).split()

# ─────────────────────────────────────────────────────────────
# Security — conditional on DEBUG
# ─────────────────────────────────────────────────────────────
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_PROXY_SSL_HEADER = None
else:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

# ─────────────────────────────────────────────────────────────
# JWT / Secrets
# ─────────────────────────────────────────────────────────────
# JWT material is deliberately independent of Django's session/CSRF secret.
# Development gets ephemeral values so a missing local .env never causes a
# developer to accidentally share DJANGO_SECRET_KEY with another service.
JWT_SIGNING_SECRET = os.getenv("JWT_SIGNING_SECRET") or secrets.token_urlsafe(64)
FASTAPI_SERVICE_SECRET = os.getenv("FASTAPI_SERVICE_SECRET") or secrets.token_urlsafe(32)
if DJANGO_ENV == "production" and (
    not os.getenv("DJANGO_SECRET_KEY") or not os.getenv("JWT_SIGNING_SECRET")
    or not os.getenv("FASTAPI_SERVICE_SECRET") or JWT_SIGNING_SECRET == SECRET_KEY
):
    raise RuntimeError("Production requires distinct DJANGO_SECRET_KEY, JWT_SIGNING_SECRET, and FASTAPI_SERVICE_SECRET.")
JWT_ISSUER = os.getenv("JWT_ISSUER", "datalens-backend")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "datalens-api")
SERVICE_TOKEN_LIFETIME_SECONDS = int(os.getenv("SERVICE_TOKEN_LIFETIME_SECONDS", "300"))
WEEKLY_REPORT_TIMEZONE = os.getenv("ANALYTICS_TIMEZONE", "UTC")
WEEKLY_REPORT_HOUR = int(os.getenv("WEEKLY_REPORT_HOUR", "8"))
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))

# ─────────────────────────────────────────────────────────────
# Applications
# ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "rest_framework_simplejwt.token_blacklist",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "dj_rest_auth",
    "dj_rest_auth.registration",

    # allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",

    # Local apps
    "apps.users",
    "apps.organizations",
    "apps.datasets",
    "django_celery_beat",
]

# ─────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # allauth
    "allauth.account.middleware.AccountMiddleware",

    # Custom middleware
    "apps.users.middleware.TokenBlacklistMiddleware",
]

# ─────────────────────────────────────────────────────────────
# User model / auth
# ─────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]

AUTHENTICATION_BACKENDS = (
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
)

# ─────────────────────────────────────────────────────────────
# REST AUTH (SINGLE CLEAN CONFIG)
# ─────────────────────────────────────────────────────────────
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "auth-token",
    "JWT_AUTH_REFRESH_COOKIE": "refresh-token",
    "REGISTER_SERIALIZER": "apps.users.serializers.RegisterSerializer",
    "USER_DETAILS_SERIALIZER": "apps.users.serializers.UserSerializer",
}

# ─────────────────────────────────────────────────────────────
# URLs / Templates
# ─────────────────────────────────────────────────────────────
ROOT_URLCONF = "core.urls"

# Disable APPEND_SLASH for API consistency.
# When True (default), CommonMiddleware issues 301 redirects for URLs
# without trailing slashes. Django converts POST→GET on redirect,
# dropping the request body and causing silent failures.
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# ─────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────
if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }
else:
    if DJANGO_ENV == "production":
        raise RuntimeError("POSTGRES_HOST must be set in production.")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "TIMEOUT": 300,
    }
}

# ─────────────────────────────────────────────────────────────
# REST Framework
# ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.auth.AccessTokenOnlyAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer"
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "EXCEPTION_HANDLER": "core.exception_handler.custom_exception_handler",
}

if "test" in sys.argv:
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "anon": "1000/min",
        "user": "10000/min",
        "login": "1000/min",
        "login_block": "10000/min",
        "password_reset": "1000/min",
        "password_reset_block": "10000/min",
    }
else:
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "anon": "100/min",
        "user": "1000/min",
        "login": "5/min",
        "login_block": "15/min",
        "password_reset": "3/min",
        "password_reset_block": "5/min",
    }

# ─────────────────────────────────────────────────────────────
# Celery
# ─────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_POOL_LIMIT = 10
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "weekly-analytics-report": {
        "task": "apps.datasets.tasks.send_weekly_analytics_report",
        "schedule": crontab(minute=0, hour=WEEKLY_REPORT_HOUR, day_of_week="sat"),
        "args": (),
    },
}
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ─────────────────────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SIGNING_SECRET,
    "ISSUER": JWT_ISSUER,
    "AUDIENCE": JWT_AUDIENCE,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "apps.users.views.CustomTokenObtainPairSerializer",
}

# ─────────────────────────────────────────────────────────────
# CORS (FIXED)
# ─────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3002,http://127.0.0.1:3002"
).split(",")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ["*"]
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

# ─────────────────────────────────────────────────────────────
# Static / Media
# ─────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─────────────────────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@datalens.com")

# ─────────────────────────────────────────────────────────────
# Misc
# ─────────────────────────────────────────────────────────────
SITE_ID = int(os.getenv("DJANGO_SITE_ID", "1"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3002")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps.users": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.datasets": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
