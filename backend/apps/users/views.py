import logging
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.permissions import IsOrganizationAdmin, IsSameOrganization, IsAdminOrReadOnly
from core.throttles import LoginAnonThrottle, LoginBlockThrottle, PasswordResetAnonThrottle, PasswordResetBlockThrottle
from .claims import build_user_claims, issue_user_tokens
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    RegisterSerializer,
    UserUpdateSerializer,
    UserRoleUpdateSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from .password_reset_tokens import (
    generate_secure_token,
    hash_token,
    token_is_expired,
)
from .models import PasswordResetToken

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        _, refresh = issue_user_tokens(user)
        return refresh


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginAnonThrottle, LoginBlockThrottle]


class UserViewSet(ModelViewSet):
    queryset = User.objects.select_related("organization").all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        if self.action == "set_role":
            return UserRoleUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(organization=user.organization)

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save()
        if user.organization:
            instance.organization = user.organization
            instance.save(update_fields=["organization"])

    @action(detail=False, methods=["get", "patch"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if request.method == "GET":
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated successfully."})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsOrganizationAdmin])
    def set_role(self, request, pk=None):
        target_user = self.get_object()
        if target_user.organization_id != request.user.organization_id:
            return Response(
                {"detail": "You cannot modify users in another organization."},
                status=status.HTTP_403_FORBIDDEN,
            )
        old_role = target_user.role
        serializer = UserRoleUpdateSerializer(target_user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data.get("role", old_role)
        if old_role != new_role:
            logger.warning(
                "Role changed by %s for user %s: %s -> %s in org %s",
                request.user.email,
                target_user.email,
                old_role,
                new_role,
                target_user.organization_id,
            )
        serializer.save()
        return Response(UserSerializer(target_user).data)


class RegisterView(generics.CreateAPIView):
    """Public endpoint: register a new user + a brand-new organization for them.

    Uses RegisterSerializer specifically — never UserCreateSerializer — so
    role and organization_id can never be supplied by an anonymous caller.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetAnonThrottle, PasswordResetBlockThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email, is_active=True)

            raw_token = generate_secure_token()
            token_hash = hash_token(raw_token)

            PasswordResetToken.objects.filter(user=user).delete()

            PasswordResetToken.objects.create(
                user=user,
                token_hash=token_hash,
                expires_at=timezone.now() + timezone.timedelta(minutes=15),
                used=False,
            )

            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3002")
            reset_url = f"{frontend_url}/reset-password?uid={urlsafe_base64_encode(force_bytes(str(user.pk)))}&token={raw_token}"

            subject = "Password Reset Request"
            message = f"""Hello {user.full_name},

You requested a password reset for your account. Click the link below to reset your password:

{reset_url}

This link will expire in 15 minutes.

If you did not request this, please ignore this email and ensure your password is secure.

Best regards,
DataLens Team""".strip()

            send_mail(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@datalens.com"),
                [user.email],
                fail_silently=False,
            )
            logger.info("Password reset email sent to %s", email)

        except User.DoesNotExist:
            pass

        return Response(
            {"detail": "If an account exists with this email, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetAnonThrottle, PasswordResetBlockThrottle]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        raw_token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_hash = hash_token(raw_token)

        try:
            reset_record = PasswordResetToken.objects.get(user=user, token_hash=token_hash)
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reset_record.used:
            return Response(
                {"detail": "This token has already been used."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if token_is_expired(reset_record.created_at):
            reset_record.delete()
            return Response(
                {"detail": "This token has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        reset_record.used = True
        reset_record.save(update_fields=["used"])

        from django.contrib.sessions.models import Session
        Session.objects.filter(session_data__contains=user_id).delete()

        logger.info("Password reset completed for user %s", user.email)

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
