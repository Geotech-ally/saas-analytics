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
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    # Optional during signup: if provided, user joins existing org;
    # if omitted/blank, we auto-create a new organization.
    organization_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)



    class Meta:
        model = User
        fields = [
            "email", "password", "password_confirm",
            "first_name", "last_name", "role", "organization_id",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.get("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        attrs.pop("password_confirm", None)
        return attrs


    def validate_organization_id(self, value):
        # Allow blank/None so we can auto-create an org.
        if value in (None, ""):
            return None
        try:
            return Organization.objects.get(id=value, is_active=True)
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Organization not found or inactive.")


    def create(self, validated_data):
        org = validated_data.pop("organization_id", None)

        user = User.objects.create_user(**validated_data)

        if org is not None:
            user.organization = org
            user.save(update_fields=["organization"])
            return user

        # Auto-create organization (required for "organization_id optional" flow)
        email = (user.email or "").lower().strip()
        domain = email.split("@", 1)[-1] if "@" in email else "workspace"

        # Derive name/slug and ensure slug uniqueness.
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
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role"]

    def validate_role(self, value):
        # Only org admins can change roles — enforced at view/permission level too
        return value


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
