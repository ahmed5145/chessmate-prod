"""
Standalone tests for cache functionality.

These tests can run without Django integration.
"""

import json

import pytest

# Mark all tests in this module as standalone
pytestmark = pytest.mark.standalone


class TestCacheOperations:
    """Tests for basic cache operations using fakeredis."""

    def test_cache_set_and_get(self, cache_mock):
        """Test setting and getting values from the cache."""
        # Test with different data types
        test_cases = [
            ("string_key", "string_value"),
            ("int_key", 42),
            ("list_key", [1, 2, 3]),
            ("dict_key", {"name": "Test", "value": 42}),
        ]

        for key, value in test_cases:
            # Set the value
            cache_mock.set(key, value)

            # Get the value
            result = cache_mock.get(key)

            # Check it matches
            assert result == value, f"Cache did not return the correct value for {key}"

    def test_cache_delete(self, cache_mock):
        """Test deleting values from the cache."""
        # Set some values
        cache_mock.set("key1", "value1")
        cache_mock.set("key2", "value2")

        # Verify they're set
        assert cache_mock.get("key1") == "value1"
        assert cache_mock.get("key2") == "value2"

        # Delete one key
        cache_mock.delete("key1")

        # Verify it's gone
        assert cache_mock.get("key1") is None
        assert cache_mock.get("key2") == "value2"

    def test_cache_pattern_matching(self, cache_mock):
        """Test retrieving values by pattern."""
        # Set some values with a common prefix
        cache_mock.set("user:1", {"name": "Alice"})
        cache_mock.set("user:2", {"name": "Bob"})
        cache_mock.set("product:1", {"name": "Widget"})

        # Get all user entries
        user_entries = cache_mock.get_by_pattern("user:*")

        # Verify we get the expected keys
        assert len(user_entries) == 2
        assert "user:1" in user_entries
        assert "user:2" in user_entries
        assert user_entries["user:1"]["name"] == "Alice"
        assert user_entries["user:2"]["name"] == "Bob"

    def test_cache_expiration(self, cache_mock, redis_mock):
        """Test cache expiration functionality."""
        # Set a value with a short TTL
        cache_mock.set("expiring_key", "temp_value", ttl=1)

        # Immediately it should be available
        assert cache_mock.get("expiring_key") == "temp_value"

        # Simulate expiration by manipulating the Redis mock directly
        # (since we can't easily wait for real expiration in tests)
        redis_mock.delete("expiring_key")

        # Now the value should be gone
        assert cache_mock.get("expiring_key") is None

    def test_cache_json_serialization(self, cache_mock):
        """Test serialization and deserialization of JSON data."""
        # Complex nested structure
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
                {"id": 2, "name": "Bob", "roles": ["user"]},
            ],
            "settings": {"theme": "dark", "notifications": True, "limits": {"max_queries": 100, "timeout": 30}},
        }

        # Store in cache
        cache_mock.set("complex_data", complex_data)

        # Retrieve and verify all nested structures are preserved
        result = cache_mock.get("complex_data")

        assert result == complex_data
        assert result["users"][0]["name"] == "Alice"
        assert result["settings"]["limits"]["max_queries"] == 100

    def test_cache_clear_all(self, cache_mock):
        """Test clearing all cache entries."""
        # Set multiple values
        cache_mock.set("key1", "value1")
        cache_mock.set("key2", "value2")
        cache_mock.set("key3", "value3")

        # Verify they're set
        assert cache_mock.get("key1") == "value1"
        assert cache_mock.get("key2") == "value2"
        assert cache_mock.get("key3") == "value3"

        # Clear all
        cache_mock.clear_all()

        # Verify all are gone
        assert cache_mock.get("key1") is None
        assert cache_mock.get("key2") is None
        assert cache_mock.get("key3") is None
