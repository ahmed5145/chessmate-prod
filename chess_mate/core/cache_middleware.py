"""Middleware for automatic cache invalidation."""

# pylint: disable=no-member

import logging
from typing import Any, Dict, List, Type

from django.apps import apps
from django.db.models import Model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .redis_config import (
    KEY_PREFIX_USER,
    invalidate_analysis_cache,
    invalidate_game_cache,
    invalidate_player_cache,
    invalidate_user_games_cache,
    redis_invalidate_by_prefix,
    redis_invalidate_by_tags,
)

# Configure logging
logger = logging.getLogger(__name__)
CACHE_INVALIDATION_EXCEPTIONS = (LookupError, AttributeError, TypeError, ValueError, RuntimeError)


def invalidate_user_prefix(user_id: int) -> None:
    redis_invalidate_by_prefix(f"{KEY_PREFIX_USER}{user_id}")


def invalidate_game_for_instance(instance: Any) -> None:
    game_id = getattr(instance, "id", None)
    if game_id is not None:
        invalidate_game_cache(game_id)


def invalidate_analysis_for_instance(instance: Any) -> None:
    analysis_id = getattr(instance, "id", None)
    if analysis_id is not None:
        invalidate_analysis_cache(analysis_id)


def invalidate_user_games_for_user(user: Any) -> None:
    invalidate_user_games_cache(user.id)


def invalidate_game_for_id(game_id: int) -> None:
    invalidate_game_cache(game_id)


def invalidate_user_games_for_id(user_id: int) -> None:
    invalidate_user_games_cache(user_id)


# Model to cache mapping
MODEL_CACHE_MAPPING: Dict[str, Dict[str, Any]] = {
    "Game": {
        "tags": ["games"],
        "fields": ["id", "status", "result"],
        "invalidate_functions": [
            invalidate_game_for_instance,
        ],
        "related_invalidations": [
            {"field": "user", "func": invalidate_user_games_for_user}
        ],
    },
    "Player": {
        "tags": ["players", "games"],
        "invalidate_functions": [],
        "related_invalidations": [
            {"field": "game_id", "func": invalidate_game_for_id},
            {"field": "user_id", "func": invalidate_user_games_for_id},
        ],
    },
    "GameAnalysis": {
        "tags": ["analysis"],
        "invalidate_functions": [
            invalidate_analysis_for_instance,
        ],
        "related_invalidations": [{"field": "game_id", "func": invalidate_game_for_id}],
    },
    "Profile": {
        "tags": ["profiles", "users"],
        "invalidate_functions": [],
        "related_invalidations": [
            {"field": "user_id", "func": invalidate_user_prefix}
        ],
    },
}


def get_related_values(instance: Any, field_path: str) -> List[Any]:
    """
    Get values from a related field path.

    Args:
        instance: Model instance
        field_path: Dot-separated field path (e.g., 'players__user_id')

    Returns:
        List of values
    """
    if "__" not in field_path:
        return [getattr(instance, field_path)]

    # Split the field path
    parts = field_path.split("__")
    current_field = parts[0]
    remaining_path = "__".join(parts[1:])

    # Handle different relationship types
    current_value = getattr(instance, current_field)

    if current_value is None:
        return []

    # Handle many-to-many relationships
    if hasattr(current_value, "all"):
        related_objects = current_value.all()
        result = []
        for obj in related_objects:
            result.extend(get_related_values(obj, remaining_path))
        return result

    # Handle foreign key relationships
    return get_related_values(current_value, remaining_path)


@receiver(post_save)
def invalidate_cache_on_save(sender: Type[Model], instance: Any, **kwargs) -> None:
    """
    Signal handler to invalidate cache when a model is saved.

    Args:
        sender: Model class
        instance: Model instance
    """
    _ = kwargs
    model_name = sender.__name__

    # Skip if model not in mapping
    if model_name not in MODEL_CACHE_MAPPING:
        return

    mapping: Dict[str, Any] = MODEL_CACHE_MAPPING[model_name]
    instance_id = getattr(instance, "id", None)

    # Log invalidation
    logger.debug("Invalidating cache for %s %s", model_name, instance_id)

    # Invalidate by tags
    if mapping.get("tags"):
        tags = mapping["tags"]
        if isinstance(tags, list):
            redis_invalidate_by_tags(tags)
        elif isinstance(tags, str):
            redis_invalidate_by_tags(tags)

    # Run model-specific invalidation functions
    invalidate_functions = mapping.get("invalidate_functions", [])
    for func in invalidate_functions:
        try:
            func(instance)
        except CACHE_INVALIDATION_EXCEPTIONS as e:
            logger.error("Error in cache invalidation function: %s", e)

    # Run related invalidations
    related_invalidations = mapping.get("related_invalidations", [])
    for related in related_invalidations:
        field_path = related["field"]
        invalidate_func = related["func"]

        try:
            related_values = get_related_values(instance, field_path)
            for value in related_values:
                if value is not None:
                    invalidate_func(value)
        except CACHE_INVALIDATION_EXCEPTIONS as e:
            logger.error("Error in related cache invalidation: %s", e)


@receiver(post_delete)
def invalidate_cache_on_delete(sender: Type[Model], instance: Any, **kwargs) -> None:
    """
    Signal handler to invalidate cache when a model is deleted.

    Args:
        sender: Model class
        instance: Model instance
    """
    _ = kwargs
    # Reuse the same logic as post_save
    invalidate_cache_on_save(sender, instance, **kwargs)


def setup_cache_invalidation():
    """
    Set up cache invalidation signals for all relevant models.
    Call this function in the AppConfig.ready() method.
    """
    # Get the models
    for model_name in MODEL_CACHE_MAPPING.keys():
        try:
            # Find the model
            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = app_config.get_model(model_name)
                    break
                except LookupError:
                    continue

            if model:
                logger.info("Registered cache invalidation for %s", model_name)
            else:
                logger.warning("Could not find model %s", model_name)

        except CACHE_INVALIDATION_EXCEPTIONS as e:
            logger.error("Error setting up cache invalidation for %s: %s", model_name, e)


def invalidate_player_cache_for_game(game_id):
    """Invalidate player cache for all players in a game."""
    try:
        # Import here to avoid circular imports
        from .models import Game
        game = Game.objects.get(id=game_id)
        # Get all players through the game's players relationship
        players_relation = getattr(game, "players", None)
        if players_relation is None:
            return
        for player in players_relation.all():
            if player.user_id:
                invalidate_user_games_cache(player.user_id)
                invalidate_player_cache(player.id)
    except CACHE_INVALIDATION_EXCEPTIONS as e:
        logger.error("Error invalidating player cache for game %s: %s", game_id, e)


class CacheInvalidationMiddleware:
    """
    Middleware to handle cache invalidation.
    This is mainly for future extensions - most invalidation happens via signals.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
