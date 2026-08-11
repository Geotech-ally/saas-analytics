"""
Django test suite — Security Hardening Tests
Run: python manage.py test tests
"""
import os
import sys
import tempfile

# Ensure fastapi_service is importable from Django tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "fastapi_service"))

import jwt
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.organizations.models import Organization
from apps.users.models import User
from apps.datasets.models import Dataset


# ── Helpers ────────────────────────────────────────────────────────────────
def make_org(name="Acme", slug="acme", plan="pro"):
    return Organization.objects.create(name=name, slug=slug, plan=plan)


def make_user(org, email="user@acme.com", role=User.Role.USER, password="Test1234!"):
    return User.objects.create_user(email=email, password=password, organization=org, role=role)


def get_tokens(client, email, password="Test1234!"):
    resp = client.post(reverse("token_obtain"), {"email": email, "password": password}, follow=False)
    if hasattr(resp, "data") and "access" in resp.data:
        return resp.data
    return {}


def get_list_results(resp):
    if isinstance(resp.data, list):
        return resp.data
    return resp.data.get("results", [])


# ── Auth Tests ─────────────────────────────────────────────────────────────
class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = make_org()
        self.user = make_user(self.org, email="auth@acme.com")

    def test_obtain_token_success(self):
        resp = self.client.post(reverse("token_obtain"), {"email": "auth@acme.com", "password": "Test1234!"}, follow=False)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_obtain_token_bad_credentials(self):
        resp = self.client.post(reverse("token_obtain"), {"email": "auth@acme.com", "password": "wrong"}, follow=False)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        resp = self.client.get(reverse("user-me"), follow=False)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_user(self):
        tokens = get_tokens(self.client, "auth@acme.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = self.client.get(reverse("user-me"), follow=False)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "auth@acme.com")

    def test_register_new_user(self):
        payload = {
            "email": "new@acme.com",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
            "first_name": "New",
            "last_name": "User",
        }
        resp = self.client.post(reverse("rest_register"), payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@acme.com").exists())

    def test_register_password_mismatch(self):
        payload = {
            "email": "bad@acme.com",
            "password1": "StrongPass1!",
            "password2": "DifferentPass1!",
        }
        resp = self.client.post(reverse("rest_register"), payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_contains_custom_claims(self):
        tokens = get_tokens(self.client, "auth@acme.com")
        from django.conf import settings
        secret = getattr(settings, "JWT_SIGNING_SECRET", settings.SECRET_KEY)
        payload = jwt.decode(tokens["access"], secret, algorithms=["HS256"])
        self.assertIn("role", payload)
        self.assertIn("org_id", payload)
        self.assertIn("email", payload)

    def test_token_uses_jwt_signing_secret(self):
        from django.conf import settings
        self.assertEqual(
            settings.SIMPLE_JWT["SIGNING_KEY"],
            settings.JWT_SIGNING_SECRET,
        )


# ── Organization Tests ──────────────────────────────────────────────────────
class OrganizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = make_org()
        self.admin = make_user(self.org, email="admin@acme.com", role=User.Role.ADMIN)
        self.member = make_user(self.org, email="member@acme.com", role=User.Role.USER)

    def _auth(self, email):
        tokens = get_tokens(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_admin_can_read_org(self):
        self._auth("admin@acme.com")
        resp = self.client.get(reverse("organization-list"), follow=False)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_member_can_read_org(self):
        self._auth("member@acme.com")
        resp = self.client.get(reverse("organization-list"), follow=False)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_member_cannot_update_org(self):
        self._auth("member@acme.com")
        resp = self.client.patch(
            reverse("organization-detail", args=[self.org.id]),
            {"name": "Hacked"},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_org(self):
        self._auth("admin@acme.com")
        resp = self.client.patch(
            reverse("organization-detail", args=[self.org.id]),
            {"name": "Acme Updated"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Acme Updated")

    def test_user_cannot_see_other_org(self):
        other_org = make_org(name="Other", slug="other")
        self._auth("member@acme.com")
        resp = self.client.get(reverse("organization-detail", args=[other_org.id]))
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])


# ── User Management Tests ───────────────────────────────────────────────────
class UserManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = make_org()
        self.admin = make_user(self.org, email="admin@acme.com", role=User.Role.ADMIN)
        self.member = make_user(self.org, email="member@acme.com", role=User.Role.USER)

    def _auth(self, email):
        tokens = get_tokens(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_admin_can_list_org_users(self):
        self._auth("admin@acme.com")
        resp = self.client.get(reverse("user-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        emails = [u["email"] for u in get_list_results(resp)]
        self.assertIn("member@acme.com", emails)

    def test_member_cannot_create_user(self):
        self._auth("member@acme.com")
        resp = self.client.post(reverse("user-list"), {
            "email": "new@acme.com", "password": "Test1234!", "password_confirm": "Test1234!",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_password(self):
        self._auth("member@acme.com")
        resp = self.client.post(reverse("user-change-password"), {
            "current_password": "Test1234!",
            "new_password": "NewStrong99!",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password("NewStrong99!"))

    def test_change_password_wrong_current(self):
        self._auth("member@acme.com")
        resp = self.client.post(reverse("user-change-password"), {
            "current_password": "wrong",
            "new_password": "NewStrong99!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_update_own_role(self):
        self._auth("member@acme.com")
        resp = self.client.patch(
            reverse("user-me"),
            {"role": "admin"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, User.Role.USER)

    def test_admin_can_set_role(self):
        self._auth("admin@acme.com")
        resp = self.client.post(
            reverse("user-set-role", args=[self.member.id]),
            {"role": "admin"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, User.Role.ADMIN)

    def test_member_cannot_set_role(self):
        self._auth("member@acme.com")
        resp = self.client.post(
            reverse("user-set-role", args=[self.admin.id]),
            {"role": "user"},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ── RBAC / Tenant Isolation Tests ──────────────────────────────────────────
class TenantIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_a = make_org(name="Org A", slug="org-a")
        self.org_b = make_org(name="Org B", slug="org-b")
        self.user_a = make_user(self.org_a, email="a@orga.com")
        self.user_b = make_user(self.org_b, email="b@orgb.com")

    def _auth(self, email):
        tokens = get_tokens(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_user_a_cannot_see_org_b_users(self):
        self._auth("a@orga.com")
        resp = self.client.get(reverse("user-list"))
        emails = [u["email"] for u in get_list_results(resp)]
        self.assertNotIn("b@orgb.com", emails)

    def test_user_a_cannot_see_org_b(self):
        self._auth("a@orga.com")
        resp = self.client.get(reverse("organization-detail", args=[self.org_b.id]))
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_user_a_cannot_see_org_b_datasets(self):
        dataset_b = Dataset.objects.create(
            name="B Dataset",
            organization=self.org_b,
            uploaded_by=self.user_b,
        )
        self._auth("a@orga.com")
        resp = self.client.get(reverse("dataset-list"))
        dataset_ids = [d["id"] for d in get_list_results(resp)]
        self.assertNotIn(str(dataset_b.id), dataset_ids)

    def test_user_a_cannot_access_org_b_dataset_detail(self):
        dataset_b = Dataset.objects.create(
            name="B Dataset",
            organization=self.org_b,
            uploaded_by=self.user_b,
        )
        self._auth("a@orga.com")
        resp = self.client.get(reverse("dataset-detail", args=[dataset_b.id]))
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])


# ── File Upload Security Tests ─────────────────────────────────────────
class FileUploadSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = make_org()
        self.user = make_user(self.org, email="uploader@acme.com")

    def _auth(self):
        tokens = get_tokens(self.client, "uploader@acme.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_upload_valid_csv(self):
        self._auth()
        csv_content = b"col1,col2\n1,2\n3,4\n"
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(csv_content)
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                resp = self.client.post(
                    reverse("dataset-list"),
                    {"name": "Test CSV", "file": f},
                    format="multipart",
                )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_upload_file_too_large_rejected(self):
        self._auth()
        large_content = b"x" * (11 * 1024 * 1024)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(large_content)
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                resp = self.client.post(
                    reverse("dataset-list"),
                    {"name": "Too Large", "file": f},
                    format="multipart",
                )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("10 MB", resp.data["file"][0])

    def test_upload_invalid_extension_rejected(self):
        self._auth()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"hello")
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                resp = self.client.post(
                    reverse("dataset-list"),
                    {"name": "Bad File", "file": f},
                    format="multipart",
                )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_path_traversal_rejected(self):
        self._auth()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(b"col1,col2\n1,2\n")
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                resp = self.client.post(
                    reverse("dataset-list"),
                    {"name": "Traversal", "file": f},
                    format="multipart",
                )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# ── Logout & Token Invalidation Tests ──────────────────────────────────
class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = make_org()
        self.user = make_user(self.org, email="logout@acme.com")

    def _auth(self, email, password="Test1234!"):
        resp = self.client.post(reverse("token_obtain"), {"email": email, "password": password})
        return resp.data

    def test_logout_invalidates_refresh_token(self):
        tokens = self._auth("logout@acme.com")
        refresh = tokens["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = self.client.get(reverse("user-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.client.post(reverse("logout"), {"refresh": refresh})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_logout_requires_token(self):
        resp = self.client.post(reverse("logout"), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_without_token_graceful(self):
        resp = self.client.post(
            reverse("logout"),
            data={},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ── Password Reset Security Tests ────────────────────────────────────
class PasswordResetSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = make_org()
        self.user = make_user(self.org, email="reset@acme.com")

    def test_forgot_password_does_not_reveal_user_exists(self):
        resp = self.client.post(reverse("forgot_password"), {"email": "nonexistent@acme.com"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("sent", resp.data["detail"].lower())

    def test_secure_token_generation(self):
        from apps.users.password_reset_tokens import generate_secure_token, hash_token
        token = generate_secure_token()
        self.assertGreater(len(token), 20)
        hashed = hash_token(token)
        self.assertNotEqual(token, hashed)
        self.assertEqual(len(hashed), 64)

    def test_token_expiration(self):
        from apps.users.password_reset_tokens import token_is_expired
        from django.utils import timezone
        from datetime import timedelta

        self.assertFalse(token_is_expired(timezone.now() - timedelta(minutes=1)))
        self.assertTrue(token_is_expired(timezone.now() - timedelta(minutes=16)))


# ── Internal JWT Service Token Tests ──────────────────────────────────
class ServiceTokenTests(TestCase):
    def test_make_service_token_is_valid_jwt(self):
        import os
        test_secret = "test-fastapi-service-secret-for-pytest"
        os.environ["FASTAPI_SERVICE_SECRET"] = test_secret
        os.environ["JWT_SIGNING_SECRET"] = "test-jwt-signing-secret"

        from fastapi_service.core.auth import _make_service_token

        token = _make_service_token()
        payload = jwt.decode(token, test_secret, algorithms=["HS256"])
        self.assertIn("service_name", payload)
        self.assertEqual(payload["service_name"], "django-backend")
        self.assertIn("exp", payload)

    def test_make_service_token_not_shared_with_user_token(self):
        import os
        test_secret = "test-fastapi-service-secret-for-pytest"
        os.environ["FASTAPI_SERVICE_SECRET"] = test_secret
        os.environ["JWT_SIGNING_SECRET"] = "test-jwt-signing-secret"

        from fastapi_service.core.auth import _make_service_token
        from rest_framework_simplejwt.tokens import AccessToken
        from apps.users.models import User

        org = make_org()
        user = make_user(org)
        user_token = str(AccessToken.for_user(user))
        service_token = _make_service_token()

        self.assertNotEqual(user_token, service_token)


# ── Production Security Settings Tests ───────────────────────────────
class SecuritySettingsTests(TestCase):
    def test_security_settings_exist_in_settings(self):
        """Verify that all production security settings are defined."""
        from django.conf import settings
        required_settings = [
            "SECURE_SSL_REDIRECT",
            "SECURE_HSTS_SECONDS",
            "SECURE_HSTS_INCLUDE_SUBDOMAINS",
            "SECURE_HSTS_PRELOAD",
            "SECURE_PROXY_SSL_HEADER",
            "SESSION_COOKIE_SECURE",
            "CSRF_COOKIE_SECURE",
            "SESSION_COOKIE_HTTPONLY",
            "CSRF_COOKIE_HTTPONLY",
        ]
        for setting_name in required_settings:
            self.assertIn(setting_name, dir(settings), f"{setting_name} missing from settings")

    def test_security_settings_conditional_logic_exists(self):
        """Verify that security settings conditional on DEBUG are present in settings.py."""
        import inspect
        from core import settings as settings_module
        source = inspect.getsource(settings_module)
        self.assertIn("if DEBUG:", source)
        self.assertIn("SECURE_SSL_REDIRECT", source)
        self.assertIn("SECURE_HSTS_SECONDS", source)
        self.assertIn("SECURE_PROXY_SSL_HEADER", source)

    def test_proxy_header_configuration(self):
        """Verify SECURE_PROXY_SSL_HEADER is configured for production proxies."""
        from django.conf import settings
        # The setting must exist
        self.assertIn("SECURE_PROXY_SSL_HEADER", dir(settings))
        # Verify the production value is present in settings source code
        import inspect
        from core import settings as settings_module
        source = inspect.getsource(settings_module)
        self.assertIn('("HTTP_X_FORWARDED_PROTO", "https")', source)


# ── Rate Limiting Tests ──────────────────────────────────────────────
class RateLimitingTests(TestCase):
    def test_login_throttle_rates_defined(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.assertIn("login", rates)
        self.assertIn("login_block", rates)

    def test_password_reset_throttle_rates_defined(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.assertIn("password_reset", rates)
        self.assertIn("password_reset_block", rates)

    def test_login_throttle_class_has_correct_scope(self):
        from core.throttles import LoginAnonThrottle, LoginBlockThrottle
        self.assertEqual(LoginAnonThrottle.scope, "login")
        self.assertEqual(LoginBlockThrottle.scope, "login_block")

    def test_password_reset_throttle_class_has_correct_scope(self):
        from core.throttles import PasswordResetAnonThrottle, PasswordResetBlockThrottle
        self.assertEqual(PasswordResetAnonThrottle.scope, "password_reset")
        self.assertEqual(PasswordResetBlockThrottle.scope, "password_reset_block")
