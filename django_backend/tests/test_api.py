"""
Django test suite.
Run: python manage.py test tests
"""
from django.test import TestCase
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
    resp = client.post(reverse("token_obtain"), {"email": email, "password": password})
    return resp.data


# ── Auth Tests ─────────────────────────────────────────────────────────────
class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = make_org()
        self.user = make_user(self.org, email="auth@acme.com")

    def test_obtain_token_success(self):
        resp = self.client.post(reverse("token_obtain"), {"email": "auth@acme.com", "password": "Test1234!"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_obtain_token_bad_credentials(self):
        resp = self.client.post(reverse("token_obtain"), {"email": "auth@acme.com", "password": "wrong"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        resp = self.client.get(reverse("user-me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_user(self):
        tokens = get_tokens(self.client, "auth@acme.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = self.client.get(reverse("user-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "auth@acme.com")

    def test_register_new_user(self):
        payload = {
            "email": "new@acme.com",
            "password": "StrongPass1!",
            "password_confirm": "StrongPass1!",
            "first_name": "New",
            "last_name": "User",
        }
        resp = self.client.post(reverse("register"), payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@acme.com").exists())

    def test_register_password_mismatch(self):
        payload = {
            "email": "bad@acme.com",
            "password": "StrongPass1!",
            "password_confirm": "DifferentPass1!",
        }
        resp = self.client.post(reverse("register"), payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_contains_custom_claims(self):
        import jwt
        from django.conf import settings
        tokens = get_tokens(self.client, "auth@acme.com")
        payload = jwt.decode(tokens["access"], settings.SECRET_KEY, algorithms=["HS256"])
        self.assertIn("role", payload)
        self.assertIn("org_id", payload)
        self.assertIn("email", payload)


# ── Organization Tests ─────────────────────────────────────────────────────
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
        resp = self.client.get(reverse("organization-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_member_can_read_org(self):
        self._auth("member@acme.com")
        resp = self.client.get(reverse("organization-list"))
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
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ── User Management Tests ──────────────────────────────────────────────────
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
        emails = [u["email"] for u in resp.data["results"]]
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
        emails = [u["email"] for u in resp.data["results"]]
        self.assertNotIn("b@orgb.com", emails)

    def test_user_a_cannot_see_org_b(self):
        self._auth("a@orga.com")
        resp = self.client.get(reverse("organization-detail", args=[self.org_b.id]))
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
