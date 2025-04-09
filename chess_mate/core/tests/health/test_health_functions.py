"""
Tests for the health check functions.

This module contains tests for the individual health check functions in the ChessMate application.
"""

import os
import tempfile
import time
from unittest.mock import MagicMock, patch

from core.health_checks import (
    RESPONSE_TIME_CRITICAL,
    RESPONSE_TIME_WARNING,
    STATUS_CRITICAL,
    STATUS_OK,
    STATUS_UNKNOWN,
    STATUS_WARNING,
    check_cache,
    check_celery,
    check_database,
    check_dns,
    check_external_service,
    check_redis,
    check_storage,
    get_system_info,
    run_all_checks,
)
from django.core.cache import cache
from django.db.utils import OperationalError
from django.test import TestCase
from django.utils import timezone


class HealthFunctionsTestCase(TestCase):
    """Test health check functions."""

    @patch("core.health_checks.connections")
    def test_check_database_success(self, mock_connections):
        """Test database check when database is operational."""
        # Setup mock
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_connection

        # Run the check
        result = check_database()

        # Verify result
        self.assertEqual(result["status"], STATUS_OK)
        self.assertEqual(result["component"], "database")
        self.assertIn("response_time", result)
        self.assertIn("timestamp", result)

    @patch("core.health_checks.connections")
    def test_check_database_error(self, mock_connections):
        """Test database check when database has an error."""
        # Setup mock to raise an exception
        mock_connections.__getitem__.side_effect = OperationalError("connection refused")

        # Run the check
        result = check_database()

        # Verify result
        self.assertEqual(result["status"], STATUS_CRITICAL)
        self.assertEqual(result["component"], "database")
        self.assertIn("Database error", result["message"])

    @patch("core.health_checks.cache")
    def test_check_cache_success(self, mock_cache):
        """Test cache check when cache is operational."""
        # Setup mock
        mock_cache.get.return_value = "test_value"

        # Run the check
        result = check_cache()

        # Verify result
        self.assertEqual(result["status"], STATUS_OK)
        self.assertEqual(result["component"], "cache")

    @patch("core.health_checks.cache")
    def test_check_cache_failure(self, mock_cache):
        """Test cache check when cache retrieval fails."""
        # Setup mock to return None (cache miss)
        mock_cache.get.return_value = None

        # Run the check
        result = check_cache()

        # Verify result
        self.assertEqual(result["status"], STATUS_WARNING)
        self.assertEqual(result["component"], "cache")
        self.assertIn("Cache retrieval failed", result["message"])

    @patch("core.health_checks.cache")
    def test_check_cache_error(self, mock_cache):
        """Test cache check when cache has an error."""
        # Setup mock to raise an exception
        mock_cache.set.side_effect = Exception("connection refused")

        # Run the check
        result = check_cache()

        # Verify result
        self.assertEqual(result["status"], STATUS_CRITICAL)
        self.assertEqual(result["component"], "cache")
        self.assertIn("Cache error", result["message"])

    @patch("core.health_checks.get_redis_connection")
    def test_check_redis_success(self, mock_get_redis):
        """Test Redis check when Redis is operational."""
        # Setup mock
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {"redis_version": "6.2.6"}
        mock_get_redis.return_value = mock_redis

        # Run the check
        result = check_redis()

        # Verify result
        self.assertEqual(result["status"], STATUS_OK)
        self.assertEqual(result["component"], "redis")
        self.assertEqual(result["version"], "6.2.6")

    @patch("core.health_checks.get_redis_connection")
    def test_check_redis_error(self, mock_get_redis):
        """Test Redis check when Redis has an error."""
        # Setup mock to raise an exception
        mock_get_redis.side_effect = Exception("connection refused")

        # Run the check
        result = check_redis()

        # Verify result
        self.assertEqual(result["status"], STATUS_CRITICAL)
        self.assertEqual(result["component"], "redis")
        self.assertIn("Redis error", result["message"])

    def test_check_storage_success(self):
        """Test storage check when storage is accessible."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run the check
            result = check_storage(temp_dir)

            # Verify result
            self.assertEqual(result["status"], STATUS_OK)
            self.assertEqual(result["component"], "storage")
            self.assertEqual(result["path"], temp_dir)

    def test_check_storage_nonexistent(self):
        """Test storage check when path doesn't exist."""
        # Run the check with a non-existent path
        result = check_storage("/nonexistent/path")

        # Verify result
        self.assertEqual(result["status"], STATUS_CRITICAL)
        self.assertEqual(result["component"], "storage")
        self.assertIn("Storage path does not exist", result["message"])

    @patch("core.health_checks.requests.get")
    def test_check_external_service_success(self, mock_get):
        """Test external service check when service is operational."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response

        # Run the check
        result = check_external_service("https://example.com")

        # Verify result
        self.assertEqual(result["status"], STATUS_OK)
        self.assertEqual(result["component"], "external_service")

    @patch("core.health_checks.requests.get")
    def test_check_external_service_error(self, mock_get):
        """Test external service check when service has an error."""
        # Setup mock to raise an exception
        mock_get.side_effect = Exception("connection refused")

        # Run the check
        result = check_external_service("https://example.com")

        # Verify result
        self.assertEqual(result["status"], STATUS_CRITICAL)
        self.assertEqual(result["component"], "external_service")
        self.assertIn("Error connecting to external service", result["message"])

    @patch("core.health_checks.socket.getaddrinfo")
    @patch("core.health_checks.socket.socket")
    def test_check_dns_success(self, mock_socket, mock_getaddrinfo):
        """Test DNS check when hostname is resolvable."""
        # Setup mocks
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("192.0.2.1", 80))]
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock

        # Run the check
        result = check_dns("example.com")

        # Verify result
        self.assertEqual(result["status"], STATUS_OK)
        self.assertEqual(result["component"], "external_service")

    @patch("core.health_checks.socket.getaddrinfo")
    def test_check_dns_resolution_error(self, mock_getaddrinfo):
        """Test DNS check when hostname cannot be resolved."""
        # Setup mock to raise an exception
        mock_getaddrinfo.side_effect = socket.gaierror("name resolution failed")

        # Run the check
        result = check_dns("nonexistent.example.com")

        # Verify result
        self.assertEqual(result["status"], STATUS_CRITICAL)
        self.assertEqual(result["component"], "external_service")
        self.assertIn("DNS resolution failed", result["message"])

    @patch("core.health_checks.check_database")
    @patch("core.health_checks.check_cache")
    @patch("core.health_checks.check_redis")
    def test_run_all_checks(self, mock_check_redis, mock_check_cache, mock_check_db):
        """Test running all health checks."""
        # Setup mocks
        mock_check_db.return_value = {"status": STATUS_OK, "component": "database"}
        mock_check_cache.return_value = {"status": STATUS_OK, "component": "cache"}
        mock_check_redis.return_value = {"status": STATUS_OK, "component": "redis"}

        # Run all checks
        result = run_all_checks()

        # Verify result
        self.assertEqual(result["status"], STATUS_OK)
        self.assertIn("checks", result)
        self.assertIn("database", result["checks"])
        self.assertIn("cache", result["checks"])
        self.assertIn("redis", result["checks"])

    @patch("core.health_checks.check_database")
    @patch("core.health_checks.check_cache")
    def test_run_all_checks_with_failure(self, mock_check_cache, mock_check_db):
        """Test running all health checks with a failure."""
        # Setup mocks
        mock_check_db.return_value = {"status": STATUS_CRITICAL, "component": "database"}
        mock_check_cache.return_value = {"status": STATUS_OK, "component": "cache"}

        # Run all checks
        result = run_all_checks()

        # Verify result
        self.assertEqual(result["status"], STATUS_CRITICAL)

    def test_get_system_info(self):
        """Test getting system information."""
        # Run the function
        result = get_system_info()

        # Verify result
        self.assertIn("platform", result)
        self.assertIn("python_version", result)
        self.assertIn("django_version", result)
        self.assertIn("hostname", result)
        self.assertIn("timestamp", result)
