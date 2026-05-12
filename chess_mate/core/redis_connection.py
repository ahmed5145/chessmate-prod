"""Redis connection handling for ChessMate."""

import logging
import os
from typing import Optional

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

# Redis connection singleton
_redis_client = None

def get_redis_connection():
    """Get a Redis connection or return None if Redis is disabled or unreachable."""
    try:
        if getattr(settings, "REDIS_DISABLED", False):
            logger.warning("Redis is disabled via settings")
            return None

        # Prefer a full URL (REDIS_URL) when available (easier for environment injection).
        redis_url = getattr(settings, "REDIS_URL", None)
        if redis_url:
            # Don't log the full URL because it may contain credentials
            logger.info("Creating Redis client from REDIS_URL (credentials hidden)")
            # redis.from_url will create a client using a ConnectionPool internally
            client = redis.from_url(
                redis_url,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=getattr(settings, "REDIS_CONNECTION_POOL_SIZE", 10),
            )
        else:
            redis_host = getattr(settings, "REDIS_HOST", "localhost")
            redis_port = int(getattr(settings, "REDIS_PORT", 6379))  # Default Redis port
            redis_db = int(getattr(settings, "REDIS_DB", 0))
            redis_password = getattr(settings, "REDIS_PASSWORD", None)

            # Log connection details without password
            logger.info(f"Creating Redis connection pool for {redis_host}:{redis_port} (attempt 1)")

            # Create a connection pool for better performance
            pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                socket_timeout=5,  # 5 second timeout for operations
                socket_connect_timeout=5,  # 5 second timeout for connections
                retry_on_timeout=True,  # Retry on timeout
                health_check_interval=30,  # Check connection health periodically
                max_connections=getattr(settings, "REDIS_CONNECTION_POOL_SIZE", 10),
            )

            # Create a Redis client with the connection pool
            client = redis.Redis(connection_pool=pool)

        # Test connection with ping
        client.ping()
        logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
        return client
    except redis.RedisError as e:
        logger.warning(f"Redis error: {str(e)}")
        # If we can't connect to Redis, return None and the app will use fallback mechanisms
        return None
    except Exception as e:
        logger.warning(f"Unexpected error creating Redis connection: {str(e)}")
        return None 