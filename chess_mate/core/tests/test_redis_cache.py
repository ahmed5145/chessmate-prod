"""Tests for Redis caching functionality."""

import json
import time
from unittest.mock import MagicMock, call, patch

import pytest
import redis
from core.cache import (
    CACHE_BACKEND_MEMORY,
    CACHE_BACKEND_REDIS,
    cache_delete,
    cache_get,
    cache_memoize,
    cache_set,
    get_cache_instance,
    get_redis_connection,
    invalidate_cache,
    invalidate_pattern,
)
from core.redis_config import (
    KEY_PREFIX_GAME,
    KEY_PREFIX_USER,
    TTL_GAME,
    TTL_USER,
    get_redis_client,
    get_redis_key,
    redis_add_to_tag,
    redis_delete,
    redis_get,
    redis_invalidate_by_tags,
    redis_lock,
    redis_set,
    redis_unlock,
    with_redis_lock,
)
from django.conf import settings
from django.test import TestCase, override_settings


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        """Initialize with empty data store."""
        self.data = {}
        self.expiry = {}
        self.sets = {}

    def get(self, key):
        """Get a value if it exists and hasn't expired."""
        if key in self.data:
            # Check if key has expired
            if key in self.expiry and self.expiry[key] < time.time():
                del self.data[key]
                del self.expiry[key]
                return None
            return self.data[key]
        return None

    def set(self, key, value, ex=None, nx=False):
        """Set a value with optional expiry."""
        if nx and key in self.data:
            return False

        self.data[key] = value

        if ex:
            self.expiry[key] = time.time() + ex

        return True

    def setex(self, key, ex, value):
        """Set a value with expiry."""
        return self.set(key, value, ex=ex)

    def delete(self, *keys):
        """Delete one or more keys."""
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                count += 1
                if key in self.expiry:
                    del self.expiry[key]
        return count

    def exists(self, key):
        """Check if a key exists."""
        return 1 if key in self.data else 0

    def keys(self, pattern):
        """Get keys matching a pattern."""
        import fnmatch

        matches = []
        for key in self.data.keys():
            if fnmatch.fnmatch(key, pattern):
                matches.append(key.encode("utf-8"))
        return matches

    def incrby(self, key, amount=1):
        """Increment a key by amount."""
        if key not in self.data:
            self.data[key] = b"0"

        value = int(self.data[key])
        value += amount
        self.data[key] = str(value).encode("utf-8")
        return value

    def expire(self, key, seconds):
        """Set expiry on a key."""
        if key in self.data:
            self.expiry[key] = time.time() + seconds
            return 1
        return 0

    def pipeline(self):
        """Return a pipeline object."""
        return MockPipeline(self)

    def sadd(self, key, value):
        """Add a value to a set."""
        if key not in self.sets:
            self.sets[key] = set()

        if isinstance(value, bytes):
            value_str = value
        else:
            value_str = value.encode("utf-8") if isinstance(value, str) else str(value).encode("utf-8")

        self.sets[key].add(value_str)
        return 1

    def smembers(self, key):
        """Get all members of a set."""
        return self.sets.get(key, set())

    def info(self):
        """Return Redis server info."""
        return {"redis_version": "mock"}


class MockPipeline:
    """Mock Redis pipeline."""

    def __init__(self, redis_client):
        """Initialize with client reference and empty commands."""
        self.redis_client = redis_client
        self.commands = []
        self.results = []

    def execute(self):
        """Execute all queued commands."""
        results = []
        for cmd, args, kwargs in self.commands:
            method = getattr(self.redis_client, cmd)
            results.append(method(*args, **kwargs))

        self.results = results
        self.commands = []
        return results

    def __getattr__(self, name):
        """Capture method calls to queue them."""

        def method(*args, **kwargs):
            self.commands.append((name, args, kwargs))
            return self

        return method


@pytest.fixture
def mock_redis_client(monkeypatch):
    """Fixture to provide a mock Redis client."""
    mock_client = MockRedis()

    def mock_get_redis_client():
        return mock_client

    # Replace the real client with our mock
    monkeypatch.setattr("chess_mate.core.redis_config.get_redis_client", mock_get_redis_client)

    return mock_client


