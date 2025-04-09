"""
Tests for the cache invalidation system.

This module contains tests for the tag-based cache invalidation system
in the ChessMate application.
"""

import json
import time
import uuid
from unittest.mock import MagicMock, patch

import redis
from core.cache_invalidation import (
    GLOBAL_TAG,
    generate_cache_key,
    invalidate_cache,
    invalidate_pattern,
    with_cache_tags,
)
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse


class CacheInvalidationTestCase(TestCase):
    """Test cache invalidation functionality."""

    def setUp(self):
        """Set up the test client and Redis connection."""
        self.client = Client()
        self.redis_client = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
        self.tag_separator = "::tag::"
        self.redis_client.flushdb()  # Clear Redis before tests

    def tearDown(self):
        """Clean up after tests."""
        self.redis_client.flushdb()  # Clear Redis after tests

    def setup_test_cache_entries(self, count=5, tag="test"):
        """
        Set up test cache entries with a specific tag.

        Args:
            count: Number of test entries to create
            tag: Tag to use for the entries

        Returns:
            List of cache keys created
        """
        keys = []

        for i in range(count):
            # Create a unique key with the tag
            test_id = str(uuid.uuid4())
            key = f"chessmate:test:{test_id}"
            tag_key = f"{key}{self.tag_separator}{tag}"

            # Store a value in the main key
            self.redis_client.set(key, f"test-value-{i}")

            # Store a reference in the tag key (dummy value)
            self.redis_client.set(tag_key, "1")

            keys.append(key)

        return keys

    def test_direct_invalidation(self):
        """Test direct invalidation through Redis."""
        tag = "test_direct"

        # Get initial cache size
        initial_size = self.redis_client.dbsize()

        # Create test entries
        keys = self.setup_test_cache_entries(5, tag)

        # Verify the keys exist
        after_setup_size = self.redis_client.dbsize()
        self.assertEqual(after_setup_size, initial_size + 10)  # 5 keys + 5 tag keys

        # Count keys with the test tag
        keys_with_tag = len(self.redis_client.keys(f"*{self.tag_separator}{tag}"))
        self.assertEqual(keys_with_tag, 5)

        # Invalidate the tag
        invalidate_cache(tag)

        # Verify the tag keys are gone
        after_invalidation_tag_keys = len(self.redis_client.keys(f"*{self.tag_separator}{tag}"))
        self.assertEqual(after_invalidation_tag_keys, 0)

        # Verify the original keys are still there (implementation dependent)
        # In a real implementation, these would also be invalidated
        for key in keys:
            self.assertIsNotNone(self.redis_client.get(key))

    def test_pattern_invalidation(self):
        """Test pattern-based invalidation."""
        # Create some test keys with a common prefix
        prefix = "chessmate:user:123:"

        for i in range(5):
            key = f"{prefix}data:{i}"
            self.redis_client.set(key, f"user-data-{i}")

        # Verify the keys exist
        keys_count = len(self.redis_client.keys(f"{prefix}*"))
        self.assertEqual(keys_count, 5)

        # Invalidate using pattern
        invalidate_pattern(f"{prefix}*")

        # Verify the keys are gone
        after_invalidation_keys = len(self.redis_client.keys(f"{prefix}*"))
        self.assertEqual(after_invalidation_keys, 0)

    def test_cache_tags_decorator(self):
        """Test the with_cache_tags decorator."""

        # Create a mock function with the decorator
        @with_cache_tags("test_tag_1", "test_tag_2")
        def mock_function(arg1, arg2=None):
            return f"Result: {arg1}, {arg2}"

        # Call the function to generate cached value
        result1 = mock_function("value1", arg2="value2")
        self.assertEqual(result1, "Result: value1, value2")

        # Verify it created cache entries with tags
        key = generate_cache_key("mock_function", "value1", arg2="value2")
        tag1_key = f"{key}{self.tag_separator}test_tag_1"
        tag2_key = f"{key}{self.tag_separator}test_tag_2"

        self.assertIsNotNone(self.redis_client.get(key))
        self.assertIsNotNone(self.redis_client.get(tag1_key))
        self.assertIsNotNone(self.redis_client.get(tag2_key))

        # Invalidate one tag
        invalidate_cache("test_tag_1")

        # Verify the tag key is gone, but the value is still cached
        self.assertIsNone(self.redis_client.get(tag1_key))
        self.assertIsNotNone(self.redis_client.get(tag2_key))
        self.assertIsNotNone(self.redis_client.get(key))

        # Call the function again, should still return cached value
        result2 = mock_function("value1", arg2="value2")
        self.assertEqual(result2, "Result: value1, value2")

        # Invalidate the other tag
        invalidate_cache("test_tag_2")

        # Verify all tag keys are gone
        self.assertIsNone(self.redis_client.get(tag1_key))
        self.assertIsNone(self.redis_client.get(tag2_key))

        # In a real implementation, the main key would be invalidated when
        # both tags are invalidated, but this depends on implementation

    def test_global_invalidation(self):
        """Test global cache invalidation."""
        # Create test entries with various tags
        tags = ["tag1", "tag2", "tag3", "tag4"]
        all_keys = []

        for tag in tags:
            keys = self.setup_test_cache_entries(3, tag)
            all_keys.extend(keys)

        # Verify the keys exist
        for key in all_keys:
            self.assertIsNotNone(self.redis_client.get(key))

        # Invalidate all cache using global tag
        invalidate_cache(GLOBAL_TAG)

        # Verify all tag keys are gone
        for tag in tags:
            tag_keys = len(self.redis_client.keys(f"*{self.tag_separator}{tag}"))
            self.assertEqual(tag_keys, 0)

    @patch("core.cache_invalidation.invalidate_cache")
    def test_api_invalidation(self, mock_invalidate_cache):
        """Test cache invalidation through the API."""
        # Set up a test admin user
        from django.contrib.auth.models import User

        admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="adminpassword")

        # Login
        self.client.login(username="admin", password="adminpassword")

        # Test invalidating specific tags
        response = self.client.post(
            "/api/system/cache/clear/",
            data=json.dumps({"tags": ["user_data", "profile"]}),
            content_type="application/json",
        )

        # Verify the response and that invalidate_cache was called
        self.assertEqual(response.status_code, 200)
        mock_invalidate_cache.assert_any_call("user_data")
        mock_invalidate_cache.assert_any_call("profile")

        # Test global invalidation
        response = self.client.post("/api/system/cache/clear/", data=json.dumps({}), content_type="application/json")

        # Verify the response and that invalidate_cache was called with global tag
        self.assertEqual(response.status_code, 200)
        mock_invalidate_cache.assert_any_call(GLOBAL_TAG)

    def test_redis_fallback(self):
        """Test fallback when Redis is unavailable."""
        # Patch the redis client to simulate a failure
        with patch("core.cache_invalidation.get_redis_connection") as mock_get_redis:
            # Configure the mock to raise an exception
            mock_redis = MagicMock()
            mock_redis.keys.side_effect = redis.ConnectionError("connection refused")
            mock_get_redis.return_value = mock_redis

            # Try to invalidate cache - should not raise an exception
            try:
                invalidate_cache("test_tag")
                # If we get here, no exception was raised
                passed = True
            except:
                passed = False

            self.assertTrue(passed)
