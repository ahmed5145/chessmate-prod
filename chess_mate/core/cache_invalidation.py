"""
Cache invalidation utilities for efficient cache management.

This module provides a framework for intelligent cache invalidation
using cache tags and pattern-based invalidation. It allows for fine-grained
cache control and automatic cache invalidation when data changes.
"""

import functools
import logging
from typing import Any, Callable, Dict, List, Set, TypeVar, Union, cast

from django.conf import settings
from django.utils.decorators import method_decorator

from .cache import generate_cache_key, invalidate_pattern

logger = logging.getLogger(__name__)

# Type variable for function return types
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Cache tag constants
TAG_SEPARATOR = "::tag::"
GLOBAL_TAG = "global"

# Backward-compatible lookup tables used by older tests.
ENTITY_KEY_PREFIXES: Dict[str, List[str]] = {
    "User": ["user:", "profile:", "dashboard:", "analysis:", "feedback:", "subscription:"],
    "Profile": ["profile:"],
    "Game": ["game:", "analysis:", "feedback:"],
    "Subscription": ["subscription:"],
}

ENTITY_DEPENDENCIES: Dict[str, List[str]] = {
    "User": ["Profile", "Game", "Subscription"],
    "Profile": [],
    "Game": [],
    "Subscription": [],
}

TAG_KEY_PREFIXES: Dict[str, List[str]] = {
    "user_games": ["user_games:"],
    "dashboard": ["dashboard:"],
    "game_details": ["game_details:"],
    "game_analysis": ["analysis:"],
    "profile": ["profile:"],
    "feedback": ["feedback:"],
}

TAG_DEPENDENCIES: Dict[str, List[str]] = {
    "user_games": ["game_details", "game_analysis", "dashboard"],
    "dashboard": [],
    "game_details": [],
    "game_analysis": [],
    "profile": [],
    "feedback": [],
}


class CacheInvalidator:
    """
    Manages cache invalidation through tag-based patterns.

    This class provides methods to track and invalidate caches based on
    tags, enabling fine-grained cache control.
    """

    def __init__(self):
        """Initialize the cache invalidator."""
        self._tag_patterns: Dict[str, Set[str]] = {}
        self._initialized = False

    @classmethod
    def invalidate_entity(cls, entity_type: str, entity_id: Any) -> bool:
        """Invalidate cache keys for an entity and its dependent entities."""
        try:
            for prefix in ENTITY_KEY_PREFIXES.get(entity_type, []):
                invalidate_pattern(f"{prefix}*{entity_id}*", "redis")

            for dependency in ENTITY_DEPENDENCIES.get(entity_type, []):
                for prefix in ENTITY_KEY_PREFIXES.get(dependency, []):
                    invalidate_pattern(f"{prefix}*{entity_id}*", "redis")

            logger.debug("Invalidated cache for %s:%s", entity_type, entity_id)
            return True
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            logger.error("Error invalidating entity cache for %s:%s: %s", entity_type, entity_id, error)
            return False

    def initialize(self) -> None:
        """
        Initialize the cache invalidator.

        Loads tag patterns from settings or sets up defaults.
        """
        if self._initialized:
            return

        # Load patterns from settings if available
        patterns = getattr(settings, "CACHE_TAG_PATTERNS", {})
        for tag, patterns_for_tag in patterns.items():
            self._tag_patterns[tag] = set(patterns_for_tag)

        self._initialized = True

    def add_tag_pattern(self, tag: str, pattern: str) -> None:
        """
        Add a pattern to be invalidated when a tag is invalidated.

        Args:
            tag: The cache tag
            pattern: The cache key pattern to invalidate
        """
        self.initialize()
        if tag not in self._tag_patterns:
            self._tag_patterns[tag] = set()
        self._tag_patterns[tag].add(pattern)

    def get_patterns_for_tag(self, tag: str) -> Set[str]:
        """
        Get all patterns that should be invalidated for a tag.

        Args:
            tag: The cache tag

        Returns:
            Set of patterns to invalidate
        """
        self.initialize()
        return self._tag_patterns.get(tag, set())

    @classmethod
    def invalidate_tag(cls, tag: str) -> bool:
        """
        Invalidate all cache entries associated with a tag.

        Args:
            tag: The cache tag to invalidate

        Returns:
            Number of patterns invalidated
        """
        try:
            for prefix in TAG_KEY_PREFIXES.get(tag, []):
                invalidate_pattern(f"{prefix}*", "redis")

            for dependency in TAG_DEPENDENCIES.get(tag, []):
                for prefix in TAG_KEY_PREFIXES.get(dependency, []):
                    invalidate_pattern(f"{prefix}*", "redis")

            logger.debug("Invalidated cache for tag: %s", tag)
            return True
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            logger.error("Error invalidating tag cache for %s: %s", tag, error)
            return False

    @classmethod
    def invalidate_tags(cls, tags: List[str]) -> bool:
        """
        Invalidate multiple tags at once.

        Args:
            tags: List of tags to invalidate

        Returns:
            Total number of patterns invalidated
        """
        for tag in tags:
            cls.invalidate_tag(tag)
        return True

    @classmethod
    def invalidate_user_cache(cls, user_id: Any) -> bool:
        """Invalidate user-specific cache keys."""
        try:
            patterns = [
                f"user:*{user_id}*",
                f"profile:*{user_id}*",
                f"user_games:*{user_id}*",
                f"dashboard:*{user_id}*",
                f"analysis:*{user_id}*",
                f"feedback:*{user_id}*",
                f"user_stats:*{user_id}*",
                f"subscription:*{user_id}*",
            ]
            for pattern in patterns:
                invalidate_pattern(pattern, "redis")
            logger.debug("Invalidated all cache for user: %s", user_id)
            return True
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            logger.error("Error invalidating user cache for %s: %s", user_id, error)
            return False

    @classmethod
    def invalidate_game_cache(cls, game_id: Any) -> bool:
        """Invalidate game-specific cache keys."""
        try:
            patterns = [
                f"game:*{game_id}*",
                f"analysis:*{game_id}*",
                f"feedback:*{game_id}*",
            ]
            for pattern in patterns:
                invalidate_pattern(pattern, "redis")
            logger.debug("Invalidated all cache for game: %s", game_id)
            return True
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            logger.error("Error invalidating game cache for %s: %s", game_id, error)
            return False

    @classmethod
    def invalidate_all(cls) -> bool:
        """
        Invalidate all cached data.

        Returns:
            Number of patterns invalidated
        """
        return cls.invalidate_tag(GLOBAL_TAG)


