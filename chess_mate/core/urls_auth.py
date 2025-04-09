"""
URL configuration for authentication-related endpoints.
"""

from django.urls import path

from . import auth_views

urlpatterns = [
    path("register/", auth_views.register_view, name="register"),
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("token/refresh/", auth_views.token_refresh_view, name="token_refresh"),
    path("reset-password/", auth_views.request_password_reset, name="request_password_reset"),
    path("reset-password/confirm/", auth_views.reset_password, name="reset_password"),
    path("verify-email/<str:uidb64>/<str:token>/", auth_views.verify_email, name="verify_email"),
    path("csrf/", auth_views.csrf, name="csrf"),
    path("test-auth/", auth_views.test_authentication, name="test_authentication"),
    path("simple-auth/", auth_views.simple_test_auth, name="simple_test_auth"),
]
