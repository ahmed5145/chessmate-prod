"""Tests for Google OAuth sign-in and registration."""

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from ..google_oauth import (
    PREF_GOOGLE_SUB,
    GoogleOAuthError,
    exchange_code_for_userinfo,
    upsert_user_from_google,
)
from ..models import Profile


@pytest.fixture(autouse=True)
def google_oauth_settings(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "test-client-secret"
    settings.FRONTEND_URL = "http://localhost:3000"
    return settings


@pytest.fixture
def google_userinfo():
    return {
        "sub": "google-sub-123",
        "email": "google.user@example.com",
        "email_verified": True,
        "name": "Google User",
    }


@pytest.mark.django_db
class TestGoogleOAuth:
    def test_start_redirects_to_google(self, client):
        url = reverse("google_oauth_start")
        response = client.get(url)

        assert response.status_code == 302
        assert "accounts.google.com/o/oauth2" in response["Location"]
        assert "client_id=test-client-id" in response["Location"]
        assert "state=" in response["Location"]

    def test_start_stores_referral_in_session(self, client):
        client.get(reverse("google_oauth_start"), {"ref": "friend-code"})
        session = client.session
        assert session.get("google_oauth_referral") == "friend-code"

    @patch("core.google_oauth.requests.post")
    @patch("core.google_oauth.requests.get")
    def test_exchange_code_for_userinfo(self, mock_get, mock_post, rf, google_userinfo):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "at-1"})
        mock_get.return_value = MagicMock(status_code=200, json=lambda: google_userinfo)

        request = rf.get("/api/v1/auth/google/callback/")
        request.META["HTTP_HOST"] = "localhost:8000"

        result = exchange_code_for_userinfo(request, "auth-code")

        assert result["email"] == "google.user@example.com"
        mock_post.assert_called_once()
        mock_get.assert_called_once()

    @patch("core.google_oauth.requests.post")
    @patch("core.google_oauth.requests.get")
    def test_exchange_rejects_unverified_email(self, mock_get, mock_post, rf):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "at-1"})
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "sub": "sub-1",
                "email": "noverify@example.com",
                "email_verified": False,
            },
        )

        request = rf.get("/api/v1/auth/google/callback/")
        request.META["HTTP_HOST"] = "localhost:8000"

        with pytest.raises(GoogleOAuthError) as exc:
            exchange_code_for_userinfo(request, "auth-code")
        assert exc.value.code == "email_unverified"

    def test_upsert_creates_verified_user(self, rf, google_userinfo):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        user, created = upsert_user_from_google(request, google_userinfo)

        assert created is True
        assert user.email == "google.user@example.com"
        profile = Profile.objects.get(user=user)
        assert profile.email_verified is True
        assert profile.preferences[PREF_GOOGLE_SUB] == "google-sub-123"
        assert not user.has_usable_password()

    @patch("core.welcome_email.send_welcome_email_once")
    def test_upsert_links_existing_email_user(self, mock_welcome, rf, google_userinfo):
        existing = User.objects.create_user(
            username="existing",
            email="google.user@example.com",
            password="testpassword123",
        )
        profile = Profile.objects.get(user=existing)
        profile.email_verified = False
        profile.save(update_fields=["email_verified", "legacy_rating"])

        request = rf.get("/")
        user, created = upsert_user_from_google(request, google_userinfo)

        assert created is False
        assert user.pk == existing.pk
        profile.refresh_from_db()
        assert profile.email_verified is True
        assert profile.preferences[PREF_GOOGLE_SUB] == "google-sub-123"
        mock_welcome.assert_not_called()

    def test_upsert_logs_in_existing_google_user(self, rf, google_userinfo):
        user = User.objects.create_user(
            username="linked",
            email="google.user@example.com",
            password="testpassword123",
        )
        profile = Profile.objects.get(user=user)
        profile.preferences[PREF_GOOGLE_SUB] = "google-sub-123"
        profile.save(update_fields=["preferences"])

        request = rf.get("/")
        found, created = upsert_user_from_google(request, google_userinfo)

        assert created is False
        assert found.pk == user.pk

    @patch("core.google_oauth.exchange_code_for_userinfo")
    def test_callback_redirects_with_tokens(self, mock_exchange, client, google_userinfo):
        mock_exchange.return_value = google_userinfo
        start = client.get(reverse("google_oauth_start"))
        state = parse_qs(urlparse(start["Location"]).query)["state"][0]

        response = client.get(
            reverse("google_oauth_callback"),
            {"code": "abc", "state": state},
        )

        assert response.status_code == 302
        assert response["Location"].startswith("http://localhost:3000/auth/google/callback#")
        assert "access=" in response["Location"]
        assert "refresh=" in response["Location"]
        assert User.objects.filter(email="google.user@example.com").exists()

    def test_callback_rejects_invalid_state(self, client):
        response = client.get(
            reverse("google_oauth_callback"),
            {"code": "abc", "state": "wrong"},
        )

        assert response.status_code == 302
        assert "error=invalid_state" in response["Location"]

    @patch("core.google_oauth.exchange_code_for_userinfo")
    def test_callback_handles_access_denied(self, mock_exchange, client):
        response = client.get(
            reverse("google_oauth_callback"),
            {"error": "access_denied"},
        )

        assert response.status_code == 302
        assert "error=access_denied" in response["Location"]
        mock_exchange.assert_not_called()
