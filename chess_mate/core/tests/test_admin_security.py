"""Tests for hardened Django admin access."""

from unittest.mock import patch

import pytest
from core.admin_security import (
    AdminSecurityMiddleware,
    admin_login_rate_limit_exceeded,
    get_client_ip,
    is_admin_path,
    is_legacy_admin_path,
    resolve_admin_path,
)
from django.http import HttpResponse
from django.test import RequestFactory, override_settings


class TestAdminPathHelpers:
    def test_resolve_admin_path_allows_default_in_tests(self):
        assert resolve_admin_path(is_production=True, testing=True, configured="admin") == "admin"

    def test_resolve_admin_path_requires_secret_in_production(self):
        with pytest.raises(ValueError, match="DJANGO_ADMIN_PATH must be set"):
            resolve_admin_path(is_production=True, testing=False, configured="")

    def test_resolve_admin_path_rejects_default_admin_in_production(self):
        with pytest.raises(ValueError, match="not allowed"):
            resolve_admin_path(is_production=True, testing=False, configured="admin")

    def test_resolve_admin_path_accepts_custom_secret(self):
        path = resolve_admin_path(is_production=True, testing=False, configured="cm-ops-secret")
        assert path == "cm-ops-secret"

    def test_is_legacy_admin_path(self):
        assert is_legacy_admin_path("/admin")
        assert is_legacy_admin_path("/admin/")
        assert not is_legacy_admin_path("/cm-ops-secret/")

    def test_is_admin_path(self):
        assert is_admin_path("/cm-ops-secret/", "cm-ops-secret")
        assert is_admin_path("/cm-ops-secret", "cm-ops-secret")
        assert not is_admin_path("/admin/", "cm-ops-secret")

    def test_get_client_ip_prefers_forwarded_header(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.10, 10.0.0.1"
        assert get_client_ip(request) == "203.0.113.10"


class TestAdminSecurityMiddleware:
    def setup_method(self):
        self.factory = RequestFactory()
        self.middleware = AdminSecurityMiddleware(lambda request: HttpResponse("ok"))

    @override_settings(ADMIN_HIDE_LEGACY_PATH=True, DJANGO_ADMIN_PATH="cm-ops-secret", ADMIN_ALLOWED_IPS=[])
    def test_legacy_admin_path_returns_404(self):
        request = self.factory.get("/admin/")
        response = self.middleware.process_request(request)
        assert response.status_code == 404

    @override_settings(ADMIN_HIDE_LEGACY_PATH=False, DJANGO_ADMIN_PATH="admin", ADMIN_ALLOWED_IPS=[])
    def test_legacy_admin_path_allowed_when_not_hidden(self):
        request = self.factory.get("/admin/")
        response = self.middleware.process_request(request)
        assert response is None

    @override_settings(DJANGO_ADMIN_PATH="cm-ops-secret", ADMIN_ALLOWED_IPS=["203.0.113.10"])
    def test_admin_ip_allowlist_blocks_unknown_ip(self):
        request = self.factory.get("/cm-ops-secret/")
        request.META["REMOTE_ADDR"] = "198.51.100.20"
        response = self.middleware.process_request(request)
        assert response.status_code == 403

    @override_settings(DJANGO_ADMIN_PATH="cm-ops-secret", ADMIN_ALLOWED_IPS=["203.0.113.10"])
    def test_admin_ip_allowlist_allows_configured_ip(self):
        request = self.factory.get("/cm-ops-secret/")
        request.META["REMOTE_ADDR"] = "203.0.113.10"
        response = self.middleware.process_request(request)
        assert response is None

    @override_settings(
        DJANGO_ADMIN_PATH="cm-ops-secret",
        ADMIN_ALLOWED_IPS=[],
        ADMIN_LOGIN_MAX_ATTEMPTS=2,
        ADMIN_LOGIN_WINDOW_SECONDS=900,
    )
    @patch("core.admin_security.cache_set")
    @patch("core.admin_security.cache_get")
    def test_admin_login_rate_limit(self, mock_cache_get, mock_cache_set):
        attempt_state = {"count": 0}

        def _cache_get(_key, default=0):
            return attempt_state["count"]

        def _cache_set(_key, value, timeout=None):
            attempt_state["count"] = value

        mock_cache_get.side_effect = _cache_get
        mock_cache_set.side_effect = _cache_set

        for _ in range(2):
            request = self.factory.post("/cm-ops-secret/login/", {"username": "x", "password": "y"})
            request.META["REMOTE_ADDR"] = "203.0.113.55"
            response = self.middleware.process_request(request)
            assert response is None

        blocked = self.factory.post("/cm-ops-secret/login/", {"username": "x", "password": "y"})
        blocked.META["REMOTE_ADDR"] = "203.0.113.55"
        response = self.middleware.process_request(blocked)
        assert response.status_code == 403

    def test_admin_login_rate_limit_helper_only_counts_post_login(self):
        request = self.factory.get("/cm-ops-secret/login/")
        assert admin_login_rate_limit_exceeded(request) is False
