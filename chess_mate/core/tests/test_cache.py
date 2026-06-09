"""
Tests for the caching utilities in the ChessMate application.
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from core.cache import (
    cache_key,
    cache_stats,
    cacheable,
    get_cache_instance,
    get_redis_connection,
    invalidate_cache,
    invalidate_pattern,
    memoize,
)
from django.core.cache import caches
from django.core.cache.backends.dummy import DummyCache
from django.test import override_settings


class TestCacheModule:
    """Tests for the cache module functions"""

    def test_cache_key_generation(self):
        """Test cache key generation with different arguments"""
        # Simple key
        assert cache_key("test") == "test"

        # Keys with args
        assert cache_key("user", 123) == "user:123"
        assert cache_key("game", 123, "analysis") == "game:123:analysis"

        # Keys with kwargs
        assert cache_key("profile", user_id=123) == "profile:user_id:123"

        # Mixed args and kwargs
        assert cache_key("analysis", 123, type="basic") == "analysis:123:type:basic"

        # None values should be skipped
        assert cache_key("test", None, user_id=None, game_id=123) == "test:game_id:123"

        # Sorting of kwargs should be consistent
        assert cache_key("test", a=1, b=2, c=3) == cache_key("test", c=3, b=2, a=1)

    @patch("core.cache.get_cache_instance")
    def test_get_cache_instance_success(self, mock_get_cache):
        """Test successful cache instance retrieval"""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache

        cache = get_cache_instance("redis")
        assert cache == mock_cache

    @patch("django.core.cache.caches.__getitem__")
    def test_get_cache_instance_fallback(self, mock_caches_getitem):
        """Test cache instance fallback when primary cache fails"""
        # Mock primary cache to fail
        mock_caches_getitem.side_effect = [Exception("Cache error"), MagicMock()]

        # Should fall back to default cache
        cache = get_cache_instance("redis")
        assert cache is not None

        # Called twice - once for redis, once for default
        assert mock_caches_getitem.call_count == 2

    @patch("django.core.cache.caches.__getitem__")
    def test_get_cache_instance_dummy_fallback(self, mock_caches_getitem):
        """Test fallback to dummy cache when all caches fail"""
        # Mock both primary and default cache to fail
        mock_caches_getitem.side_effect = Exception("Cache error")

        cache = get_cache_instance("redis")
        assert isinstance(cache, DummyCache)

    @override_settings(USE_REDIS=False)
    def test_get_redis_connection_disabled(self):
        """Test getting Redis connection when Redis is disabled"""
        assert get_redis_connection() is None

    @override_settings(USE_REDIS=True)
    @patch("core.cache.get_cache_instance")
    def test_get_redis_connection_success(self, mock_get_cache):
        """Test successful Redis connection retrieval"""
        mock_redis = MagicMock()
        mock_cache = MagicMock()
        mock_cache.client = mock_redis
        mock_get_cache.return_value = mock_cache

        assert get_redis_connection() == mock_redis

    @pytest.mark.parametrize("cache_attr,expected", [("client", True), ("_client", True), (None, False)])
    @override_settings(USE_REDIS=True)
    @patch("core.cache.get_cache_instance")
    def test_get_redis_connection_different_attrs(self, mock_get_cache, cache_attr, expected):
        """Test Redis connection with different client attribute names"""
        mock_redis = MagicMock()
        mock_cache = MagicMock()

        # Remove all client attributes first
        for attr in ["client", "_client", "get_client"]:
            if hasattr(mock_cache, attr):
                delattr(mock_cache, attr)

        # Set the appropriate attribute
        if cache_attr == "client":
            mock_cache.client = mock_redis
        elif cache_attr == "_client":
            mock_cache._client = mock_redis
        elif cache_attr == "get_client":
            mock_cache.get_client = lambda: mock_redis

        mock_get_cache.return_value = mock_cache

        result = get_redis_connection()
        if expected:
            assert result == mock_redis
        else:
            assert result is None

    def test_cacheable_decorator(self):
        """Test the cacheable decorator functionality"""
        cache_mock = MagicMock()

        # Mock the cache get/set functions
        cache_mock.get.return_value = None  # First call cache miss

        with patch("core.cache.get_cache_instance", return_value=cache_mock):
            # Define a function with our decorator
            call_count = 0

            @cacheable("test")
            def test_func(arg1, arg2=None):
                nonlocal call_count
                call_count += 1
                return f"Result: {arg1}, {arg2}"

            # First call - should miss cache and call real function
            result1 = test_func("a", arg2="b")
            assert result1 == "Result: a, b"
            assert call_count == 1
            assert cache_mock.set.call_count == 1

            # Reset cache mock to return a value
            cache_mock.get.return_value = "Result: a, b"

            # Second call with same args - should hit cache
            result2 = test_func("a", arg2="b")
            assert result2 == "Result: a, b"
            assert call_count == 1  # Didn't increment

            # Different args - should miss
            cache_mock.get.return_value = None
            result3 = test_func("c", arg2="d")
            assert result3 == "Result: c, d"
            assert call_count == 2

    def test_cacheable_decorator_with_custom_key_func(self):
        """Test the cacheable decorator with a custom key function"""
        cache_mock = MagicMock()
        cache_mock.get.return_value = None

        with patch("core.cache.get_cache_instance", return_value=cache_mock):
            # Custom key function
            def custom_key(*args, **kwargs):
                return f"custom:{args[0]}:{kwargs.get('arg2', '')}"

            @cacheable("prefix", key_func=custom_key)
            def test_func(arg1, arg2=None):
                return f"Result: {arg1}, {arg2}"

            # Call function
            test_func("a", arg2="b")

            # Check that the custom key was used
            cache_mock.get.assert_called_with("custom:a:b")

    def test_invalidate_cache(self):
        """Test cache invalidation function"""
        cache_mock = MagicMock()

        with patch("core.cache.get_cache_instance", return_value=cache_mock):
            result = invalidate_cache("test", 123, type="analysis")
            assert result is True
            cache_mock.delete.assert_called_once()

    def test_invalidate_cache_error(self):
        """Test cache invalidation when an error occurs"""
        cache_mock = MagicMock()
        cache_mock.delete.side_effect = Exception("Cache error")

        with patch("core.cache.get_cache_instance", return_value=cache_mock):
            result = invalidate_cache("test", 123)
            assert result is False

    def test_invalidate_pattern(self):
        """Test cache invalidation by pattern"""
        redis_mock = MagicMock()
        redis_mock.keys.return_value = ["key1", "key2"]

        with patch("core.cache.get_redis_connection", return_value=redis_mock):
            result = invalidate_pattern("test:*")
            assert result is True
            redis_mock.keys.assert_called_with("test:*")
            redis_mock.delete.assert_called_once_with("key1", "key2")

    def test_invalidate_pattern_no_redis(self):
        """Test pattern invalidation without Redis"""
        with patch("core.cache.get_redis_connection", return_value=None):
            result = invalidate_pattern("test:*")
            assert result is False

    def test_cache_stats(self):
        """Test cache stats function with Redis available"""
        redis_mock = MagicMock()
        redis_mock.info.return_value = {
            "redis_version": "6.0.0",
            "db0": {"keys": 100},
            "used_memory_human": "1M",
            "uptime_in_seconds": 86400,
            "connected_clients": 5,
        }

        with patch("core.cache.get_redis_connection", return_value=redis_mock):
            stats = cache_stats()
            assert stats["type"] == "redis"
            assert stats["version"] == "6.0.0"
            assert stats["entries"] == 100
            assert stats["uptime_days"] == 1.0

    def test_cache_stats_no_redis(self):
        """Test cache stats function without Redis"""
        with patch("core.cache.get_redis_connection", return_value=None):
            stats = cache_stats()
            assert stats["type"] == "memory"
            assert stats["status"] == "available"

    def test_memoize_decorator(self):
        """Test memoization decorator"""
        call_count = 0

        @memoize(ttl=1)  # Short TTL for testing
        def test_func(arg):
            nonlocal call_count
            call_count += 1
            return f"Result: {arg}"

        # First call
        result1 = test_func("a")
        assert result1 == "Result: a"
        assert call_count == 1

        # Second call with same args - should use cached value
        result2 = test_func("a")
        assert result2 == "Result: a"
        assert call_count == 1  # No increment

        # Different args - should call function
        result3 = test_func("b")
        assert result3 == "Result: b"
        assert call_count == 2

        # Wait for TTL to expire
        time.sleep(1.1)

        # Same args after TTL - should call function again
        result4 = test_func("a")
        assert result4 == "Result: a"
        assert call_count == 3