@pytest.mark.django_db
class TestRedisCache:
    """Test Redis cache implementation."""

    def test_get_redis_key(self):
        """Test key generation."""
        # Test with single argument
        key = get_redis_key(KEY_PREFIX_GAME, 123)
        assert key == "game:123"

        # Test with multiple arguments
        key = get_redis_key(KEY_PREFIX_USER, 456, "games")
        assert key == "user:456:games"

        # Test with string arguments
        key = get_redis_key("prefix:", "value")
        assert key == "prefix:value"

    def test_redis_set_get(self, mock_redis_client):
        """Test setting and getting values."""
        # Set a value
        key = get_redis_key(KEY_PREFIX_GAME, 123)
        data = {"id": 123, "name": "Test Game"}

        # Test setting with TTL
        success = redis_set(key, data, TTL_GAME)
        assert success is True

        # Test getting the value back
        result = redis_get(key)
        assert result == data

        # Test getting a non-existent key
        result = redis_get("nonexistent:key")
        assert result is None

    def test_redis_delete(self, mock_redis_client):
        """Test deleting values."""
        # Set up a value
        key = get_redis_key(KEY_PREFIX_GAME, 123)
        data = {"id": 123, "name": "Test Game"}
        redis_set(key, data)

        # Verify it exists
        assert redis_get(key) == data

        # Delete the key
        result = redis_delete(key)
        assert result is True

        # Verify it's gone
        assert redis_get(key) is None

        # Test deleting a non-existent key
        result = redis_delete("nonexistent:key")
        assert result is False

    def test_redis_lock(self, mock_redis_client):
        """Test distributed locking."""
        lock_name = "test_lock"

        # Acquire a lock
        lock_id = redis_lock(lock_name, 60)
        assert lock_id is not None

        # Try to acquire it again (should fail)
        second_lock = redis_lock(lock_name, 60)
        assert second_lock is None

        # Release the lock
        result = redis_unlock(lock_name, lock_id)
        assert result is True

        # Now we should be able to acquire it again
        lock_id = redis_lock(lock_name, 60)
        assert lock_id is not None

        # Try to release with wrong ID (should fail)
        result = redis_unlock(lock_name, "wrong_id")
        assert result is False

    def test_with_redis_lock_decorator(self, mock_redis_client):
        """Test the lock decorator."""
        result_container = {"value": None}

        @with_redis_lock("test_function_lock")
        def test_function():
            result_container["value"] = "executed"
            return "success"

        # Call the decorated function
        result = test_function()

        # Check that it executed
        assert result == "success"
        assert result_container["value"] == "executed"

        # Mock the lock acquisition to fail
        original_redis_lock = redis_lock

        def mock_redis_lock_fail(*args, **kwargs):
            return None

        # Replace real function with mock that always fails
        import core.redis_config

        chess_mate.core.redis_config.redis_lock = mock_redis_lock_fail

        # Reset result and call again
        result_container["value"] = None
        result = test_function()

        # Check that it didn't execute
        assert result is None
        assert result_container["value"] is None

        # Restore original function
        chess_mate.core.redis_config.redis_lock = original_redis_lock

    def test_redis_tag_invalidation(self, mock_redis_client):
        """Test tag-based cache invalidation."""
        # Set up some keys with tags
        game1_key = get_redis_key(KEY_PREFIX_GAME, 1)
        game2_key = get_redis_key(KEY_PREFIX_GAME, 2)
        user1_key = get_redis_key(KEY_PREFIX_USER, 1)

        # Set values
        redis_set(game1_key, {"id": 1, "name": "Game 1"})
        redis_set(game2_key, {"id": 2, "name": "Game 2"})
        redis_set(user1_key, {"id": 1, "name": "User 1"})

        # Add keys to tags
        redis_add_to_tag("games", game1_key)
        redis_add_to_tag("games", game2_key)
        redis_add_to_tag("user1", game1_key)
        redis_add_to_tag("user1", user1_key)

        # Verify all keys exist
        assert redis_get(game1_key) is not None
        assert redis_get(game2_key) is not None
        assert redis_get(user1_key) is not None

        # Invalidate the 'user1' tag
        count = redis_invalidate_by_tags("user1")
        assert count >= 1

        # Verify user1 keys are gone, but game2 still exists
        assert redis_get(game1_key) is None
        assert redis_get(user1_key) is None
        assert redis_get(game2_key) is not None

        # Invalidate the 'games' tag
        count = redis_invalidate_by_tags("games")
        assert count >= 1

        # Verify all game keys are gone
        assert redis_get(game2_key) is None


@pytest.mark.integration
class TestRedisIntegration(TestCase):
    """Integration tests with real Redis."""

    def setUp(self):
        """Set up a real Redis client if available."""
        try:
            self.redis_client = get_redis_client()
            self.redis_client.ping()
            self.redis_available = True
        except (redis.exceptions.ConnectionError, redis.exceptions.ResponseError):
            self.redis_available = False

    def test_real_redis_connection(self):
        """Test connection to real Redis server if available."""
        if not self.redis_available:
            pytest.skip("Redis server not available")

        # Test we can get client info
        info = self.redis_client.info()
        assert "redis_version" in info

    def test_real_redis_operations(self):
        """Test basic operations with real Redis if available."""
        if not self.redis_available:
            pytest.skip("Redis server not available")

        # Generate a unique test key
        import uuid

        test_key = f"test:{uuid.uuid4()}"

        try:
            # Set a value
            self.redis_client.set(test_key, "test_value")

            # Get it back
            value = self.redis_client.get(test_key)
            assert value == b"test_value"

            # Delete it
            self.redis_client.delete(test_key)

            # Verify it's gone
            value = self.redis_client.get(test_key)
            assert value is None

        finally:
            # Cleanup
            self.redis_client.delete(test_key)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    with patch("core.cache.redis.Redis") as mock_redis_class:
        # Create a mock instance to return
        mock_instance = MagicMock()
        mock_redis_class.return_value = mock_instance

        # Mock the expected Redis methods
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = 1
        mock_instance.keys.return_value = []
        mock_instance.scan_iter.return_value = []

        yield mock_instance


@pytest.fixture
def mock_django_cache():
    """Create a mock Django cache."""
    with patch("core.cache.cache") as mock_cache:
        # Mock the expected cache methods
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache.delete.return_value = True

        yield mock_cache


class TestCacheBackends:
    """Tests for cache backend selection and connection."""

    def test_get_cache_instance_redis(self, mock_redis):
        """Test getting a Redis cache instance."""
        # Call the function
        cache_instance = get_cache_instance(CACHE_BACKEND_REDIS)

        # Check that Redis was instantiated
        assert cache_instance is not None

        # Test Redis-specific methods to ensure it's a Redis instance
        cache_instance.get("test_key")
        mock_redis.get.assert_called_once_with("test_key")

    def test_get_cache_instance_memory(self, mock_django_cache):
        """Test getting a memory (Django) cache instance."""
        # Call the function
        cache_instance = get_cache_instance(CACHE_BACKEND_MEMORY)

        # Check that Django cache is used
        assert cache_instance is not None

        # Test Django-specific methods
        cache_instance.get("test_key")
        mock_django_cache.get.assert_called_once_with("test_key")

    def test_get_redis_connection(self, mock_redis):
        """Test getting a Redis connection."""
        # Call the function
        connection = get_redis_connection()

        # Check that Redis was instantiated with the correct parameters
        assert connection is mock_redis