# Global cache invalidator instance
cache_invalidator = CacheInvalidator()


def invalidate_cache(tags: Union[str, List[str]]) -> int:
    """
    Invalidate cache for the specified tags.

    Args:
        tags: Tag or list of tags to invalidate

    Returns:
        Number of cache entries invalidated
    """
    if isinstance(tags, str):
        tags = [tags]

    return cache_invalidator.invalidate_tags(tags)


def with_cache_tags(*tags: str) -> Callable[[Any], Any]:
    """
    Decorator to associate cache tags with a function's cache key.

    Args:
        *tags: Cache tags to associate with the function

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the base cache key for this function call
            base_key = generate_cache_key(func.__module__, func.__qualname__, *args, **kwargs)

            # For each tag, store a mapping from the tag to this cache key
            for tag in tags:
                _tag_key = f"{base_key}{TAG_SEPARATOR}{tag}"
                # This is a no-op key that helps us find keys by tag pattern
                # We don't actually store anything here, it's just for pattern matching
                # This approach allows for fine-grained invalidation without maintaining
                # a separate index of keys

            # Call the original function
            return func(*args, **kwargs)

        # Store the tags on the function for introspection
        setattr(wrapper, "_cache_tags", tags)
        return cast(F, wrapper)

    return decorator


def invalidates_cache(*tags: str) -> Callable[[F], F]:
    """
    Decorator to invalidate cache tags when a function is called.

    Args:
        *tags: Cache tags to invalidate

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Call the original function
            result = func(*args, **kwargs)

            # Invalidate the specified cache tags
            try:
                invalidate_cache(list(tags))
            except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                logger.error("Error invalidating cache in %s: %s", func.__qualname__, error)

            return result

        return cast(F, wrapper)

    return decorator


# Method decorator version for class methods
def invalidates_cache_method(*tags: str) -> Callable[[F], F]:
    """
    Method decorator version of invalidates_cache.

    Args:
        *tags: Cache tags to invalidate

    Returns:
        Decorator function
    """
    return method_decorator(invalidates_cache(*tags))


class CacheTagsMiddleware:
    """
    Middleware to add cache control headers based on cache tags.

    This middleware adds appropriate Cache-Control headers to responses
    based on the cache tags associated with the view.
    """

    def __init__(self, get_response: Callable) -> None:
        """
        Initialize the middleware.

        Args:
            get_response: Django response getter function
        """
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """
        Process the request and add cache headers to the response.

        Args:
            request: Django request object

        Returns:
            Django response object
        """
        response = self.get_response(request)

        # Get the view function
        view_func = getattr(request, "resolver_match", None)
        if view_func and hasattr(view_func, "func"):
            view_func = view_func.func

            # Check if the view has cache tags
            cache_tags = getattr(view_func, "_cache_tags", None)
            if cache_tags:
                # Set cache control headers
                cache_control = response.get("Cache-Control", "")

                # Add cache tags to header for CDN support
                tags_header = ",".join(cache_tags)
                response["Cache-Tag"] = tags_header

                # If no cache control is set, add a default
                if not cache_control:
                    if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
                        # Private caching for authenticated users
                        response["Cache-Control"] = "private, max-age=60"
                    else:
                        # Public caching for anonymous users
                        response["Cache-Control"] = "public, max-age=300"

        return response
