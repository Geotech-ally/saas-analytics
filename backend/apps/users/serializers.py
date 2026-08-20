from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.organizations.models import Organization

User = get_user_model()


class OrganizationBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "plan"]


class UserSerializer(serializers.ModelSerializer):
    organization = OrganizationBriefSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "role", "organization", "is_active", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Used ONLY by UserViewSet's admin-gated `create` action (POST /users/),
    where an existing org admin invites a teammate into their OWN org.
    That endpoint's permission_classes ([IsAuthenticated, IsAdminOrReadOnly])
    already restrict who can call it, and UserViewSet.perform_create()
    assigns the new user to the calling admin's organization automatically.

    Deliberately excludes `organization_id` (nobody should be able to name
    an arbitrary org to join) and `role` (new members always start as USER;
    promote via the admin-only /users/{id}/set_role/ endpoint).
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name"]

    def validate(self, attrs):
        if attrs["password"] != attrs.get("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        attrs.pop("password_confirm", None)
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    """
    Used ONLY by the public, unauthenticated RegisterView (POST /auth/register/).

    SECURITY: this must never expose `role` or `organization_id`. The
    previous version of this serializer let anyone self-registering supply
    BOTH fields, which meant any anonymous visitor could type in ANY
    existing organization's UUID (which the old Register.tsx form even
    surfaced as a plain "Organization ID (optional)" text box) and set
    role="admin" in the same request — instantly joining a stranger's
    workspace as a full admin with no invitation or verification at all.

    Public self-registration now ALWAYS creates a brand-new organization for
    the signing-up user, who always starts as role=USER (the model default).
    Joining an *existing* org must go through the admin-gated invite flow
    (UserViewSet.create, using UserCreateSerializer above) instead.
    """
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=False)
    # Accept dj_rest_auth / allauth default field names as aliases so existing
    # clients/tests that send password1/password2 still work.
    password1 = serializers.CharField(write_only=True, required=False)
    password2 = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name", "password1", "password2"]

    def to_internal_value(self, data):
        # Django test client (and form submissions) arrive as QueryDict, where
        # unpacking preserves list values. Convert to a plain dict first so
        # field validation sees strings, not lists.
        if hasattr(data, "dict"):
            data = data.dict()
        else:
            data = dict(data)
        # Map dj_rest_auth default aliases to canonical names BEFORE field
        # validation runs, so the required checks see the right keys.
        if "password1" in data and "password" not in data:
            data = {**data, "password": data["password1"]}
        if "password2" in data and "password_confirm" not in data:
            data = {**data, "password_confirm": data["password2"]}
        return super().to_internal_value(data)

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")
        if not password or not password_confirm:
            raise serializers.ValidationError("Password fields are required.")
        if password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def save(self, request=None):
        user = self.create(self.validated_data)
        return user

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        validated_data.pop("password1", None)
        validated_data.pop("password2", None)
        user = User.objects.create_user(**validated_data)

        # Every public sign-up gets its own fresh organization.
        email = (user.email or "").lower().strip()
        domain = email.split("@", 1)[-1] if "@" in email else "workspace"

        base_slug = domain.replace(".", "-").replace("_", "-")
        base_slug = "".join(ch for ch in base_slug if ch.isalnum() or ch == "-").strip("-")
        if not base_slug:
            base_slug = "workspace"

        name = f"{domain} Workspace"

        slug = base_slug
        i = 1
        while Organization.objects.filter(slug=slug, is_active=True).exists():
            i += 1
            slug = f"{base_slug}-{i}"

        new_org = Organization.objects.create(name=name, slug=slug)
        user.organization = new_org
        user.save(update_fields=["organization"])
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Self-service profile update (used by PATCH /users/me/ and by admins
    editing other users via the ModelViewSet). Deliberately excludes `role`:
    a user must never be able to grant themselves admin by PATCHing their
    own profile. Role changes go through UserRoleUpdateSerializer, which is
    only reachable behind IsOrganizationAdmin.
    """
    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class UserRoleUpdateSerializer(serializers.ModelSerializer):
    """Admin-only: change another user's role. Never expose this on /me/."""
    class Meta:
        model = User
        fields = ["role"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Normalize email
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    uid = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs.pop("new_password_confirm"):
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs
