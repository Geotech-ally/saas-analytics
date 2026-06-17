from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    CustomTokenObtainPairView,
    UserViewSet,
    RegisterView,
    ForgotPasswordView,
    ResetPasswordView,
)
from apps.users.views_social import SocialTokenExchangeView

from apps.organizations.views import OrganizationViewSet
from apps.datasets.views import DatasetViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("datasets", DatasetViewSet, basename="dataset")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("api/v1/auth/register/", RegisterView.as_view(), name="register"),
    path("api/v1/auth/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("api/v1/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("api/v1/auth/reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path(
        "api/v1/auth/social/token-exchange/",
        SocialTokenExchangeView.as_view(),
        name="social_token_exchange",
    ),
    path("api/v1/auth/logout/", include("apps.users.urls")),
]


