"""
Centralized caching utilities for the Chess Mate application.

This module provides cache-related functions and decorators to:
1. Cache frequently accessed data
2. Prevent cache stampede
3. Manage cache invalidation
4. Support multiple cache backends (Redis and in-memory)
"""

import functools
import hashlib
import json
import logging
import random
import time
import uuid
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import redis
from django.conf import settings  # type: ignore
from django.core.cache import cache, caches  # type: ignore
from django.core.cache.backends.base import BaseCache  # type: ignore
from django.db.models import Model  # type: ignore
from django.http import HttpRequest, HttpResponse  # type: ignore
from redis.exceptions import RedisError
from rest_framework.response import Response  # type: ignore

# Configure logger
logger = logging.getLogger(__name__)

# Define cache backends
CACHE_BACKEND_DEFAULT = "default"  # Django's default cache (memory)
CACHE_BACKEND_REDIS = "redis"  # Redis cache for persistence
CACHE_BACKEND_LOCAL = "local"  # Local cache for testing

# Type variables for return typing
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# Protocol for key functions
class KeyFunction(Protocol):
    """Protocol for key generation functions."""

    def __call__(self, *args: Any, **kwargs: Any) -> str: ...


# Default cache TTL in seconds
DEFAULT_CACHE_TTL = 60 * 60  # 1 hour
SHORT_CACHE_TIMEOUT = 300  # 5 minutes
LONG_CACHE_TIMEOUT = 86400  # 24 hours

# Cache key prefixes to ensure uniqueness
KEY_PREFIX = getattr(settings, "CACHE_KEY_PREFIX", "chessmate:")

# Flag to enable cache debugging
CACHE_DEBUG = getattr(settings, "CACHE_DEBUG", False)

# Redis connection singleton
_redis_client = None


def get_cache_instance(cache_alias: str = "default") -> BaseCache:
    """
    Get a cache instance by alias with fallback to default if the requested cache is unavailable.

    Args:
        cache_alias: The alias of the cache to retrieve

    Returns:
        A Django cache instance
    """
    try:
        return caches[cache_alias]
    except Exception as e:
        logger.warning(f"Could not get cache '{cache_alias}', falling back to default. Error: {str(e)}")
        try:
            return caches["default"]
        except Exception as e:
            logger.error(f"Could not get default cache. Error: {str(e)}")
            from django.core.cache.backends.dummy import DummyCache

            return DummyCache("dummy", {})


def get_redis_connection() -> Optional["Redis"]:  # type: ignore
    """
    Get a Redis connection for direct Redis operations.
    If Redis is disabled via settings, returns a dummy client.

    Returns:
        Redis client instance
    """
    global _redis_client

    # Check if Redis is disabled in settings
    redis_disabled = getattr(settings, "REDIS_DISABLED", False)
    if redis_disabled:
        logger.debug("Redis is disabled in settings. Using dummy Redis client.")
        class DummyRedis:
            def __getattr__(self, name):
                def method(*args, **kwargs):
                    logger.debug(f"Redis operation {name} called but Redis is disabled")
                    return None
                return method
        return cast(redis.Redis, DummyRedis())  # type: ignore

    if _redis_client is None:
        try:
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.from_url(  # type: ignore
                redis_url,
                socket_timeout=getattr(settings, "REDIS_SOCKET_TIMEOUT", 5),
                socket_connect_timeout=getattr(settings, "REDIS_SOCKET_CONNECT_TIMEOUT", 5),
                retry_on_timeout=True,
                decode_responses=True,
                health_check_interval=30,
                connection_pool_class=redis.connection.BlockingConnectionPool,
                max_connections=getattr(settings, "REDIS_MAX_CONNECTIONS", 100),
            )
            # Test connection
            _redis_client.ping()  # type: ignore
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            _redis_client = None
            return None

    return _redis_client


def cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate a cache key with the given prefix and arguments.

    Args:
        prefix: A string prefix for the cache key
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key

    Returns:
        A string cache key
    """
    key_parts = [prefix]

    # Add positional args
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))

    # Add keyword args, sorted by key
    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}:{v}")

    return ":".join(key_parts)


def cache_get(key, default=None, backend_name=CACHE_BACKEND_DEFAULT):
    """
    Get a value from cache with error handling.
    
    Args:
        key: Cache key
        default: Default value if key not found
        backend_name: Cache backend name
        
    Returns:
        Cached value or default
    """
    try:
        logger.debug(f"Getting cache key: {key}")
        return cache.get(key, default)
    except RedisError as e:
        # Handle Redis-specific errors
        logger.warning(f"Unexpected cache get error for key {key}: {str(e)}")
        return default
    except Exception as e:
        logger.error(f"Cache get error for key {key}: {str(e)}")
        return default


def cache_set(key: str, value: Any, timeout: Optional[int] = None, backend_name: str = CACHE_BACKEND_DEFAULT) -> bool:
    """
    Set a value in the specified cache backend.

    Args:
        key: Cache key
        value: Value to cache
        timeout: Cache timeout in seconds (None for default)
        backend_name: Name of cache backend to use

    Returns:
        True if successful, False otherwise
    """
    try:
        # First try to use the specified backend
        backend = caches[backend_name] if backend_name != CACHE_BACKEND_DEFAULT else cache
        backend.set(key, value, timeout=timeout)
        return True
    except (KeyError, RedisError) as e:
        # If Redis backend is unavailable, fallback to default
        if backend_name != CACHE_BACKEND_DEFAULT:
            logger.warning(f"Cache backend '{backend_name}' unavailable, falling back to default: {str(e)}")
            try:
                cache.set(key, value, timeout=timeout)
                return True
            except Exception as inner_e:
                logger.error(f"Default cache set error for key {key}: {str(inner_e)}")
                return False
        else:
            logger.warning(f"Cache set error for key {key}: {str(e)}")
            return False
    except Exception as e:
        logger.warning(f"Unexpected cache set error for key {key}: {str(e)}")
        return False


def cache_delete(key: str, backend_name: str = CACHE_BACKEND_DEFAULT) -> bool:
    """
    Delete a value from the specified cache backend.

    Args:
        key: Cache key
        backend_name: Name of cache backend to use

    Returns:
        True if successful, False otherwise
    """
    try:
        # First try to use the specified backend
        backend = caches[backend_name] if backend_name != CACHE_BACKEND_DEFAULT else cache
        backend.delete(key)
        return True
    except (KeyError, RedisError) as e:
        # If Redis backend is unavailable, fallback to default
        if backend_name != CACHE_BACKEND_DEFAULT:
            logger.warning(f"Cache backend '{backend_name}' unavailable, falling back to default: {str(e)}")
            try:
                cache.delete(key)
                return True
            except Exception as inner_e:
                logger.error(f"Default cache delete error for key {key}: {str(inner_e)}")
                return False
        else:
            logger.warning(f"Cache delete error for key {key}: {str(e)}")
            return False
    except Exception as e:
        logger.warning(f"Unexpected cache delete error for key {key}: {str(e)}")
        return False


def cache_stampede_prevention(
    key: str,
    resource_func: Callable[[], T],
    timeout: int = 60,
    backend_name: str = CACHE_BACKEND_DEFAULT,
    stale_timeout: int = 10,
) -> T:
    """
    Cache with protection against stampede (thundering herd) using stale-while-revalidate pattern.

    Args:
        key: Cache key
        resource_func: Function to call to get the value if not cached
        timeout: Cache timeout in seconds
        backend_name: Name of cache backend to use
        stale_timeout: How long stale data can be served while refreshing

    Returns:
        The cached or freshly computed value
    """
    backend = caches[backend_name] if backend_name != CACHE_BACKEND_DEFAULT else cache

    # Try to get cached entry with timestamp
    cached_entry = backend.get(key)
    now = time.time()

    if cached_entry is not None:
        # Parse timestamp and value
        cached_time, cached_value = cached_entry

        # Check if entry is fresh
        if now - cached_time < timeout:
            return cached_value

        # Entry is stale but still usable - refresh in background
        try:
            # Set a temporary lock key to prevent multiple refreshes
            lock_key = f"{key}_refreshing"
            if not backend.add(lock_key, True, timeout=stale_timeout):
                # Another process is already refreshing, return stale value
                return cached_value

            # Compute new value and update cache asynchronously (if we had async)
            # For now, we'll do it synchronously but still return stale value
            new_value = resource_func()
            backend.set(key, (now, new_value), timeout=timeout + stale_timeout)
            backend.delete(lock_key)

            # Return the stale value to this request to prevent blocking
            return cached_value
        except Exception as e:
            logger.error(f"Cache refresh error for {key}: {str(e)}")
            # Return stale value on error
            return cached_value

    # No cached value exists, compute and cache
    try:
        value = resource_func()
        backend.set(key, (now, value), timeout=timeout + stale_timeout)
        return value
    except Exception as e:
        logger.error(f"Cache miss error for {key}: {str(e)}")
        raise


def cache_decorator(
    key_func: KeyFunction, timeout: Optional[int] = None, cache_backend: str = CACHE_BACKEND_DEFAULT
) -> Callable[[F], F]:
    """
    Decorator for caching function results.

    Args:
        key_func: A function that generates a cache key
        timeout: Cache timeout in seconds (or None for default)
        cache_backend: Name of cache backend to use

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            key = key_func(*args, **kwargs)

            # Try to get value from cache
            cached_value = cache_get(key, cache_backend)
            if cached_value is not None:
                if CACHE_DEBUG:
                    logger.debug(f"Cache hit for {key}")
                return cast(Any, cached_value)  # Cast to Any to satisfy mypy

            if CACHE_DEBUG:
                logger.debug(f"Cache miss for {key}")

            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache_set(key, result, timeout, cache_backend)

            return result

        return cast(F, wrapper)

    return decorator


