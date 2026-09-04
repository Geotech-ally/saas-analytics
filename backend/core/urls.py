from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.users.views import (
    UserViewSet,
    ForgotPasswordView,
    ResetPasswordView,
    CustomTokenObtainPairView,
)
from apps.users.views_social import SocialTokenExchangeView
from apps.users.logout import LogoutView

from apps.organizations.views import OrganizationViewSet
from apps.datasets.views import DatasetViewSet, WeeklyReportViewSet, LiveAnalyticsView


def health_check(request):
    return JsonResponse({"status": "ok", "service": "django"})


router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("datasets", DatasetViewSet, basename="dataset")
router.register("weekly-reports", WeeklyReportViewSet, basename="weekly-report")

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("api/v1/analytics/live/", LiveAnalyticsView.as_view(), name="live-analytics"),
    # Custom login with rate limiting (must come before dj_rest_auth to take precedence)
    path("api/v1/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain"),
    # Custom endpoints (must come before dj_rest_auth to take precedence)
    path("api/v1/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/v1/auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("api/v1/auth/reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("api/v1/auth/social/token-exchange/", SocialTokenExchangeView.as_view(), name="social_token_exchange"),
    # dj_rest_auth endpoints (login, register, logout, password reset)
    path("api/v1/auth/", include("dj_rest_auth.urls")),
    path("api/v1/auth/registration/", include("dj_rest_auth.registration.urls")),
]
