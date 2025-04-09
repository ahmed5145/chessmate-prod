"""ChessMate Django app configuration."""

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ChessMateConfig(AppConfig):
    """Django app configuration for ChessMate."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "chess_mate"

    def ready(self):
        """Initialize app-specific components when Django starts."""
        # Import and setup cache invalidation
        try:
            from chess_mate.core.cache_middleware import setup_cache_invalidation

            setup_cache_invalidation()
            logger.info("Cache invalidation system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize cache invalidation: {str(e)}")

        # Initialize Redis connection pool
        try:
            from chess_mate.core.redis_config import get_redis_client

            client = get_redis_client()
            info = client.info()
            logger.info(f"Redis connection established: {info.get('redis_version', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {str(e)}")

        # Import signal handlers
        try:
            import chess_mate.signals

            logger.info("Signal handlers registered")
        except Exception as e:
            logger.error(f"Failed to register signal handlers: {str(e)}")