def cacheable(
    prefix: str, timeout: Optional[int] = None, cache_backend: str = CACHE_BACKEND_DEFAULT
) -> Callable[[F], F]:
    """
    Decorator for caching function results with a simple key pattern.

    Args:
        prefix: Prefix for cache key
        timeout: Cache timeout in seconds (or None for default)
        cache_backend: Name of cache backend to use

    Returns:
        Decorator function
    """

    def key_func(*args: Any, **kwargs: Any) -> str:
        return cache_key(prefix, *args, **kwargs)

    return cache_decorator(key_func, timeout, cache_backend)


def memoize(timeout: Optional[int] = None, cache_backend: str = CACHE_BACKEND_DEFAULT) -> Callable[[F], F]:
    """
    Decorator for memoizing function results based on arguments.

    Args:
        timeout: Cache timeout in seconds (or None for default)
        cache_backend: Name of cache backend to use

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate a unique key based on function name and arguments
            key_parts = [func.__module__, func.__name__]

            # Add args to key
            for arg in args:
                key_parts.append(str(arg))

            # Add kwargs to key, sorted by name
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}:{v}")

            key = ":".join(key_parts)
            hash_key = f"{KEY_PREFIX}memoize:{hashlib.md5(key.encode()).hexdigest()}"

            # Try to get from cache
            cached_value = cache_get(hash_key, cache_backend)
            if cached_value is not None:
                return cast(Any, cached_value)  # Cast to Any to satisfy mypy

            # Call function and cache result
            result = func(*args, **kwargs)
            cache_set(hash_key, result, timeout, cache_backend)
            return result

        return cast(F, wrapper)

    return decorator


def invalidate_cache(prefix: str, *args: Any, cache_alias: str = "default", **kwargs: Any) -> bool:
    """
    Invalidate cache entries with the given prefix and arguments.

    Args:
        prefix: The prefix of the cache keys to invalidate
        *args: Positional arguments used in the cache key
        cache_alias: The alias of the cache to use
        **kwargs: Keyword arguments used in the cache key

    Returns:
        True if cache was invalidated successfully, False otherwise
    """
    key = cache_key(prefix, *args, **kwargs)
    cache_instance = get_cache_instance(cache_alias)

    try:
        cache_instance.delete(key)
        logger.debug(f"Invalidated cache for key: {key}")
        return True
    except Exception as e:
        logger.warning(f"Error invalidating cache for key {key}: {str(e)}")
        return False


def invalidate_pattern(pattern: str, cache_alias: str = "default") -> bool:
    """
    Invalidate all cache entries matching the given pattern.
    Only works with Redis cache.

    Args:
        pattern: The pattern to match cache keys (Redis pattern)
        cache_alias: The alias of the cache to use

    Returns:
        True if pattern invalidation was successful, False otherwise
    """
    redis_client = get_redis_connection()
    if not redis_client:
        logger.warning("Cannot invalidate by pattern: Redis not available")
        return False

    try:
        # Get keys matching the pattern - using scan_iter for efficiency with large datasets
        key_list = []
        for key in redis_client.scan_iter(match=pattern):  # type: ignore
            # Convert bytes to string if necessary
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            key_list.append(key)

        # Delete keys in batches to avoid issues with very large key sets
        if key_list:
            # Delete in batches of 100 to avoid issues with too many arguments
            batch_size = 100
            for i in range(0, len(key_list), batch_size):
                batch = key_list[i : i + batch_size]
                if batch:
                    redis_client.delete(*batch)  # type: ignore

            logger.debug(f"Invalidated {len(key_list)} keys matching pattern: {pattern}")
        else:
            logger.debug(f"No keys found matching pattern: {pattern}")
        return True
    except Exception as e:
        logger.warning(f"Error invalidating cache for pattern {pattern}: {str(e)}")
        return False


def cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dict with cache statistics
    """
    stats: Dict[str, Any] = {}

    # Get basic stats from default cache
    stats["default"] = {"type": "unknown", "entries": 0, "backend": str(cache.__class__.__name__)}

    # If Redis is available, get Redis stats
    try:
        redis_client = get_redis_connection()
        if redis_client:
            info = redis_client.info()  # type: ignore
            if isinstance(info, dict):
                # Process Redis info - safely extract values with proper type handling
                redis_version = info.get("redis_version")
                if not isinstance(redis_version, str):
                    redis_version = "unknown"

                # Handle db0 which might be a dict or not exist
                db0 = info.get("db0", {})
                db0_keys = 0
                if isinstance(db0, dict):
                    db0_keys = db0.get("keys", 0)

                # Handle uptime which should be converted to float
                uptime_secs = info.get("uptime_in_seconds", 0)
                try:
                    uptime_days = round(float(uptime_secs) / 86400, 2)
                except (ValueError, TypeError):
                    uptime_days = 0

                # Handle clients count
                clients = info.get("connected_clients", 0)
                if not isinstance(clients, int):
                    try:
                        clients = int(clients)
                    except (ValueError, TypeError):
                        clients = 0

                # Handle memory usage
                memory_used = info.get("used_memory_human", "unknown")
                if not isinstance(memory_used, str):
                    memory_used = str(memory_used)

                # Build the stats dict with properly typed values
                redis_stats = {
                    "type": "redis",
                    "version": redis_version,
                    "entries": db0_keys,
                    "memory_used": memory_used,
                    "uptime_days": uptime_days,
                    "connected_clients": clients,
                }

                stats.update(redis_stats)
    except Exception as e:
        logger.warning(f"Error getting Redis stats: {str(e)}")

    return stats


