"""
Tests for the rate limiting middleware.
"""

import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from core.middleware import RateLimitMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse


@pytest.fixture
def middleware():
    def get_response(request):
        return HttpResponse("Test response")

    return RateLimitMiddleware(get_response)


@pytest.fixture
def auth_request(db):
    factory = RequestFactory()
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
    request = factory.get("/api/games/")
    request.user = user
    return request


@pytest.fixture
def anon_request():
    factory = RequestFactory()
    request = factory.get("/api/games/")
    request.user = AnonymousUser()
    request.META["REMOTE_ADDR"] = "127.0.0.1"
    return request


class TestRateLimitMiddleware:

    def test_non_api_request_bypasses_rate_limiting(self, middleware):
        """Test that non-API requests bypass rate limiting."""
        factory = RequestFactory()
        request = factory.get("/non-api-path/")
        request.user = AnonymousUser()

        response = middleware(request)

        assert response.status_code == 200
        assert response.content.decode() == "Test response"

    def test_excluded_path_bypasses_rate_limiting(self, middleware):
        """Test that excluded paths bypass rate limiting."""
        factory = RequestFactory()
        request = factory.get("/api/health/")
        request.user = AnonymousUser()

        with patch.object(settings, "RATE_LIMIT_EXCLUDED_PATHS", [r"^/api/health/?$"]):
            response = middleware(request)

            assert response.status_code == 200
            assert response.content.decode() == "Test response"

    def test_authenticated_user_rate_limiting(self, middleware, auth_request):
        """Test rate limiting for authenticated users."""
        # Setup endpoint patterns
        with patch.object(middleware, "endpoint_patterns", {"GAME": [r"^/api/games/?$"]}):
            # Mock rate limit check method to not actually rate limit
            with patch.object(middleware, "_is_rate_limited", return_value=False):
                with patch.object(
                    middleware, "_get_rate_limit_config", return_value={"MAX_REQUESTS": 100, "TIME_WINDOW": 3600}
                ):
                    with patch.object(middleware, "_get_remaining_requests", return_value=99):
                        with patch.object(middleware, "_get_reset_time", return_value=3600):
                            response = middleware(auth_request)

                            assert response.status_code == 200
                            assert response.content.decode() == "Test response"

                            # Check rate limit headers
                            assert response["X-RateLimit-Limit"] == "100"
                            assert response["X-RateLimit-Remaining"] == "99"
                            assert response["X-RateLimit-Reset"] == "3600"

    def test_anonymous_user_rate_limiting(self, middleware, anon_request):
        """Test rate limiting for anonymous users (IP-based)."""
        # Setup endpoint patterns
        with patch.object(middleware, "endpoint_patterns", {"GAME": [r"^/api/games/?$"]}):
            # Mock rate limit check method to not actually rate limit
            with patch.object(middleware, "_is_rate_limited", return_value=False):
                with patch.object(
                    middleware, "_get_rate_limit_config", return_value={"MAX_REQUESTS": 100, "TIME_WINDOW": 3600}
                ):
                    with patch.object(middleware, "_get_remaining_requests", return_value=99):
                        with patch.object(middleware, "_get_reset_time", return_value=3600):
                            response = middleware(anon_request)

                            assert response.status_code == 200
                            assert response.content.decode() == "Test response"

                            # Check rate limit headers
                            assert response["X-RateLimit-Limit"] == "100"
                            assert response["X-RateLimit-Remaining"] == "99"
                            assert response["X-RateLimit-Reset"] == "3600"

    def test_rate_limit_exceeded(self, middleware, auth_request):
        """Test when rate limit is exceeded."""
        # Setup endpoint patterns and rate limit config
        with patch.object(middleware, "endpoint_patterns", {"GAME": [r"^/api/games/?$"]}):
            # Mock rate limit check method to indicate rate limit exceeded
            with patch.object(middleware, "_is_rate_limited", return_value=True):
                with patch.object(middleware, "_get_reset_time", return_value=3600):
                    with patch("core.middleware.create_error_response") as mock_error:
                        mock_error.return_value = HttpResponse("Rate limit exceeded", status=429)
                        response = middleware(auth_request)

                        assert response.status_code == 429
                        assert response.content.decode() == "Rate limit exceeded"

                        mock_error.assert_called_once_with(
                            error_type="rate_limit_exceeded",
                            message="Rate limit exceeded. Please try again in 3600 seconds.",
                            status_code=429,
                            details={"reset_time": 3600, "endpoint_type": "GAME"},
                        )

    def test_get_endpoint_type(self, middleware):
        """Test the _get_endpoint_type method."""
        # Setup patterns
        middleware.endpoint_patterns = {
            "AUTH": [r"^/api/login/?$", r"^/api/register/?$"],
            "GAME": [r"^/api/games/?$"],
            "ANALYSIS": [r"^/api/games/\d+/analyze/?$"],
        }

        # Test matching
        assert middleware._get_endpoint_type("/api/login/") == "AUTH"
        assert middleware._get_endpoint_type("/api/register/") == "AUTH"
        assert middleware._get_endpoint_type("/api/games/") == "GAME"
        assert middleware._get_endpoint_type("/api/games/123/analyze/") == "ANALYSIS"

        # Test default
        assert middleware._get_endpoint_type("/api/unknown/") == "DEFAULT"

    def test_rate_limit_config(self, middleware):
        """Test getting rate limit configuration."""
        # Setup rate limit config
        test_config = {
            "DEFAULT": {"MAX_REQUESTS": 100, "TIME_WINDOW": 3600},
            "AUTH": {"MAX_REQUESTS": 5, "TIME_WINDOW": 300},
            "ANALYSIS": {"MAX_REQUESTS": 10, "TIME_WINDOW": 600},
        }

        with patch.object(settings, "RATE_LIMIT_CONFIG", test_config):
            # Get config for AUTH endpoint
            config = middleware._get_rate_limit_config("AUTH")
            assert config == test_config["AUTH"]

            # Get config for non-existent endpoint (should use DEFAULT)
            config = middleware._get_rate_limit_config("NONEXISTENT")
            assert config == test_config["DEFAULT"]

    def test_is_rate_limited(self, middleware):
        """Test the _is_rate_limited method."""
        # Clear cache
        cache.clear()

        # Setup rate limit config
        test_config = {"DEFAULT": {"MAX_REQUESTS": 3, "TIME_WINDOW": 3600}}

        with patch.object(settings, "RATE_LIMIT_CONFIG", test_config):
            key = "test:rate:limit"

            # First few requests should not be rate limited
            assert middleware._is_rate_limited(key, "DEFAULT") is False
            assert middleware._is_rate_limited(key, "DEFAULT") is False
            assert middleware._is_rate_limited(key, "DEFAULT") is False

            # Next request should be rate limited
            assert middleware._is_rate_limited(key, "DEFAULT") is True

    def test_get_remaining_requests(self, middleware):
        """Test the _get_remaining_requests method."""
        # Clear cache
        cache.clear()

        # Setup rate limit config
        test_config = {"DEFAULT": {"MAX_REQUESTS": 5, "TIME_WINDOW": 3600}}

        with patch.object(settings, "RATE_LIMIT_CONFIG", test_config):
            key = "test:remaining:requests"

            # Initial remaining should be max requests
            assert middleware._get_remaining_requests(key, "DEFAULT") == 5

            # Make some requests
            middleware._is_rate_limited(key, "DEFAULT")
            assert middleware._get_remaining_requests(key, "DEFAULT") == 4

            middleware._is_rate_limited(key, "DEFAULT")
            assert middleware._get_remaining_requests(key, "DEFAULT") == 3

    def test_get_reset_time(self, middleware):
        """Test the _get_reset_time method."""
        # Setup rate limit config
        test_config = {"DEFAULT": {"MAX_REQUESTS": 5, "TIME_WINDOW": 60}}

        with patch.object(settings, "RATE_LIMIT_CONFIG", test_config):
            key = "test:reset:time"

            # Set a fake current time to make testing deterministic
            current_time = 1000.0  # 1000 seconds since epoch

            with patch("datetime.datetime.utcnow") as mock_utcnow:
                # Mock timestamp to return fixed time
                mock_date = MagicMock()
                mock_date.timestamp.return_value = current_time
                mock_utcnow.return_value = mock_date

                # Reset time should be less than or equal to the window
                reset_time = middleware._get_reset_time(key, "DEFAULT")
                assert 0 <= reset_time <= 60
