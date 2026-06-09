"""Celery time limits for single-game analysis tasks."""

from core.tasks import analyze_game_task
from django.test import override_settings


@override_settings(
    SINGLE_GAME_TASK_SOFT_TIME_LIMIT=840, SINGLE_GAME_TASK_TIME_LIMIT=900
)
def test_analyze_game_task_has_extended_time_limits():
    # Decorator reads settings at import; values below match production defaults.
    assert analyze_game_task.time_limit == 900
    assert analyze_game_task.soft_time_limit == 840
