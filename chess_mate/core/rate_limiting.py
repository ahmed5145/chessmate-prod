"""
Rate limiting implementation for ChessMate API
"""

import logging
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiting implementation using Redis."""

    def __init__(self, backend: str = "default"):
        """Initialize the rate limiter with the specified cache backend."""
        self.backend = backend
        self.cache = caches[backend]

    def _parse_rate(self, rate: str) -> Tuple[int, int]:
        """Parse rate string into number of requests and time window."""
        if not rate or '/' not in rate:
            return 100, 3600  # Default: 100 per hour
            
        try:
            requests, seconds = rate.split('/', 1)
            return int(requests), int(seconds)
        except (ValueError, TypeError):
            logger.warning(f"Invalid rate format: {rate}. Using default.")
            return 100, 3600  # Default fallback

    def _get_cache_key(self, key_type: str, identifier: str) -> str:
        """Generate a cache key for rate limiting."""
        return f"ratelimit:{key_type}:{identifier}"

    def is_rate_limited(self, key_type: str, identifier: str, rate: str) -> bool:
        """Check if the request should be rate limited."""
        key = self._get_cache_key(key_type, identifier)
        
        # Parse rate
        max_requests, _ = self._parse_rate(rate)
        
        # Get current count
        try:
            # Get current count, ensure it's an integer
            current_str = self.cache.get(key)
            current = int(current_str) if current_str else 0
            
            # Compare with max requests
            return current >= max_requests
        except (ValueError, TypeError) as e:
            logger.warning(f"Rate limiting error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in rate limiting: {str(e)}")
            return False

    def increment(self, key_type: str, identifier: str, rate: str) -> None:
        """Increment the request counter for rate limiting."""
        key = self._get_cache_key(key_type, identifier)
        
        # Parse rate
        _, window = self._parse_rate(rate)
        
        try:
            # Get current count
            current_str = self.cache.get(key)
            current = int(current_str) if current_str is not None else 0
            
            # Increment and save as string to ensure compatibility
            self.cache.set(key, str(current + 1), window)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to increment rate limit counter: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error incrementing counter: {str(e)}")

    def get_remaining(self, key_type: str, identifier: str, rate: str) -> int:
        """Get the number of remaining requests allowed."""
        key = self._get_cache_key(key_type, identifier)
        
        # Parse rate
        max_requests, _ = self._parse_rate(rate)
        
        try:
            # Get current count
            current_str = self.cache.get(key)
            current = int(current_str) if current_str is not None else 0
            
            # Calculate remaining
            return max(0, max_requests - current)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error calculating remaining requests: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error in remaining calculation: {str(e)}")
            return 0

# Global instance
limiter = RateLimiter() 