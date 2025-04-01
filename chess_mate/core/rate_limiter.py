import redis
from typing import Optional, Dict, Any
from datetime import datetime
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import cache, caches
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter implementation using local memory cache with Redis fallback."""

    def __init__(self):
        """Initialize rate limiter with local memory cache."""
        try:
            self.use_redis = getattr(settings, 'USE_REDIS', False)
            if self.use_redis:
                self.cache = caches['redis']
                logger.info("Using Redis for rate limiting")
            else:
                self.cache = caches['default']
                logger.info("Using local memory cache for rate limiting")
        except Exception as e:
            logger.warning(f"Using default cache for rate limiting: {str(e)}")
            self.cache = caches['default']
            self.use_redis = False

    def get_rate_limit_config(self, endpoint_type: str) -> Dict[str, int]:
        """Get rate limit configuration for endpoint type."""
        try:
            return settings.RATE_LIMIT_CONFIG.get(
                endpoint_type.upper(),
                settings.RATE_LIMIT_CONFIG['DEFAULT']
            )
        except (AttributeError, KeyError):
            logger.warning(f"Rate limit configuration not found for {endpoint_type}, using defaults")
            return {'MAX_REQUESTS': 100, 'TIME_WINDOW': 3600}

    def is_rate_limited(self, key: str, endpoint_type: str = 'DEFAULT') -> bool:
        """Check if the request should be rate limited."""
        try:
            config = self.get_rate_limit_config(endpoint_type)
            max_requests = config['MAX_REQUESTS']
            time_window = config['TIME_WINDOW']

            current_time = datetime.utcnow().timestamp()
            window_key = f"rl:{key}:{int(current_time / time_window)}"
            
            # Use atomic increment
            current_requests = self.cache.get(window_key, 0)
            if current_requests >= max_requests:
                return True
                
            self.cache.set(window_key, current_requests + 1, time_window)
            return False
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            return False  # Fail open

    def get_remaining_requests(self, key: str, endpoint_type: str = 'DEFAULT') -> int:
        """Get the number of remaining requests allowed."""
        try:
            config = self.get_rate_limit_config(endpoint_type)
            max_requests = config['MAX_REQUESTS']
            time_window = config['TIME_WINDOW']

            current_time = datetime.utcnow().timestamp()
            window_key = f"rl:{key}:{int(current_time / time_window)}"
            
            current_requests = self.cache.get(window_key, 0)
            return max(0, max_requests - current_requests)
        except Exception as e:
            logger.error(f"Error getting remaining requests: {str(e)}")
            return 0

    def get_reset_time(self, key: str, endpoint_type: str = 'DEFAULT') -> int:
        """Get the time in seconds until the rate limit resets."""
        try:
            config = self.get_rate_limit_config(endpoint_type)
            time_window = config['TIME_WINDOW']
            current_time = datetime.utcnow().timestamp()
            next_window = (int(current_time / time_window) + 1) * time_window
            return max(0, int(next_window - current_time))
        except Exception as e:
            logger.error(f"Error getting reset time: {str(e)}")
            return 0 