"""
Conftest for standalone tests that don't require Django.

This file contains pytest fixtures specific to standalone tests.
"""

import os
import sys

import pytest

# Add the project root to the path for relative imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mark tests in this directory as standalone
pytestmark = [pytest.mark.standalone]


@pytest.fixture
def redis_mock():
    """
    Provides a fakeredis server instance for tests.

    This is a replacement for the custom MockRedis implementation,
    providing more complete and accurate Redis functionality.
    """
    server = fakeredis.FakeServer()
    redis_client = fakeredis.FakeStrictRedis(server=server, decode_responses=True)

    # Clear all data before each test
    redis_client.flushall()

    return redis_client


@pytest.fixture
def cache_mock(redis_mock):
    """
    Provides a simple cache implementation using the fakeredis client.
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
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    return data
            return data

        def set(self, key, value, ttl=None):
            """Set a value in the cache with optional time-to-live."""
            if ttl is None:
                ttl = self.default_ttl

            # Convert complex types to JSON
            if not isinstance(value, (str, bytes, int, float, bool, type(None))):
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

    return SimpleCache(redis_mock)


@pytest.fixture
def mock_user():
    """Mock user fixture for testing."""
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
    """Mock game fixture for testing."""
    return {
        "id": 1,
        "user_id": 1,
        "pgn": '[Event "Test Game"]\n[White "Test User"]\n[Black "Opponent"]\n1. e4 e5 2. Nf3 Nc6',
        "result": "1-0",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T01:00:00Z",
    }