class TestCacheOperations:
    """Tests for basic cache operations."""

    def test_cache_get_hit(self, mock_redis):
        """Test retrieving a value from cache (cache hit)."""
        # Configure mock Redis to return a value
        mock_redis.get.return_value = json.dumps({"value": "test_data"}).encode("utf-8")

        # Call the function
        result = cache_get("test_key", CACHE_BACKEND_REDIS)

        # Check that Redis.get was called with the correct key
        mock_redis.get.assert_called_once_with("test_key")

        # Check the result
        assert result == "test_data"

    def test_cache_get_miss(self, mock_redis):
        """Test retrieving a value from cache (cache miss)."""
        # Configure mock Redis to return None (cache miss)
        mock_redis.get.return_value = None

        # Call the function
        result = cache_get("test_key", CACHE_BACKEND_REDIS)

        # Check that Redis.get was called with the correct key
        mock_redis.get.assert_called_once_with("test_key")

        # Check the result
        assert result is None

    def test_cache_set(self, mock_redis):
        """Test setting a value in cache."""
        # Call the function
        cache_set("test_key", "test_value", ttl=300, backend=CACHE_BACKEND_REDIS)

        # Check that Redis.set was called with the correct parameters
        expected_value = json.dumps({"value": "test_value"})
        mock_redis.set.assert_called_once_with("test_key", expected_value, ex=300)

    def test_cache_delete(self, mock_redis):
        """Test deleting a value from cache."""
        # Call the function
        result = cache_delete("test_key", CACHE_BACKEND_REDIS)

        # Check that Redis.delete was called with the correct key
        mock_redis.delete.assert_called_once_with("test_key")

        # Check the result
        assert result == 1

    def test_invalidate_cache(self, mock_redis):
        """Test invalidating a cache key based on prefix and arguments."""
        # Call the function
        result = invalidate_cache("user", [123], backend=CACHE_BACKEND_REDIS)

        # Check that Redis.delete was called with the correct key
        mock_redis.delete.assert_called_once()

        # Check the result
        assert result is True

    def test_invalidate_pattern(self, mock_redis):
        """Test invalidating cache entries matching a pattern."""
        # Configure mock Redis to return some keys
        mock_redis.scan_iter.return_value = [b"user:123", b"user:123:profile", b"user:123:games"]

        # Call the function
        result = invalidate_pattern("user:123*", backend=CACHE_BACKEND_REDIS)

        # Check that Redis.scan_iter was called with the correct pattern
        mock_redis.scan_iter.assert_called_once_with(match="user:123*")

        # Check that Redis.delete was called for each key
        assert mock_redis.delete.call_count == 1  # pipeline execute calls delete once with all keys

        # Check the result
        assert result is True


class TestCacheMemoize:
    """Tests for the cache_memoize decorator."""

    def test_cache_memoize_miss_then_hit(self, mock_redis):
        """Test the cache_memoize decorator with a cache miss followed by a hit."""
        # Configure mock Redis for cache miss on first call
        mock_redis.get.return_value = None

        # Define a function to memoize
        @cache_memoize(prefix="test", ttl=300, backend=CACHE_BACKEND_REDIS)
        def test_function(arg1, arg2):
            return f"{arg1}_{arg2}"

        # First call (cache miss)
        result1 = test_function("hello", "world")

        # Check that the function returned the correct result
        assert result1 == "hello_world"

        # Check that Redis.set was called to store the result
        mock_redis.set.assert_called_once()

        # Configure mock Redis for cache hit on second call
        mock_redis.get.return_value = json.dumps({"value": "hello_world"}).encode("utf-8")

        # Reset set method for clearer assertions
        mock_redis.set.reset_mock()

        # Second call (cache hit)
        result2 = test_function("hello", "world")

        # Check that the function returned the cached result
        assert result2 == "hello_world"

        # Check that Redis.set was not called again
        mock_redis.set.assert_not_called()

    def test_cache_memoize_with_different_args(self, mock_redis):
        """Test the cache_memoize decorator with different function arguments."""
        # Configure mock Redis to always return None (cache miss)
        mock_redis.get.return_value = None

        # Define a function to memoize
        @cache_memoize(prefix="test", ttl=300, backend=CACHE_BACKEND_REDIS)
        def test_function(arg1, arg2):
            return f"{arg1}_{arg2}"

        # Call with first set of arguments
        result1 = test_function("hello", "world")

        # Check that the function returned the correct result
        assert result1 == "hello_world"

        # Call with second set of arguments
        result2 = test_function("goodbye", "world")

        # Check that the function returned the correct result
        assert result2 == "goodbye_world"

        # Check that Redis.get was called twice with different keys
        assert mock_redis.get.call_count == 2

        # Check that Redis.set was called twice with different keys
        assert mock_redis.set.call_count == 2


