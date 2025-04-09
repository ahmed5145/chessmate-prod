"""
Common test fixtures for ChessMate tests.

This module contains fixtures that can be used by both Django-integrated
and standalone tests to provide consistent test functionality.
"""

import json

import fakeredis
import pytest


@pytest.fixture
def redis_mock():
    """
    Provides a fakeredis server instance for tests.

    This is a replacement for the custom MockRedis implementation,
    providing more complete and accurate Redis functionality.
    """
    server = fakeredis.FakeServer()
    redis_client = fakeredis.FakeStrictRedis(server=server)

    # Clear all data before each test
    redis_client.flushall()

    return redis_client


@pytest.fixture
def cache_mock(redis_mock):
    """
    Provides a simple cache implementation using the fakeredis client.

    Args:
        redis_mock: The fakeredis client fixture

    Returns:
        A SimpleCache instance for testing
    """

    class SimpleCache:
        """A simple cache implementation for testing."""

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
                # Convert bytes key to string if needed
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                result[key_str] = self.get(key)
            return result

    return SimpleCache(redis_mock)


@pytest.fixture
def mock_user():
    """
    Create a mock user for testing.

    Returns:
        A dictionary containing user attributes
    """
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
    }


@pytest.fixture
def mock_game():
    """
    Create a mock chess game for testing.

    Returns:
        A dictionary containing game attributes
    """
    return {
        "id": 1,
        "user_id": 1,
        "pgn": '[Event "Test Game"]\n[White "Test User"]\n[Black "Opponent"]\n1. e4 e5 2. Nf3 Nc6',
        "result": "1-0",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T01:00:00Z",
    }
