"""Redis configuration and optimization for ChessMate."""

import json
import logging
import os
from functools import wraps
from typing import Any, Dict, List, Optional, Set, Union

import redis
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

# Redis connection pool configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_SOCKET_TIMEOUT = int(os.environ.get("REDIS_SOCKET_TIMEOUT", 5))
REDIS_SOCKET_CONNECT_TIMEOUT = int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", 5))
REDIS_RETRY_ON_TIMEOUT = os.environ.get("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
REDIS_CONNECTION_POOL_SIZE = int(os.environ.get("REDIS_CONNECTION_POOL_SIZE", 20))
REDIS_MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", 100))

# Redis key prefixes for different data types
KEY_PREFIX_GAME = "game:"
KEY_PREFIX_USER = "user:"
KEY_PREFIX_TASK = "task:"
KEY_PREFIX_ANALYSIS = "analysis:"
KEY_PREFIX_PLAYER = "player:"
KEY_PREFIX_CACHE_TAG = "tag:"
KEY_PREFIX_LOCK = "lock:"
KEY_PREFIX_RATE_LIMIT = "rate:"
KEY_PREFIX_STATS = "stats:"

# Redis TTL settings (in seconds)
TTL_GAME = 3600  # 1 hour
TTL_USER = 1800  # 30 minutes
TTL_TASK = 7200  # 2 hours
TTL_ANALYSIS = 86400  # 24 hours
TTL_PLAYER = 3600  # 1 hour
TTL_TAG = 86400  # 24 hours
TTL_LOCK = 300  # 5 minutes
TTL_RATE_LIMIT = 3600  # 1 hour
TTL_STATS = 86400  # 24 hours

# Initialize connection pool as None, will be created on first use
connection_pool = None

def get_redis_client() -> redis.Redis:
    """Get a Redis client from the connection pool with improved error handling and retries."""
    global connection_pool
    
    # Check if Redis is disabled in settings
    if getattr(settings, 'REDIS_DISABLED', False):
        logger.info("Redis is disabled, using dummy client")
        return DummyRedisClient()
        
    # Maximum number of retry attempts
    max_retries = 3
    retry_delay = 0.5  # seconds
    
    # Create connection pool if it doesn't exist
    if connection_pool is None:
        for attempt in range(max_retries):
            try:
                connection_pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                socket_timeout=REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
                retry_on_timeout=REDIS_RETRY_ON_TIMEOUT,
                max_connections=REDIS_MAX_CONNECTIONS,
                decode_responses=True,
                health_check_interval=30,  # Periodically check connections
                )
                logger.info(f"Created Redis connection pool for {REDIS_HOST}:{REDIS_PORT} (attempt {attempt+1})")
                break
            except Exception as e:
                logger.error(f"Failed to create Redis connection pool (attempt {attempt+1}): {str(e)}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.critical(f"Max retries ({max_retries}) reached for creating Redis connection pool")
                    return DummyRedisClient()
    
    # Get client from pool with retries
    for attempt in range(max_retries):
        try:
            client = redis.Redis(connection_pool=connection_pool)
            
            # Test connection with a ping
            if client.ping():
                return client
            else:
                logger.warning(f"Redis ping failed on attempt {attempt+1}")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error (attempt {attempt+1}): {str(e)}")
        except redis.TimeoutError as e:
            logger.error(f"Redis timeout error (attempt {attempt+1}): {str(e)}")
        except Exception as e:
            logger.error(f"Failed to get Redis client (attempt {attempt+1}): {str(e)}")
        
        # Retry after delay if this isn't the last attempt
        if attempt < max_retries - 1:
            import time
            time.sleep(retry_delay)
    
    # Return dummy client if all attempts failed
    logger.critical(f"All {max_retries} attempts to get Redis client failed, using dummy client")
    return DummyRedisClient()

# Dummy client for when Redis is unavailable
class DummyRedisClient:
    """
    Dummy Redis client that provides fallback behaviors when Redis is unavailable.
    This class logs operations and returns reasonable defaults for all Redis methods.
    """
    
    def __init__(self):
        self._local_cache = {}
        self._pipeline_commands = []
        logger.warning("Using DummyRedisClient - Redis operations will be simulated")
    
    def __getattr__(self, name):
        def dummy_method(*args, **kwargs):
            # Log the attempted operation
            arg_str = ', '.join([str(a) for a in args])
            kwargs_str = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
            all_args = ", ".join(filter(None, [arg_str, kwargs_str]))
            logger.debug(f"DummyRedisClient: {name}({all_args}) called but Redis is unavailable")
            
            # Simulate common Redis commands with local in-memory operations
            if name == 'get':
                key = args[0]
                return self._local_cache.get(key)
            elif name == 'set':
                key = args[0]
                value = args[1]
                self._local_cache[key] = value
                return True
            elif name == 'setex':
                key = args[0]
                value = args[2]  # args[1] is the TTL
                self._local_cache[key] = value
                return True
            elif name == 'delete' or name == 'del':
                key = args[0]
                if key in self._local_cache:
                    del self._local_cache[key]
                    return 1
                return 0
            elif name == 'exists':
                key = args[0]
                return 1 if key in self._local_cache else 0
            elif name == 'keys':
                pattern = args[0]
                import fnmatch
                return [k for k in self._local_cache.keys() if fnmatch.fnmatch(k, pattern)]
            elif name == 'hget':
                return None
            elif name == 'hgetall':
                return {}
            elif name == 'incr' or name == 'incrby':
                key = args[0]
                increment = args[1] if len(args) > 1 and name == 'incrby' else 1
                if key not in self._local_cache:
                    self._local_cache[key] = 0
                self._local_cache[key] += increment
                return self._local_cache[key]
            elif name == 'ping':
                return True
            elif name in ('hset', 'hmset', 'rpush', 'lpush', 'sadd', 'zadd'):
                return 1  # Simulate success for write operations
            else:
                return None if name in ('get', 'hget', 'hgetall') else False
        
        return dummy_method
    
    def pipeline(self):
        logger.debug("DummyRedisClient: Creating pipeline but Redis is unavailable")
        return self
    
    def execute(self):
        logger.debug(f"DummyRedisClient: Executing {len(self._pipeline_commands)} pipeline commands")
        results = []
        for cmd, args, kwargs in self._pipeline_commands:
            method = getattr(self, cmd)
            results.append(method(*args, **kwargs))
        self._pipeline_commands = []  # Reset after execution
        return results
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def get_redis_key(prefix: str, *args) -> str:
    """
    Create a Redis key with proper prefix and arguments.

    Args:
        prefix: Key prefix (e.g., KEY_PREFIX_GAME)
        *args: Additional arguments to append to the key

    Returns:
        Formatted Redis key

    Example:
        get_redis_key(KEY_PREFIX_GAME, 123) -> 'game:123'
    """
    return f"{prefix}{':'.join(str(arg) for arg in args)}"


def redis_get(key: str) -> Optional[Any]:
    """
    Get a value from Redis with proper error handling.

    Args:
        key: Redis key

    Returns:
        Deserialized value or None if not found or error
    """
    try:
        client = get_redis_client()
        data = client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Redis get error for key {key}: {str(e)}")
        return None


def redis_set(key: str, value: Any, ttl: int = None) -> bool:
    """
    Set a value in Redis with proper error handling.

    Args:
        key: Redis key
        value: Value to store (will be JSON serialized)
        ttl: Time to live in seconds

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        serialized = json.dumps(value)
        if ttl:
            return client.setex(key, ttl, serialized)
        else:
            return client.set(key, serialized)
    except Exception as e:
        logger.error(f"Redis set error for key {key}: {str(e)}")
        return False


def redis_delete(key: str) -> bool:
    """
    Delete a key from Redis with proper error handling.

    Args:
        key: Redis key

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        return client.delete(key) > 0
    except Exception as e:
        logger.error(f"Redis delete error for key {key}: {str(e)}")
        return False


def redis_exists(key: str) -> bool:
    """
    Check if a key exists in Redis.

    Args:
        key: Redis key

    Returns:
        True if key exists, False otherwise
    """
    try:
        client = get_redis_client()
        return client.exists(key) > 0
    except Exception as e:
        logger.error(f"Redis exists error for key {key}: {str(e)}")
        return False


def redis_incr(key: str, amount: int = 1, ttl: int = None) -> Optional[int]:
    """
    Increment a value in Redis with proper error handling.

    Args:
        key: Redis key
        amount: Amount to increment
        ttl: Time to live if key doesn't exist

    Returns:
        New value or None if error
    """
    try:
        client = get_redis_client()
        pipeline = client.pipeline()
        pipeline.incrby(key, amount)

        # Set TTL if provided and key doesn't exist
        if ttl and not client.exists(key):
            pipeline.expire(key, ttl)

        results = pipeline.execute()
        return results[0]
    except Exception as e:
        logger.error(f"Redis incr error for key {key}: {str(e)}")
        return None


def redis_keys(pattern: str) -> List[str]:
    """
    Find keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., 'game:*')

    Returns:
        List of matching keys
    """
    try:
        client = get_redis_client()
        keys = client.keys(pattern)
        return [key.decode("utf-8") for key in keys]
    except Exception as e:
        logger.error(f"Redis keys error for pattern {pattern}: {str(e)}")
        return []


def redis_pipeline_execute(commands: List[Dict[str, Any]]) -> Optional[List[Any]]:
    """
    Execute multiple Redis commands in a pipeline.

    Args:
        commands: List of command dictionaries with keys 'cmd', 'args', and 'kwargs'

    Returns:
        List of results or None if error

    Example:
        redis_pipeline_execute([
            {'cmd': 'set', 'args': ['key1', 'value1'], 'kwargs': {'ex': 60}},
            {'cmd': 'get', 'args': ['key2']}
        ])
    """
    try:
        client = get_redis_client()
        pipeline = client.pipeline()

        for command in commands:
            cmd = command["cmd"]
            args = command.get("args", [])
            kwargs = command.get("kwargs", {})

            # Get the method
            method = getattr(pipeline, cmd)

            # Call the method with args and kwargs
            method(*args, **kwargs)

        return pipeline.execute()
    except Exception as e:
        logger.error(f"Redis pipeline execute error: {str(e)}")
        return None


def redis_lock(lock_name: str, timeout: int = TTL_LOCK) -> Optional[str]:
    """
    Acquire a distributed lock.

    Args:
        lock_name: Name of the lock
        timeout: Lock timeout in seconds

    Returns:
        Lock identifier if acquired, None otherwise
    """
    try:
        import uuid

        client = get_redis_client()
        lock_id = str(uuid.uuid4())
        lock_key = get_redis_key(KEY_PREFIX_LOCK, lock_name)

        # Try to acquire the lock
        acquired = client.set(lock_key, lock_id, ex=timeout, nx=True)

        if acquired:
            return lock_id
        return None
    except Exception as e:
        logger.error(f"Redis lock error for {lock_name}: {str(e)}")
        return None


def redis_unlock(lock_name: str, lock_id: str) -> bool:
    """
    Release a distributed lock.

    Args:
        lock_name: Name of the lock
        lock_id: Lock identifier returned by redis_lock

    Returns:
        True if released, False otherwise
    """
    try:
        client = get_redis_client()
        lock_key = get_redis_key(KEY_PREFIX_LOCK, lock_name)

        # Only release if we own the lock
        if client.get(lock_key) == lock_id.encode("utf-8"):
            client.delete(lock_key)
            return True
        return False
    except Exception as e:
        logger.error(f"Redis unlock error for {lock_name}: {str(e)}")
        return False


def with_redis_lock(lock_name: str, timeout: int = TTL_LOCK):
    """
    Decorator to execute a function with a Redis lock.

    Args:
        lock_name: Name of the lock or function to generate lock name
        timeout: Lock timeout in seconds

    Example:
        @with_redis_lock('my_lock')
        def my_function(arg1, arg2):
            # Critical section
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate lock name dynamically if callable
            if callable(lock_name):
                actual_lock_name = lock_name(*args, **kwargs)
            else:
                actual_lock_name = lock_name

            # Try to acquire lock
            lock_id = redis_lock(actual_lock_name, timeout)
            if not lock_id:
                logger.warning(f"Could not acquire lock: {actual_lock_name}")
                return None

            try:
                # Execute function
                return func(*args, **kwargs)
            finally:
                # Release lock
                redis_unlock(actual_lock_name, lock_id)

        return wrapper

    return decorator


def redis_cache(prefix: str, ttl: int = None, args_as_key: bool = True):
    """
    Decorator to cache function results in Redis.

    Args:
        prefix: Key prefix
        ttl: Time to live in seconds
        args_as_key: Whether to use function arguments as part of the cache key

    Example:
        @redis_cache(KEY_PREFIX_GAME, TTL_GAME)
        def get_game(game_id):
            # Expensive operation
            return game_data
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if args_as_key:
                key = get_redis_key(prefix, func.__name__, *args, *kwargs.values())
            else:
                key = get_redis_key(prefix, func.__name__)

            # Check cache
            cached = redis_get(key)
            if cached is not None:
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            if result is not None:
                redis_set(key, result, ttl)

            return result

        return wrapper

    return decorator


def redis_invalidate_by_prefix(prefix: str) -> int:
    """
    Invalidate all keys with a given prefix.

    Args:
        prefix: Key prefix

    Returns:
        Number of keys invalidated
    """
    try:
        client = get_redis_client()
        keys = client.keys(f"{prefix}*")

        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Redis invalidate by prefix error for {prefix}: {str(e)}")
        return 0


def redis_invalidate_by_tags(tags: Union[str, List[str]]) -> int:
    """
    Invalidate all keys associated with given tags.

    Args:
        tags: Tag or list of tags

    Returns:
        Number of keys invalidated
    """
    if isinstance(tags, str):
        tags = [tags]

    try:
        client = get_redis_client()
        pipeline = client.pipeline()

        # Get all keys for each tag
        all_keys = set()
        for tag in tags:
            tag_key = get_redis_key(KEY_PREFIX_CACHE_TAG, tag)
            keys = client.smembers(tag_key)
            if keys:
                # Convert bytes to strings
                keys = [key.decode("utf-8") for key in keys]
                all_keys.update(keys)

                # Clear the tag
                pipeline.delete(tag_key)

        # Delete all keys
        if all_keys:
            pipeline.delete(*all_keys)

        results = pipeline.execute()

        # Sum all deletions
        return sum([result for result in results if isinstance(result, int)])
    except Exception as e:
        logger.error(f"Redis invalidate by tags error for {tags}: {str(e)}")
        return 0


def redis_add_to_tag(tag: str, key: str) -> bool:
    """
    Add a key to a tag for later invalidation.

    Args:
        tag: Tag name
        key: Redis key to associate with tag

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        tag_key = get_redis_key(KEY_PREFIX_CACHE_TAG, tag)
        client.sadd(tag_key, key)
        client.expire(tag_key, TTL_TAG)
        return True
    except Exception as e:
        logger.error(f"Redis add to tag error for {tag}, {key}: {str(e)}")
        return False


def redis_get_tag_keys(tag: str) -> Set[str]:
    """
    Get all keys associated with a tag.

    Args:
        tag: Tag name

    Returns:
        Set of keys
    """
    try:
        client = get_redis_client()
        tag_key = get_redis_key(KEY_PREFIX_CACHE_TAG, tag)
        keys = client.smembers(tag_key)
        return {key.decode("utf-8") for key in keys}
    except Exception as e:
        logger.error(f"Redis get tag keys error for {tag}: {str(e)}")
        return set()


def redis_hashmap_set(key: str, field: str, value: Any, ttl: int = None) -> bool:
    """
    Set a field in a Redis hash.

    Args:
        key: Redis key
        field: Hash field
        value: Value to store (will be JSON serialized)
        ttl: Time to live for the entire hash

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        serialized = json.dumps(value)
        result = client.hset(key, field, serialized)

        # Set TTL if provided
        if ttl:
            client.expire(key, ttl)

        return result > 0
    except Exception as e:
        logger.error(f"Redis hashmap set error for {key}:{field}: {str(e)}")
        return False


def redis_hashmap_get(key: str, field: str) -> Optional[Any]:
    """
    Get a field from a Redis hash.

    Args:
        key: Redis key
        field: Hash field

    Returns:
        Deserialized value or None if not found or error
    """
    try:
        client = get_redis_client()
        data = client.hget(key, field)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Redis hashmap get error for {key}:{field}: {str(e)}")
        return None


def redis_hashmap_getall(key: str) -> Dict[str, Any]:
    """
    Get all fields from a Redis hash.

    Args:
        key: Redis key

    Returns:
        Dictionary of deserialized values
    """
    try:
        client = get_redis_client()
        data = client.hgetall(key)
        if not data:
            return {}

        # Deserialize all values
        result = {}
        for field, value in data.items():
            field = field.decode("utf-8")
            result[field] = json.loads(value)

        return result
    except Exception as e:
        logger.error(f"Redis hashmap getall error for {key}: {str(e)}")
        return {}


def redis_hashmap_delete(key: str, field: str) -> bool:
    """
    Delete a field from a Redis hash.

    Args:
        key: Redis key
        field: Hash field

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        return client.hdel(key, field) > 0
    except Exception as e:
        logger.error(f"Redis hashmap delete error for {key}:{field}: {str(e)}")
        return False


# Utility functions for specific ChessMate data types


def cache_game(game_id: int, data: Dict[str, Any]) -> bool:
    """Cache game data with proper TTL."""
    key = get_redis_key(KEY_PREFIX_GAME, game_id)
    return redis_set(key, data, TTL_GAME)


def get_cached_game(game_id: int) -> Optional[Dict[str, Any]]:
    """Get cached game data."""
    key = get_redis_key(KEY_PREFIX_GAME, game_id)
    return redis_get(key)


def invalidate_game_cache(game_id: int) -> bool:
    """Invalidate game cache."""
    key = get_redis_key(KEY_PREFIX_GAME, game_id)
    return redis_delete(key)


def cache_user_games(user_id: int, data: List[Dict[str, Any]]) -> bool:
    """Cache user games with proper TTL."""
    key = get_redis_key(KEY_PREFIX_USER, user_id, "games")
    return redis_set(key, data, TTL_USER)


def get_cached_user_games(user_id: int) -> Optional[List[Dict[str, Any]]]:
    """Get cached user games."""
    key = get_redis_key(KEY_PREFIX_USER, user_id, "games")
    return redis_get(key)


def invalidate_user_games_cache(user_id: int) -> bool:
    """Invalidate user games cache."""
    key = get_redis_key(KEY_PREFIX_USER, user_id, "games")
    return redis_delete(key)


def cache_analysis(analysis_id: int, data: Dict[str, Any]) -> bool:
    """Cache analysis data with proper TTL."""
    key = get_redis_key(KEY_PREFIX_ANALYSIS, analysis_id)
    return redis_set(key, data, TTL_ANALYSIS)


def get_cached_analysis(analysis_id: int) -> Optional[Dict[str, Any]]:
    """Get cached analysis data."""
    key = get_redis_key(KEY_PREFIX_ANALYSIS, analysis_id)
    return redis_get(key)


def invalidate_analysis_cache(analysis_id: int) -> bool:
    """Invalidate analysis cache."""
    key = get_redis_key(KEY_PREFIX_ANALYSIS, analysis_id)
    return redis_delete(key)


def cache_player(source: str, username: str, data: Dict[str, Any]) -> bool:
    """Cache player data with proper TTL."""
    key = get_redis_key(KEY_PREFIX_PLAYER, source, username)
    return redis_set(key, data, TTL_PLAYER)


def get_cached_player(source: str, username: str) -> Optional[Dict[str, Any]]:
    """Get cached player data."""
    key = get_redis_key(KEY_PREFIX_PLAYER, source, username)
    return redis_get(key)


def invalidate_player_cache(player_id):
    """
    Invalidate cache for a specific player.
    
    Args:
        player_id: Player ID
    """
    if not player_id:
        return
    
    key = f"{KEY_PREFIX_PLAYER}{player_id}"
    redis_invalidate_by_prefix(key)


def track_cache_hit(cache_type: str) -> None:
    """Track a cache hit for statistics."""
    key = get_redis_key(KEY_PREFIX_STATS, "cache", "hit", cache_type)
    redis_incr(key, 1, TTL_STATS)


def track_cache_miss(cache_type: str) -> None:
    """Track a cache miss for statistics."""
    key = get_redis_key(KEY_PREFIX_STATS, "cache", "miss", cache_type)
    redis_incr(key, 1, TTL_STATS)


def get_cache_stats() -> Dict[str, Dict[str, int]]:
    """Get cache hit/miss statistics."""
    hit_keys = redis_keys(f"{KEY_PREFIX_STATS}cache:hit:*")
    miss_keys = redis_keys(f"{KEY_PREFIX_STATS}cache:miss:*")

    stats = {"hits": {}, "misses": {}}

    # Process hit keys
    for key in hit_keys:
        cache_type = key.split(":")[-1]
        count = redis_get(key) or 0
        stats["hits"][cache_type] = count

    # Process miss keys
    for key in miss_keys:
        cache_type = key.split(":")[-1]
        count = redis_get(key) or 0
        stats["misses"][cache_type] = count

    return stats
