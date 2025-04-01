import zlib
import json
from typing import Dict, Any, Optional, List, Union
from django.core.cache import cache, caches
from django.conf import settings
import logging
import hashlib
import redis

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        """Initialize cache manager with appropriate backend."""
        self.use_redis = getattr(settings, 'USE_REDIS', False)
        self.redis = None
        self.cache = caches['default']
        
        if self.use_redis:
            try:
                redis_url = getattr(settings, 'REDIS_URL', None)
                if redis_url:
                    self.redis = redis.Redis.from_url(
                        redis_url,
                        socket_timeout=2,
                        socket_connect_timeout=2,
                        retry_on_timeout=True
                    )
                    self.redis.ping()
                    logger.info("Successfully connected to Redis")
                else:
                    logger.warning("Redis URL not configured, falling back to default cache")
                    self.use_redis = False
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Failed to connect to Redis: {str(e)}")
                self.use_redis = False
            except Exception as e:
                logger.error(f"Unexpected error connecting to Redis: {str(e)}")
                self.use_redis = False

    def _compress_data(self, data: Any) -> bytes:
        """Compress data using zlib with highest compression."""
        try:
            return zlib.compress(json.dumps(data).encode(), level=9)
        except Exception as e:
            logger.error(f"Error compressing data: {str(e)}")
            return json.dumps(data).encode()

    def _decompress_data(self, data: Union[bytes, str]) -> Any:
        """Decompress data using zlib."""
        try:
            if isinstance(data, str):
                data = data.encode()
            return json.loads(zlib.decompress(data).decode())
        except Exception as e:
            logger.error(f"Error decompressing data: {str(e)}")
            try:
                if isinstance(data, bytes):
                    data = data.decode()
                return json.loads(data)
            except Exception as e:
                logger.error(f"Error parsing data: {str(e)}")
                return None

    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate a cache key."""
        return f"cm:{prefix}:{identifier}"

    def _hash_position(self, fen: str) -> str:
        """Generate a hash for a chess position."""
        return hashlib.blake2b(fen.encode(), digest_size=8).hexdigest()

    def cache_analysis(self, game_id: int, analysis_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache game analysis results."""
        try:
            key = self._generate_key('analysis', str(game_id))
            compressed_data = self._compress_data(analysis_data)
            timeout = ttl or getattr(settings, 'CACHE_TTL', {}).get('analysis', 3600)
            
            if self.use_redis and self.redis:
                return bool(self.redis.setex(key, timeout, compressed_data))
            else:
                self.cache.set(key, compressed_data, timeout=timeout)
                return True
        except Exception as e:
            logger.error(f"Error caching analysis: {str(e)}")
            return False

    def get_cached_analysis(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis results."""
        try:
            key = self._generate_key('analysis', str(game_id))
            
            if self.use_redis and self.redis:
                data = self.redis.get(key)
            else:
                data = self.cache.get(key)
                
            if data:
                return self._decompress_data(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached analysis: {str(e)}")
            return None

    def cache_position_evaluation(self, fen: str, evaluation: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache evaluation for a specific position."""
        try:
            key = self._generate_key('position', self._hash_position(fen))
            compressed_data = self._compress_data(evaluation)
            timeout = ttl or settings.CACHE_TTL.get('position', 86400)
            
            if self.use_redis:
                return bool(self.redis.set(key, compressed_data, timeout=timeout))
            else:
                self.cache.set(key, compressed_data, timeout=timeout)
                return True
        except Exception as e:
            logger.error(f"Error caching position evaluation: {str(e)}")
            return False

    def get_cached_position_evaluation(self, fen: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached position evaluation."""
        try:
            key = self._generate_key('position', self._hash_position(fen))
            
            if self.use_redis:
                data = self.redis.get(key)
            else:
                data = self.cache.get(key)
                
            if data:
                return self._decompress_data(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached position: {str(e)}")
            return None

    def cache_user_games(self, user_id: int, games: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Cache user's games list."""
        try:
            key = self._generate_key('games', str(user_id))
            compressed_data = self._compress_data(games)
            timeout = ttl or getattr(settings, 'CACHE_TTL', {}).get('games', 300)
            
            if self.use_redis and self.redis:
                return bool(self.redis.setex(key, timeout, compressed_data))
            else:
                self.cache.set(key, compressed_data, timeout=timeout)
                return True
        except Exception as e:
            logger.error(f"Error caching user games: {str(e)}")
            return False

    def get_cached_user_games(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached user's games list."""
        try:
            key = self._generate_key('games', str(user_id))
            
            if self.use_redis and self.redis:
                data = self.redis.get(key)
            else:
                data = self.cache.get(key)
                
            if data:
                return self._decompress_data(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached user games: {str(e)}")
            return None

    def clear_all_caches(self) -> bool:
        """Clear all caches."""
        try:
            if self.use_redis and self.redis:
                self.redis.flushdb()
            self.cache.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing caches: {str(e)}")
            return False

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        try:
            if not self.use_redis or not self.redis:
                return {
                    "analysis_count": 0,
                    "position_count": 0,
                    "games_count": 0,
                    "total_keys": 0
                }
            
            # Only count Redis keys
            analysis_keys = len([k for k in self.redis.scan_iter("cm:analysis:*")])
            position_keys = len([k for k in self.redis.scan_iter("cm:position:*")])
            games_keys = len([k for k in self.redis.scan_iter("cm:games:*")])
            
            return {
                "analysis_count": analysis_keys,
                "position_count": position_keys,
                "games_count": games_keys,
                "total_keys": analysis_keys + position_keys + games_keys
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "analysis_count": 0,
                "position_count": 0,
                "games_count": 0,
                "total_keys": 0
            } 