def invalidate_cache_for(key_prefix: str = "", cache_alias: str = "default") -> Callable[[F], F]:
    """
    Decorator to invalidate cache with a given prefix after the view function executes.
    Useful for POST/PUT/DELETE operations that modify data.

    Args:
        key_prefix: Prefix of cache keys to invalidate
        cache_alias: Cache backend to use

    Returns:
        Decorator function
    """

    def decorator(view_func: F) -> F:
        @wraps(view_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Execute the view function
            response = view_func(*args, **kwargs)

            # After execution, invalidate cache keys with prefix
            cache_instance = get_cache_instance(cache_alias)

            try:
                # If Redis is available, use pattern deletion
                redis_client = get_redis_connection()
                if redis_client:
                    pattern = f"{key_prefix}*"
                    invalidate_pattern(pattern, cache_alias)
                # For simpler backends, try to delete user-specific keys at minimum
                elif args and isinstance(args[0], HttpRequest) and args[0].user.is_authenticated:
                    user_key = f"{key_prefix}:user:{args[0].user.id}"
                    invalidate_cache(user_key, cache_alias=cache_alias)
            except Exception as e:
                logger.warning(f"Cache invalidation error for prefix {key_prefix}: {str(e)}")

            return response

        return cast(F, wrapper)

    return decorator


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate a unique cache key based on prefix and parameters.

    Args:
        prefix: String prefix for the key
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key

    Returns:
        Cache key string
    """
    # Start with the global prefix and provided prefix
    key_parts = [KEY_PREFIX, prefix]

    # Add positional args
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))

    # Add keyword args in sorted order for consistency
    if kwargs:
        # Sort keys for consistent ordering
        sorted_items = sorted(kwargs.items())
        for k, v in sorted_items:
            if v is not None:
                key_parts.append(f"{k}={v}")

    # Join with colon and make safe for Redis
    key = ":".join(key_parts)

    # If key is too long, hash the latter part
    if len(key) > 200:
        prefix_part = ":".join(key_parts[:2])
        hash_part = hashlib.md5(":".join(key_parts[2:]).encode()).hexdigest()
        key = f"{prefix_part}:{hash_part}"

    return key


def cache_delete_pattern(pattern: str, backend_name: str = CACHE_BACKEND_DEFAULT) -> int:
    """
    Delete all keys matching a pattern.

    Args:
        pattern: Pattern to match (e.g., "user:*")
        backend_name: Name of cache backend to use

    Returns:
        Number of keys deleted
    """
    count = 0
    try:
        # For Redis, we can use the scan_iter method to find matching keys
        redis_client = get_redis_connection()

        if redis_client:
            # Use scan_iter to avoid loading all keys into memory at once
            key_list = []
            for key in redis_client.scan_iter(match=pattern):  # type: ignore
                # Convert bytes to string if necessary
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                key_list.append(key)

            # Delete keys in batches to avoid issues with very large key sets
            if key_list:
                # Delete in batches of 100 to avoid issues with too many arguments
                batch_size = 100
                for i in range(0, len(key_list), batch_size):
                    batch = key_list[i : i + batch_size]
                    if batch:
                        result = redis_client.delete(*batch)  # type: ignore
                        # Redis returns the number of keys deleted
                        if result and isinstance(result, int):
                            count += result
                        elif result:
                            count += 1  # At least something was deleted

            logger.debug(f"Deleted {count} keys matching pattern: {pattern}")
        else:
            # For other backends, we need to do a full scan
            backend = get_cache_instance(backend_name)

            # Limited support for pattern matching in non-Redis backends
            logger.warning(f"Pattern deletion not fully supported for backend {backend_name}")

    except Exception as e:
        logger.warning(f"Error deleting keys matching pattern {pattern}: {str(e)}")

    return count


def cache_incr(key: str, amount: int = 1, backend_name: str = CACHE_BACKEND_DEFAULT) -> Optional[int]:
    """
    Increment a numeric cache value.

    Args:
        key: Cache key
        amount: Amount to increment
        backend_name: Name of cache backend to use

    Returns:
        New value or None if operation failed
    """
    try:
        # Choose cache backend
        if backend_name == CACHE_BACKEND_DEFAULT:
            cache_backend = cache
        else:
            cache_backend = caches[backend_name]

        # Increment the value
        return cache_backend.incr(key, amount)
    except Exception as e:
        logger.error(f"Error incrementing cache key {key}: {str(e)}")
        return None


def cache_decr(key: str, amount: int = 1, backend_name: str = CACHE_BACKEND_DEFAULT) -> Optional[int]:
    """
    Decrement a numeric cache value.

    Args:
        key: Cache key
        amount: Amount to decrement
        backend_name: Name of cache backend to use

    Returns:
        New value or None if operation failed
    """
    try:
        # Choose cache backend
        if backend_name == CACHE_BACKEND_DEFAULT:
            cache_backend = cache
        else:
            cache_backend = caches[backend_name]

        # Decrement the value
        return cache_backend.decr(key, amount)
    except Exception as e:
        logger.error(f"Error decrementing cache key {key}: {str(e)}")
        return None


def cache_clear(backend_name: str = CACHE_BACKEND_DEFAULT) -> bool:
    """
    Clear all cache entries.

    Args:
        backend_name: Name of cache backend to use

    Returns:
        True if successful, False otherwise
    """
    try:
        # Choose cache backend
        if backend_name == CACHE_BACKEND_DEFAULT:
            cache_backend = cache
        else:
            cache_backend = caches[backend_name]

        # Clear the cache
        cache_backend.clear()
        logger.info(f"Cleared cache backend {backend_name}")
        return True
    except Exception as e:
        logger.error(f"Error clearing cache backend {backend_name}: {str(e)}")
        return False


def cache_delete_multiple(keys: List[str]) -> None:
    """
    Delete multiple cache keys at once.

    Args:
        keys: List of cache keys to delete
    """
    if not keys:
        return

    try:
        # Use Redis pipeline for efficient multi-key deletion if available
        redis_client = get_redis_connection()
        if redis_client and hasattr(redis_client, "pipeline"):
            try:
                # Process in batches of 1000 to avoid too many arguments
                batch_size = 1000
                for i in range(0, len(keys), batch_size):
                    batch_keys = keys[i : i + batch_size]
                    pipe = redis_client.pipeline()  # type: ignore
                    for key in batch_keys:
                        pipe.delete(key)  # type: ignore
                    pipe.execute()  # type: ignore
                logger.debug(f"Deleted {len(keys)} keys using Redis pipeline")
                return
            except Exception as e:
                logger.warning(f"Error using Redis pipeline: {str(e)}")
                # Fall back to standard cache deletion
    except Exception as e:
        logger.warning(f"Redis not available for bulk deletion: {str(e)}")

    # Fall back to deleting keys one by one using standard cache
    for key in keys:
        try:
            cache.delete(key)
        except Exception as e:
            logger.warning(f"Error deleting key {key}: {str(e)}")

    logger.debug(f"Deleted {len(keys)} keys using individual delete operations")


def is_redis_available() -> bool:
    """
    Check if Redis is available.

    Returns:
        True if Redis is available, False otherwise
    """
    try:
        redis_client = get_redis_connection()
        if redis_client:
            redis_client.ping()  # type: ignore
            return True
    except Exception:
        pass
    return False


def get_cache_health() -> Dict[str, Any]:
    """
    Get cache health status.

    Returns:
        Dict with cache health information
    """
    health = {"status": "ok", "backend": str(cache.__class__.__name__), "redis_available": False}

    # Check if Redis is available
    try:
        if is_redis_available():
            health["redis_available"] = True

            # Get Redis version and other info
            redis_client = get_redis_connection()
            if redis_client:
                try:
                    info = redis_client.info()  # type: ignore
                    if isinstance(info, dict):
                        health["redis_version"] = info.get("redis_version", "unknown")
                        health["uptime_days"] = round(float(info.get("uptime_in_seconds", 0)) / 86400, 2)
                except Exception as e:
                    health["error"] = str(e)
                    health["status"] = "degraded"
        else:
            health["status"] = "degraded"
    except Exception as e:
        health["status"] = "error"
        health["error"] = str(e)

    return health


def get_cached_time(key: str) -> Optional[int]:
    """
    Get the remaining TTL for a cache key.

    Args:
        key: Cache key to check

    Returns:
        TTL in seconds or None if key doesn't exist
    """
    try:
        redis_client = get_redis_connection()
        if redis_client:
            # Try to get TTL from Redis
            ttl = redis_client.ttl(key)  # type: ignore
            if ttl is not None and ttl > 0:
                return cast(int, ttl)
        # If we reach here, key not found or TTL not available
        return None
    except Exception as e:
        logger.warning(f"Error getting cache TTL for key {key}: {str(e)}")
        return None
