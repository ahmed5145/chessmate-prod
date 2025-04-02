# Rate Limiting in ChessMate API

This document explains how rate limiting works in the ChessMate API and how to configure it.

## Overview

Rate limiting is a technique used to control the amount of incoming and outgoing traffic to or from a network, server, or application. In the ChessMate API, rate limiting protects our infrastructure and ensures fair usage across all users.

## Implementation

ChessMate implements rate limiting through:

1. A `RateLimiter` class that handles the core rate limiting logic
2. A `RateLimitMiddleware` that applies rate limiting to all API requests
3. A `rate_limit` decorator for specific views that need custom rate limiting

## Features

- **Different limits for different endpoint types**: Authentication, game management, analysis, feedback, profile, and dashboard endpoints can each have their own rate limits.
- **IP-based and user-based limiting**: Anonymous users are limited by IP address, while authenticated users are limited by their user ID.
- **Configurable time windows and request limits**: Easily adjust limits in the settings.
- **Excluded paths**: Some endpoints like health checks and API documentation are excluded from rate limiting.
- **Response headers**: All responses include rate limit headers showing limits, remaining requests, and reset time.
- **Standardized error responses**: When rate limits are exceeded, a standardized error response is returned.

## Configuration

Rate limiting is configured in the Django settings:

```python
# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'DEFAULT': {'MAX_REQUESTS': 100, 'TIME_WINDOW': 3600},  # 100 requests per hour
    'AUTH': {'MAX_REQUESTS': 20, 'TIME_WINDOW': 3600},      # 20 requests per hour
    'GAME': {'MAX_REQUESTS': 50, 'TIME_WINDOW': 3600},      # 50 requests per hour
    'ANALYSIS': {'MAX_REQUESTS': 30, 'TIME_WINDOW': 3600},  # 30 requests per hour
    'FEEDBACK': {'MAX_REQUESTS': 20, 'TIME_WINDOW': 3600},  # 20 requests per hour
    'PROFILE': {'MAX_REQUESTS': 60, 'TIME_WINDOW': 3600},   # 60 requests per hour
    'DASHBOARD': {'MAX_REQUESTS': 60, 'TIME_WINDOW': 3600}, # 60 requests per hour
}

# Rate limiting patterns for different endpoint types
RATE_LIMIT_PATTERNS = {
    'AUTH': [
        r'^/api/(register|login|logout|token/refresh|reset-password|verify-email)/?.*$',
    ],
    'GAME': [
        r'^/api/games/?$',
        r'^/api/games/fetch/?$',
    ],
    # ... other patterns
}

# Paths excluded from rate limiting
RATE_LIMIT_EXCLUDED_PATHS = [
    r'^/api/health/?$',
    r'^/api/csrf/?$',
    r'^/api/docs/?.*$',
    r'^/api/version/?$',
]
```

### Configuration Options

- `RATE_LIMIT_CONFIG`: Dictionary mapping endpoint types to their rate limit configurations
  - `MAX_REQUESTS`: Maximum number of requests allowed in the time window
  - `TIME_WINDOW`: Time window in seconds
- `RATE_LIMIT_PATTERNS`: Dictionary mapping endpoint types to patterns that match their URLs
- `RATE_LIMIT_EXCLUDED_PATHS`: List of URL patterns that are excluded from rate limiting
- `USE_REDIS`: Boolean indicating whether to use Redis for rate limiting

## Response Headers

All API responses include these rate limit headers:

- `X-RateLimit-Limit`: The maximum number of requests that can be made in the window
- `X-RateLimit-Remaining`: The number of requests remaining in the current window
- `X-RateLimit-Reset`: The time in seconds until the rate limit resets

## Error Response

When a rate limit is exceeded, the API returns a 429 Too Many Requests response:

```json
{
  "status": "error",
  "code": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again in 3600 seconds.",
  "details": {
    "reset_time": 3600,
    "endpoint_type": "AUTH"
  },
  "request_id": "unique-request-id"
}
```

## Using the Decorator

For views that need custom rate limiting, you can use the `rate_limit` decorator:

```python
from core.decorators import rate_limit

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
def login_view(request):
    # The code here
```

## Storage Backends

ChessMate supports two storage backends for rate limiting:

1. **In-memory cache**: Used by default for development
2. **Redis**: Recommended for production use as it provides better persistence and scaling

To use Redis, set `USE_REDIS=True` in your environment variables.

## Best Practices

1. **Client-Side Handling**: Implement proper backoff and retry logic in your client applications
2. **Monitor Rate Limits**: Keep an eye on rate limit headers to avoid hitting limits
3. **Batch Operations**: Where possible, use batch endpoints to reduce the number of API calls
4. **Caching**: Cache API responses on the client side to reduce the need for repeated requests

## Testing

To test rate limiting, you can use the `locust` or similar tools to simulate high load.

---

*Last Updated: April 2, 2025*
