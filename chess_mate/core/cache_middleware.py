"""Middleware for automatic cache invalidation."""

import logging
from typing import Any, Dict, List, Optional, Type

from django.apps import apps
from django.db.models import Model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .redis_config import (
    KEY_PREFIX_ANALYSIS,
    KEY_PREFIX_GAME,
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

# Model to cache mapping
MODEL_CACHE_MAPPING = {
    "Game": {
        "fields": ["id", "status", "result"],
        "invalidate_functions": [
            lambda instance: invalidate_game_cache(instance.id),
        ],
        "related_invalidations": [
            {"field": "user", "func": lambda user: invalidate_user_games_cache(user.id)}
        ],
    },
    "Player": {
        "tags": ["players", "games"],
        "invalidate_functions": [],
        "related_invalidations": [
            {"field": "game_id", "func": lambda game_id: invalidate_game_cache(game_id)},
            {"field": "user_id", "func": lambda user_id: invalidate_user_games_cache(user_id)},
        ],
    },
    "GameAnalysis": {
        "tags": ["analysis"],
        "invalidate_functions": [
            lambda instance: invalidate_analysis_cache(instance.id),
        ],
        "related_invalidations": [{"field": "game_id", "func": lambda game_id: invalidate_game_cache(game_id)}],
    },
    "Profile": {
        "tags": ["profiles", "users"],
        "invalidate_functions": [],
        "related_invalidations": [
            {"field": "user_id", "func": lambda user_id: redis_invalidate_by_prefix(f"{KEY_PREFIX_USER}{user_id}")}
        ],
    },
}


def get_related_values(instance: Model, field_path: str) -> List[Any]:
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
def invalidate_cache_on_save(sender: Type[Model], instance: Model, **kwargs) -> None:
    """
    Signal handler to invalidate cache when a model is saved.

    Args:
        sender: Model class
        instance: Model instance
    """
    model_name = sender.__name__

    # Skip if model not in mapping
    if model_name not in MODEL_CACHE_MAPPING:
        return

    mapping = MODEL_CACHE_MAPPING[model_name]

    # Log invalidation
    logger.debug(f"Invalidating cache for {model_name} {instance.id}")

    # Invalidate by tags
    if mapping.get("tags"):
        redis_invalidate_by_tags(mapping["tags"])

    # Run model-specific invalidation functions
    for func in mapping.get("invalidate_functions", []):
        try:
            func(instance)
        except Exception as e:
            logger.error(f"Error in cache invalidation function: {str(e)}")

    # Run related invalidations
    for related in mapping.get("related_invalidations", []):
        field_path = related["field"]
        invalidate_func = related["func"]

        try:
            related_values = get_related_values(instance, field_path)
            for value in related_values:
                if value is not None:
                    invalidate_func(value)
        except Exception as e:
            logger.error(f"Error in related cache invalidation: {str(e)}")


@receiver(post_delete)
def invalidate_cache_on_delete(sender: Type[Model], instance: Model, **kwargs) -> None:
    """
    Signal handler to invalidate cache when a model is deleted.

    Args:
        sender: Model class
        instance: Model instance
    """
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
                logger.info(f"Registered cache invalidation for {model_name}")
            else:
                logger.warning(f"Could not find model {model_name}")

        except Exception as e:
            logger.error(f"Error setting up cache invalidation for {model_name}: {str(e)}")


def invalidate_player_cache_for_game(game_id):
    """Invalidate player cache for all players in a game."""
    try:
        # Import here to avoid circular imports
        from .models import Game
        game = Game.objects.get(id=game_id)
        # Get all players through the game's players relationship
        for player in game.players.all():
            if player.user_id:
                invalidate_user_games_cache(player.user_id)
                invalidate_player_cache(player.id)
    except Exception as e:
        logger.error(f"Error invalidating player cache for game {game_id}: {str(e)}")


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
