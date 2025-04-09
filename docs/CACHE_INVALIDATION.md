# ChessMate Cache Invalidation System

This document explains the cache invalidation system implemented in the ChessMate application.

## Overview

The cache invalidation system provides a mechanism to efficiently invalidate cached data when it becomes stale. It uses a tag-based approach, where cache entries are associated with one or more tags, allowing for fine-grained invalidation.

## Tag-Based Invalidation

Cache tags work as follows:

1. Cache entries are associated with one or more tags through the `with_cache_tags` decorator.
2. When data changes, specific tags can be invalidated using the `invalidates_cache` decorator or the `invalidate_cache` function.
3. The system can also invalidate all cache entries with a global invalidation.

### Cache Tags

Cache tags are strings that represent categories of cached data. For example:

- `user_data`: For user-related cache entries
- `game_data`: For game-related cache entries
- `analysis`: For analysis-related cache entries
- `global`: Special tag that affects all cache entries

## Usage

### Associating Cache Entries with Tags

To associate a view or function with cache tags, use the `with_cache_tags` decorator:

```python
from core.cache_invalidation import with_cache_tags

@with_cache_tags('user_data', 'profile')
@api_view(['GET'])
def get_user_profile(request, user_id):
    # This view's cached responses will be associated with both 'user_data' and 'profile' tags
    # ...
```

### Invalidating Cache Entries

To invalidate cache entries when data changes, use the `invalidates_cache` decorator:

```python
from core.cache_invalidation import invalidates_cache

@invalidates_cache('user_data')
@api_view(['POST'])
def update_user_profile(request, user_id):
    # This view will invalidate all cache entries associated with the 'user_data' tag
    # ...
```

For class methods, use the `invalidates_cache_method` decorator:

```python
from core.cache_invalidation import invalidates_cache_method

class UserViewSet(viewsets.ModelViewSet):
    @invalidates_cache_method('user_data')
    def update(self, request, *args, **kwargs):
        # ...
```

To manually invalidate cache entries, use the `invalidate_cache` function:

```python
from core.cache_invalidation import invalidate_cache

def some_function():
    # Do something that changes user data

    # Invalidate the cache
    invalidate_cache('user_data')
```

### Invalidating Multiple Tags

You can invalidate multiple tags at once:

```python
@invalidates_cache('user_data', 'profile')
def update_profile(request):
    # ...
```

Or using the function:

```python
invalidate_cache(['user_data', 'profile'])
```

### Global Invalidation

To invalidate all cache entries, invalidate the `global` tag:

```python
from core.cache_invalidation import GLOBAL_TAG, invalidate_cache

invalidate_cache(GLOBAL_TAG)
```

Or use the admin endpoint:

```
POST /api/v1/system/cache/clear/
```

## Cache Middleware

The application includes a `CacheTagsMiddleware` that adds appropriate cache control headers to responses based on the cache tags associated with the view. It also adds a `Cache-Tag` header with the tags for CDN support.

Configuration in `settings.py`:

```python
MIDDLEWARE = [
    # ...
    'core.cache_invalidation.CacheTagsMiddleware',
    # ...
]
```

## API Endpoint for Cache Invalidation

The application provides an admin-only API endpoint for cache invalidation:

```
POST /api/v1/system/cache/clear/
```

This endpoint can be used to:

1. Invalidate specific tags:

```json
{
  "tags": ["user_data", "profile"]
}
```

2. Invalidate a specific pattern:

```json
{
  "pattern": "user:*"
}
```

3. Invalidate all cache entries (send an empty JSON object).

## Testing Cache Invalidation

The `tests/test_cache_invalidation.py` script can be used to test the cache invalidation system. See `tests/README.md` for details.

## Implementation Details

### Cache Keys

Cache keys are structured with a tag separator:

```
<base_key>::tag::<tag>
```

For example, a user profile cache entry might have:

- Main key: `chessmate:user:123:profile`
- Tag keys:
  - `chessmate:user:123:profile::tag::user_data`
  - `chessmate:user:123:profile::tag::profile`

### Invalidation Process

When a tag is invalidated:

1. Find all patterns associated with the tag in the tag patterns registry
2. Delete all cache keys matching those patterns
3. Delete all cache keys matching the pattern `*::tag::<tag>*`

### Redis Requirements

The cache invalidation system requires Redis as the cache backend, as it uses Redis pattern matching to find and delete cache keys. Make sure Redis is configured in `settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## Configuration

The cache invalidation system can be configured in `settings.py`:

```python
# Tag patterns to invalidate
CACHE_TAG_PATTERNS = {
    'user_data': ['user:*', 'profile:*'],
    'game_data': ['game:*', 'analysis:*'],
    'global': ['*'],
}
```

## Best Practices

1. Use specific tags for different types of data
2. Avoid invalidating the `global` tag frequently, as it can cause a cache stampede
3. Group related data under the same tag
4. Consider cache TTLs in addition to invalidation
5. Monitor cache hit/miss rates to ensure the invalidation strategy is effective
6. Test the cache invalidation system to ensure it works as expected
