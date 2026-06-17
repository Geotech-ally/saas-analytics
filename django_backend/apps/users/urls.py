from django.urls import path

from .logout import LogoutView


urlpatterns = [
    path("api/v1/auth/logout/", LogoutView.as_view(), name="logout"),
]


