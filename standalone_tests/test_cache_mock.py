"""Test module for demonstrating Redis mocking in tests."""

import json
from unittest.mock import MagicMock, patch

import pytest


# Simple mock implementation of Redis cache
class MockRedis:
    """Mock Redis implementation for testing."""

    def __init__(self):
        self.data = {}
        self.expired_keys = set()

    def get(self, key):
        """Get a value from the cache."""
        if key in self.expired_keys:
            return None
        return self.data.get(key)

    def set(self, key, value, ex=None):
        """Set a value in the cache with optional expiration."""
        self.data[key] = value
        # In a real implementation, we'd handle expiration with a timer
        # For testing, we'll just record that it was set with expiration
        return True

    def delete(self, key):
        """Delete a key from the cache."""
        if key in self.data:
            del self.data[key]
            return 1
        return 0

    def expire(self, key, seconds):
        """Set a key to expire in the given number of seconds."""
        self.expired_keys.add(key)
        return True

    def keys(self, pattern):
        """Get all keys matching a pattern."""
        # Simple pattern matching for testing
        if pattern == "*":
            return list(self.data.keys())

        # Handle patterns like "user:*"
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.data.keys() if k.startswith(prefix)]

        # For exact matches
        if pattern in self.data:
            return [pattern]

        return []

    def flushall(self):
        """Remove all keys."""
        self.data = {}
        self.expired_keys = set()
        return True


# Simple cache implementation to test
class SimpleCache:
    """A simple cache implementation to demonstrate testing with Redis mocks."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour

    def get(self, key, default=None):
        """Get a value from the cache."""
        data = self.redis.get(key)
        if data is None:
            return default

        # Handle JSON deserialization
        if isinstance(data, bytes):
            try:
                return json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return data
        else:
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data

    def set(self, key, value, ttl=None):
        """Set a value in the cache with optional time-to-live."""
        if ttl is None:
            ttl = self.default_ttl

        # Convert complex types to JSON
        if not isinstance(value, (str, bytes)):
            value = json.dumps(value)

        return self.redis.set(key, value, ex=ttl)

    def delete(self, key):
        """Delete a key from cache."""
        return self.redis.delete(key)

    def clear_all(self):
        """Clear all cache entries."""
        return self.redis.flushall()

    def get_by_pattern(self, pattern):
        """Get all keys matching a pattern."""
        keys = self.redis.keys(pattern)
        result = {}
        for key in keys:
            result[key] = self.get(key)
        return result


# Tests
@pytest.fixture
def mock_redis():
    """Create a mock Redis instance for testing."""
    return MockRedis()


@pytest.fixture
def cache(mock_redis):
    """Create a SimpleCache instance with a mock Redis."""
    return SimpleCache(mock_redis)


def test_cache_set_and_get(cache):
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
        cache.set(key, value)

        # Get the value
        result = cache.get(key)

        # Check it matches
        assert result == value, f"Cache did not return the correct value for {key}"


def test_cache_delete(cache):
    """Test deleting values from the cache."""
    # Set some values
    cache.set("key1", "value1")
    cache.set("key2", "value2")

    # Verify they're set
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"

    # Delete one key
    cache.delete("key1")

    # Verify it's gone
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"


def test_cache_pattern_matching(cache):
    """Test retrieving values by pattern."""
    # Set some values with a common prefix
    cache.set("user:1", {"name": "Alice"})
    cache.set("user:2", {"name": "Bob"})
    cache.set("product:1", {"name": "Widget"})

    # Get all user entries
    user_entries = cache.get_by_pattern("user:*")

    # Verify we get the expected keys
    assert len(user_entries) == 2
    assert "user:1" in user_entries
    assert "user:2" in user_entries
    assert user_entries["user:1"]["name"] == "Alice"
    assert user_entries["user:2"]["name"] == "Bob"


def test_cache_with_patched_redis():
    """Test the cache using patch to mock Redis."""
    # Create a mock for Redis
    mock_client = MagicMock()

    # Configure the mock to return values
    mock_client.get.return_value = json.dumps({"name": "Mock Value"})
    mock_client.set.return_value = True

    # Create the cache with our mock
    cache = SimpleCache(mock_client)

    # Test getting a value
    result = cache.get("test_key")

    # Verify the mock was called correctly
    mock_client.get.assert_called_once_with("test_key")

    # Verify we got the expected result
    assert result == {"name": "Mock Value"}
