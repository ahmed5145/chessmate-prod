"""
Tests for the health check endpoints.

This module contains tests for the health check endpoints in the ChessMate application.
"""

import json
from unittest.mock import MagicMock, patch

from core.health_checks import (
    STATUS_CRITICAL,
    STATUS_OK,
    STATUS_UNKNOWN,
    STATUS_WARNING,
    check_cache,
    check_celery,
    check_database,
    check_redis,
    check_storage,
    get_system_info,
    run_all_checks,
)
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse


class HealthEndpointsTestCase(TestCase):
    """Test health check endpoints."""

    def setUp(self):
        """Set up the test client."""
        self.client = Client()

    @patch("core.health_checks.check_database")
    @patch("core.health_checks.check_cache")
    @patch("core.health_checks.check_redis")
    def test_basic_health_check(self, mock_check_redis, mock_check_cache, mock_check_db):
        """Test the basic health check endpoint."""
        # Configure mocks
        mock_check_db.return_value = {"status": STATUS_OK}
        mock_check_cache.return_value = {"status": STATUS_OK}
        mock_check_redis.return_value = {"status": STATUS_OK}

        # Call the endpoint
        response = self.client.get("/health/")

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "ok")

    @patch("core.health_checks.check_database")
    @patch("core.health_checks.check_cache")
    @patch("core.health_checks.check_redis")
    def test_readiness_check(self, mock_check_redis, mock_check_cache, mock_check_db):
        """Test the readiness check endpoint."""
        # Configure mocks
        mock_check_db.return_value = {"status": STATUS_OK}
        mock_check_cache.return_value = {"status": STATUS_OK}
        mock_check_redis.return_value = {"status": STATUS_OK}

        # Call the endpoint
        response = self.client.get("/readiness/")

        # Verify response
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content["status"], "ready")

    @patch("core.health_checks.check_database")
    def test_readiness_check_with_db_failure(self, mock_check_db):
        """Test the readiness check with database failure."""
        # Configure mock to simulate database failure
        mock_check_db.return_value = {"status": STATUS_CRITICAL, "message": "Database error: connection refused"}

        # Call the endpoint
        response = self.client.get("/readiness/")

        # Verify response
        self.assertEqual(response.status_code, 503)
        content = json.loads(response.content)
        self.assertEqual(content["status"], "not_ready")
        self.assertIn("Database error", content["message"])

    @patch("core.health_checks.run_all_checks")
    @patch("core.health_checks.get_system_info")
    def test_detailed_health_check(self, mock_get_system_info, mock_run_all_checks):
        """Test the detailed health check endpoint."""
        # Configure mocks
        mock_run_all_checks.return_value = {
            "status": STATUS_OK,
            "checks": {
                "database": {"status": STATUS_OK, "message": "Database is operational"},
                "cache": {"status": STATUS_OK, "message": "Cache is operational"},
                "redis": {"status": STATUS_OK, "message": "Redis is operational"},
            },
        }
        mock_get_system_info.return_value = {
            "platform": "Test Platform",
            "python_version": "3.10.0",
            "django_version": "4.2.0",
        }

        # Call the endpoint
        response = self.client.get("/api/v1/health/detailed/")

        # Verify response
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content["status"], STATUS_OK)
        self.assertIn("checks", content)
        self.assertIn("system_info", content)

    @patch("core.health_checks.run_all_checks")
    def test_detailed_health_check_with_warning(self, mock_run_all_checks):
        """Test the detailed health check with a warning status."""
        # Configure mock to return a warning
        mock_run_all_checks.return_value = {
            "status": STATUS_WARNING,
            "checks": {
                "database": {"status": STATUS_OK, "message": "Database is operational"},
                "redis": {"status": STATUS_WARNING, "message": "Redis is slow (took 0.6s)"},
            },
        }

        # Call the endpoint
        response = self.client.get("/api/v1/health/detailed/")

        # Verify response
        self.assertEqual(response.status_code, 207)  # Multi-status
        content = json.loads(response.content)
        self.assertEqual(content["status"], STATUS_WARNING)

    @patch("core.health_checks.run_all_checks")
    def test_detailed_health_check_with_critical(self, mock_run_all_checks):
        """Test the detailed health check with a critical status."""
        # Configure mock to return a critical status
        mock_run_all_checks.return_value = {
            "status": STATUS_CRITICAL,
            "checks": {
                "database": {"status": STATUS_CRITICAL, "message": "Database error: connection refused"},
            },
        }

        # Call the endpoint
        response = self.client.get("/api/v1/health/detailed/")

        # Verify response
        self.assertEqual(response.status_code, 503)  # Service Unavailable
        content = json.loads(response.content)
        self.assertEqual(content["status"], STATUS_CRITICAL)