@pytest.mark.integration
class TestIntegrationWithRedis:
    """Integration tests with a real Redis instance."""

    @pytest.fixture
    def redis_connection(self):
        """Create a real Redis connection for integration tests."""
        try:
            # Try to connect to a local Redis instance
            r = redis.Redis(host="localhost", port=6379, db=15, socket_timeout=1)
            r.ping()  # Check if Redis is available

            # Clear test database
            r.flushdb()

            yield r

            # Clean up after tests
            r.flushdb()
            r.close()
        except (redis.RedisError, ConnectionError):
            pytest.skip("Redis server not available for integration tests")

    def test_real_cache_operations(self, redis_connection):
        """Test basic cache operations with a real Redis instance."""
        # Skip if Redis is not available
        if not redis_connection:
            return

        # Test cache_set and cache_get
        cache_set("test_integration_key", "test_integration_value", ttl=10, backend=CACHE_BACKEND_REDIS)
        value = cache_get("test_integration_key", CACHE_BACKEND_REDIS)

        assert value == "test_integration_value"

        # Test cache_delete
        cache_delete("test_integration_key", CACHE_BACKEND_REDIS)
        value = cache_get("test_integration_key", CACHE_BACKEND_REDIS)

        assert value is None

    def test_real_invalidate_pattern(self, redis_connection):
        """Test invalidate_pattern with a real Redis instance."""
        # Skip if Redis is not available
        if not redis_connection:
            return

        # Set multiple keys with a common prefix
        cache_set("test_pattern:1", "value1", ttl=10, backend=CACHE_BACKEND_REDIS)
        cache_set("test_pattern:2", "value2", ttl=10, backend=CACHE_BACKEND_REDIS)
        cache_set("test_pattern:3", "value3", ttl=10, backend=CACHE_BACKEND_REDIS)

        # Also set a key with a different prefix
        cache_set("other_prefix:1", "other_value", ttl=10, backend=CACHE_BACKEND_REDIS)

        # Invalidate keys matching the pattern
        invalidate_pattern("test_pattern:*", backend=CACHE_BACKEND_REDIS)

        # Check that matching keys were invalidated
        assert cache_get("test_pattern:1", CACHE_BACKEND_REDIS) is None
        assert cache_get("test_pattern:2", CACHE_BACKEND_REDIS) is None
        assert cache_get("test_pattern:3", CACHE_BACKEND_REDIS) is None

        # Check that non-matching key still exists
        assert cache_get("other_prefix:1", CACHE_BACKEND_REDIS) == "other_value"

    def test_real_cache_memoize(self, redis_connection):
        """Test cache_memoize with a real Redis instance."""
        # Skip if Redis is not available
        if not redis_connection:
            return

        # Define a function to memoize that counts the number of times it's called
        call_count = 0

        @cache_memoize(prefix="test_memoize", ttl=10, backend=CACHE_BACKEND_REDIS)
        def test_function(arg1, arg2):
            nonlocal call_count
            call_count += 1
            return f"{arg1}_{arg2}_{call_count}"

        # First call (cache miss)
        result1 = test_function("hello", "world")
        assert result1 == "hello_world_1"
        assert call_count == 1

        # Second call with same arguments (cache hit)
        result2 = test_function("hello", "world")
        assert result2 == "hello_world_1"  # Note: still has count=1 because it was cached
        assert call_count == 1  # Function wasn't actually called again

        # Call with different arguments (cache miss)
        result3 = test_function("goodbye", "world")
        assert result3 == "goodbye_world_2"
        assert call_count == 2
