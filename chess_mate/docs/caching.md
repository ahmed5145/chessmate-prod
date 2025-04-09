# ChessMate Caching Strategy

This document outlines the caching strategy used in the ChessMate application to improve performance, reduce database load, and enhance scalability.

## Overview

ChessMate implements a multi-tiered caching strategy:

1. **Redis Cache** - For persistent, shared caching across application instances
2. **In-Memory Cache** - For fast, local caching when Redis is not available

The caching system is designed to:
- Improve response times for frequently accessed data
- Reduce database load for expensive queries
- Prevent cache stampede with stale-while-revalidate pattern
- Support efficient cache invalidation for data updates

## Cache Backends

The application uses two primary cache backends:

- **Default (Memory)**: Django's built-in LocMemCache for local caching
- **Redis**: For distributed caching across multiple application instances

## Cached Data Types

The following data types are cached in the application:

| Data Type | Cache Key Prefix | Timeout | Backend |
|-----------|-----------------|---------|---------|
| User Profile | `user_profile` | 1 hour | Redis |
| User Games List | `user_games` | 15 minutes | Redis |
| Game Details | `game_details` | 1 hour | Redis |
| Game Analysis | `game_analysis` | 24 hours | Redis |
| Leaderboards | `leaderboard` | 5 minutes | Redis |
| User Progress | `user_progress` | 1 hour | Redis |
| Static Content | `static_content` | 24 hours | Redis |

## Cache Implementation

### Cache Decorators

The application provides the following decorators for easy cache implementation:

1. **`@cached`** - For caching view results
   ```python
   @cached(timeout=60*15, key_prefix="user_games", cache_backend=CACHE_BACKEND_REDIS)
   def user_games_view(request):
       # View logic
   ```

2. **`@invalidate_cache_for`** - For invalidating cache entries when data is modified
   ```python
   @invalidate_cache_for(key_prefix="user_profile")
   def update_profile(request):
       # View logic that modifies user profile data
   ```

### Cache Utility Functions

The application also provides the following utility functions:

1. **`cache_get`** - Get a value from the cache
2. **`cache_set`** - Set a value in the cache
3. **`cache_delete`** - Delete a value from the cache
4. **`cache_stampede_prevention`** - Prevent cache stampede with stale data strategy
5. **`generate_cache_key`** - Generate a cache key from prefix and parameters

## Cache Invalidation Strategy

Cache invalidation is handled through:

1. **Time-based expiration** - All cached data has a defined timeout
2. **Explicit invalidation** - When data is modified, related caches are explicitly invalidated
3. **Pattern-based invalidation** - Redis supports deleting all keys matching a pattern

### Invalidation Examples

- When a user profile is updated, the `user_profile` cache is invalidated
- When games are fetched, the `user_games` cache is invalidated
- When a game is analyzed, the `game_analysis` cache for that game is invalidated

## Preventing Cache Stampede

Cache stampede (or thundering herd) occurs when many requests attempt to regenerate a cache value simultaneously. ChessMate prevents this using:

1. **Stale-while-revalidate pattern** - Serve stale data while refreshing in background
2. **Lock-based prevention** - Use a lock to ensure only one process refreshes the cache

```python
def get_expensive_data():
    return cache_stampede_prevention(
        "expensive_data_key",
        expensive_calculation_function,
        timeout=300,
        backend_name=CACHE_BACKEND_REDIS
    )
```

## Redis Configuration

Redis is configured in `settings.py` with optimized connection pooling and serialization:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
    'redis': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            },
            'KEY_PREFIX': 'chessmate',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_FUNCTION': 'chess_mate.core.cache.generate_cache_key',
        'TIMEOUT': 300,  # 5 minutes default timeout
    }
}
```

## Best Practices

When implementing caching in ChessMate, follow these best practices:

1. **Cache Selectively**: Only cache data that is:
   - Frequently accessed
   - Computationally expensive to generate
   - Not highly volatile

2. **Appropriate Timeouts**: Choose timeouts appropriate to the data:
   - Short timeouts (< 5 min) for rapidly changing data
   - Longer timeouts (hours/days) for static or semi-static data

3. **Smart Key Generation**:
   - Include all relevant parameters in cache keys
   - For authenticated views, include user ID in the key
   - Use helper functions to generate consistent keys

4. **Cache Invalidation**:
   - Always invalidate related caches when data is modified
   - Use decorators for consistent invalidation patterns

5. **Error Handling**:
   - Cache operations should never cause application errors
   - Always handle cache exceptions gracefully

## Monitoring and Debugging

Redis caching is monitored through:

1. Application logs - Cache hits/misses are logged
2. Redis monitoring tools - For tracking memory usage and performance
3. Django Debug Toolbar - For development environment cache inspection

## Future Improvements

Planned improvements to the caching system:

1. Implement cache prefetching for commonly accessed data
2. Add cache warming on application startup
3. Implement more granular cache invalidation strategies
4. Add circuit breakers to fall back to database when Redis is unavailable
