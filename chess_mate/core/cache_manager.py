import zlib
import json
from typing import Dict, Any, Optional, List, Union
from django.core.cache import cache, caches
from django.conf import settings
import logging
import hashlib

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        """Initialize cache manager with Redis connection if available."""
        self.use_redis = bool(settings.REDIS_URL)
        if self.use_redis:
            try:
                self.redis_cache = caches['default']
                self.local_cache = caches['local']
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                self.use_redis = False
                self.redis_cache = None
                self.local_cache = cache

    def _compress_data(self, data: Any) -> bytes:
        """Compress data using zlib with highest compression."""
        return zlib.compress(json.dumps(data).encode(), level=9)

    def _decompress_data(self, data: bytes) -> Any:
        """Decompress data using zlib."""
        return json.loads(zlib.decompress(data).decode())

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
            timeout = ttl or settings.CACHE_TTL.get('analysis', 3600)
            
            if self.use_redis:
                return bool(self.redis_cache.set(key, compressed_data, timeout=timeout))
            else:
                self.local_cache.set(key, compressed_data, timeout=timeout)
                return True
        except Exception as e:
            logger.error(f"Error caching analysis: {str(e)}")
            return False

    def get_cached_analysis(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis results."""
        try:
            key = self._generate_key('analysis', str(game_id))
            
            if self.use_redis:
                data = self.redis_cache.get(key)
            else:
                data = self.local_cache.get(key)
                
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
                return bool(self.redis_cache.set(key, compressed_data, timeout=timeout))
            else:
                self.local_cache.set(key, compressed_data, timeout=timeout)
                return True
        except Exception as e:
            logger.error(f"Error caching position evaluation: {str(e)}")
            return False

    def get_cached_position_evaluation(self, fen: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached position evaluation."""
        try:
            key = self._generate_key('position', self._hash_position(fen))
            
            if self.use_redis:
                data = self.redis_cache.get(key)
            else:
                data = self.local_cache.get(key)
                
            if data:
                return self._decompress_data(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached position: {str(e)}")
            return None

    def cache_user_games(self, user_id: int, games: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Cache user's games list with local memory cache."""
        try:
            key = self._generate_key('games', str(user_id))
            compressed_data = self._compress_data(games)
            timeout = ttl or settings.CACHE_TTL.get('games', 300)
            
            # Always use local cache for games list
            self.local_cache.set(key, compressed_data, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Error caching user games: {str(e)}")
            return False

    def get_cached_user_games(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached user's games list from local memory cache."""
        try:
            key = self._generate_key('games', str(user_id))
            data = self.local_cache.get(key)
            
            if data:
                return self._decompress_data(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached user games: {str(e)}")
            return None

    def clear_all_caches(self) -> bool:
        """Clear all caches."""
        try:
            if self.use_redis:
                self.redis_cache.clear()
            self.local_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing caches: {str(e)}")
            return False

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        try:
            if not self.use_redis:
                return {
                    "analysis_count": 0,
                    "position_count": 0,
                    "games_count": 0,
                    "total_keys": 0
                }
            
            # Only count Redis keys
            analysis_keys = len([k for k in self.redis_cache.keys() if k.startswith('cm:analysis:')])
            position_keys = len([k for k in self.redis_cache.keys() if k.startswith('cm:position:')])
            games_keys = len([k for k in self.local_cache.keys() if k.startswith('cm:games:')])
            
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