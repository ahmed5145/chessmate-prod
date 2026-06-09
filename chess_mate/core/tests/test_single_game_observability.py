"""Tests for single-game analysis observability helpers."""

from unittest.mock import MagicMock

from celery.exceptions import SoftTimeLimitExceeded
from core.single_game_observability import (
    SingleGameAnalysisTimer,
    count_plies_in_pgn,
    is_celery_time_limit_error,
)


def test_is_celery_time_limit_error():
    assert is_celery_time_limit_error(SoftTimeLimitExceeded()) is True
    assert is_celery_time_limit_error(RuntimeError("boom")) is False


def test_count_plies_in_pgn():
    pgn = '[Event "Test"]\n\n' "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *\n"
    assert count_plies_in_pgn(pgn) == 6


def test_timer_mark_and_complete():
    timer = SingleGameAnalysisTimer(
        task_id="task-1", game_id=168, depth=20, move_count=73
    )
    timer.mark("stockfish_start")
    timer.complete(analysis_id=99)
    assert "stockfish_start" in timer.phases


def test_timer_fail_marks_timeout():
    timer = SingleGameAnalysisTimer(
        task_id="task-2", game_id=42, depth=20, move_count=40
    )
    timer.fail(SoftTimeLimitExceeded(), progress=46)
    assert timer.phases == {}
