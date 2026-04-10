"""
Cache invalidation utilities for efficient cache management.

This module provides a framework for intelligent cache invalidation
using cache tags and pattern-based invalidation. It allows for fine-grained
cache control and automatic cache invalidation when data changes.
"""

import functools
import logging
import sys
from typing import Any, Callable, Dict, List, Set, TypeVar, Union, cast

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.decorators import method_decorator

from .cache import generate_cache_key, get_redis_connection, invalidate_pattern

logger = logging.getLogger(__name__)

# Keep legacy import aliases pointed at the same module so monkeypatches work
# no matter which package spelling the test runner imports first.
sys.modules.setdefault("core.cache_invalidation", sys.modules[__name__])
sys.modules.setdefault("chess_mate.core.cache_invalidation", sys.modules[__name__])
sys.modules.setdefault("chessmate_prod.chess_mate.core.cache_invalidation", sys.modules[__name__])

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

            logger.debug(f"Invalidated cache for {entity_type}:{entity_id}")
            return True
        except Exception as error:
            logger.error(f"Error invalidating entity cache for {entity_type}:{entity_id}: {error}")
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
            # Legacy tag invalidation uses explicit tag-marker keys.
            if tag == GLOBAL_TAG:
                invalidate_pattern(f"*{TAG_SEPARATOR}*", "redis")
                logger.debug(f"Invalidated cache for tag: {tag}")
                return True

            invalidate_pattern(f"*{TAG_SEPARATOR}{tag}", "redis")
            for prefix in TAG_KEY_PREFIXES.get(tag, []):
                invalidate_pattern(f"{prefix}*", "redis")

            for dependency in TAG_DEPENDENCIES.get(tag, []):
                for prefix in TAG_KEY_PREFIXES.get(dependency, []):
                    invalidate_pattern(f"{prefix}*", "redis")

            logger.debug(f"Invalidated cache for tag: {tag}")
            return True
        except Exception as error:
            logger.error(f"Error invalidating tag cache for {tag}: {error}")
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
            logger.debug(f"Invalidated all cache for user: {user_id}")
            return True
        except Exception as error:
            logger.error(f"Error invalidating user cache for {user_id}: {error}")
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
            logger.debug(f"Invalidated all cache for game: {game_id}")
            return True
        except Exception as error:
            logger.error(f"Error invalidating game cache for {game_id}: {error}")
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
        existing_tags = getattr(func, "_cache_tags", set())
        if not isinstance(existing_tags, set):
            existing_tags = set(existing_tags)
        combined_tags = existing_tags.union(set(tags))

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Keep key generation stable for legacy tests and helper utilities.
            base_key = generate_cache_key(func.__name__, *args, **kwargs)
            result = func(*args, **kwargs)

            redis_client = get_redis_connection()
            if redis_client:
                if redis_client.get(base_key) is None:
                    redis_client.set(base_key, "1")
                    for tag in combined_tags:
                        redis_client.set(f"{base_key}{TAG_SEPARATOR}{tag}", "1")

            return result

        # Store the tags on the function for introspection
        setattr(wrapper, "_cache_tags", combined_tags)
        return cast(F, wrapper)

    return decorator


def invalidates_cache(*tags: str, entities: Union[Dict[str, str], None] = None) -> Callable[[F], F]:
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
                for tag in tags:
                    CacheInvalidator.invalidate_tag(tag)

                if entities:
                    for entity_type, argument_name in entities.items():
                        entity_id = kwargs.get(argument_name)
                        if entity_id is None:
                            for arg in args:
                                if isinstance(arg, dict) and argument_name in arg:
                                    entity_id = arg.get(argument_name)
                                    break
                        if entity_id is not None:
                            CacheInvalidator.invalidate_entity(entity_type, entity_id)
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


@receiver(post_save)
def invalidate_cache_on_save(sender: Any, instance: Any, **kwargs: Any) -> None:
    """Legacy post-save hook used by compatibility tests."""
    model_name = sender.__name__
    if model_name not in ENTITY_KEY_PREFIXES:
        return

    entity_id = getattr(instance, "id", None)
    if entity_id is not None:
        CacheInvalidator.invalidate_entity(model_name, entity_id)


@receiver(post_delete)
def invalidate_cache_on_delete(sender: Any, instance: Any, **kwargs: Any) -> None:
    """Legacy post-delete hook used by compatibility tests."""
    invalidate_cache_on_save(sender, instance, **kwargs)
