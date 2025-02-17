"""Redis connection manager for ChessMate."""
from typing import Optional
import redis
from redis.connection import ConnectionPool
import logging
import os
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class RedisManager:
    """Singleton Redis connection manager with connection pooling."""
    _instance = None
    _lock = threading.Lock()
    _pool = None
    _initialized = False
    _MAX_CONNECTIONS = 20  # Reduced from 50
    _SOCKET_TIMEOUT = 5.0
    _CONNECT_TIMEOUT = 2.0

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RedisManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Redis connection pool if not already initialized."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._initialize_pool()
                    self._initialized = True

    def _initialize_pool(self):
        """Initialize the Redis connection pool with optimized settings."""
        try:
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                raise ValueError("REDIS_URL environment variable not set")

            self._pool = ConnectionPool.from_url(
                redis_url,
                max_connections=self._MAX_CONNECTIONS,
                socket_timeout=self._SOCKET_TIMEOUT,
                socket_connect_timeout=self._CONNECT_TIMEOUT,
                socket_keepalive=True,
                retry_on_timeout=True,
                health_check_interval=30,
                decode_responses=True
            )
            logger.info(f"Redis connection pool initialized with {self._MAX_CONNECTIONS} max connections")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection pool: {str(e)}")
            raise

    @contextmanager
    def get_client(self):
        """Get a Redis client from the connection pool with automatic cleanup."""
        client = None
        try:
            if not self._pool:
                with self._lock:
                    if not self._pool:
                        self._initialize_pool()
            client = redis.Redis(connection_pool=self._pool)
            yield client
        finally:
            if client:
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Error closing Redis client: {str(e)}")

    def get_connection_pool(self) -> Optional[ConnectionPool]:
        """Get the Redis connection pool."""
        if not self._pool:
            with self._lock:
                if not self._pool:
                    self._initialize_pool()
        return self._pool

    def close_all(self):
        """Close all connections in the pool."""
        if self._pool:
            with self._lock:
                if self._pool:
                    self._pool.disconnect()
                    self._pool = None
                    self._initialized = False
                    logger.info("All Redis connections closed")

    def __del__(self):
        """Ensure connections are cleaned up on deletion."""
        self.close_all()

# Global instance
redis_manager = RedisManager() 