"""Structured logging for single-game analysis tasks (timing, timeouts)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def is_celery_time_limit_error(exc: BaseException) -> bool:
    """Return True when Celery killed the task for exceeding soft/hard time limits."""
    name = type(exc).__name__
    if name in ("SoftTimeLimitExceeded", "TimeLimitExceeded"):
        return True
    try:
        from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded

        return isinstance(exc, (SoftTimeLimitExceeded, TimeLimitExceeded))
    except Exception:
        return False


class SingleGameAnalysisTimer:
    """Wall-clock timer for single-game analysis phases (searchable in EB stdouterr)."""

    def __init__(
        self,
        *,
        task_id: Optional[str],
        game_id: int,
        depth: int,
        move_count: Optional[int] = None,
    ) -> None:
        self.task_id = task_id
        self.game_id = game_id
        self.depth = depth
        self.move_count = move_count
        self._started = time.monotonic()
        self._phase_started = self._started
        self.phases: Dict[str, float] = {}

    def mark(self, phase: str, **extra: Any) -> None:
        now = time.monotonic()
        phase_seconds = now - self._phase_started
        total_seconds = now - self._started
        self.phases[phase] = round(phase_seconds, 2)
        payload = " ".join(
            f"{key}={value}" for key, value in extra.items() if value is not None
        )
        logger.info(
            "single_game_analysis phase=%s task_id=%s game_id=%s depth=%s plies=%s "
            "phase_seconds=%.2f total_seconds=%.2f%s%s",
            phase,
            self.task_id,
            self.game_id,
            self.depth,
            self.move_count,
            phase_seconds,
            total_seconds,
            " " if payload else "",
            payload,
        )
        self._phase_started = now

    def complete(self, **extra: Any) -> None:
        total_seconds = time.monotonic() - self._started
        payload = " ".join(
            f"{key}={value}" for key, value in extra.items() if value is not None
        )
        logger.info(
            "single_game_analysis COMPLETE task_id=%s game_id=%s depth=%s plies=%s "
            "total_seconds=%.2f phases=%s%s%s",
            self.task_id,
            self.game_id,
            self.depth,
            self.move_count,
            total_seconds,
            self.phases,
            " " if payload else "",
            payload,
        )

    def fail(self, exc: BaseException, **extra: Any) -> None:
        total_seconds = time.monotonic() - self._started
        timeout = is_celery_time_limit_error(exc)
        payload = " ".join(
            f"{key}={value}" for key, value in extra.items() if value is not None
        )
        logger.error(
            "single_game_analysis FAILED task_id=%s game_id=%s depth=%s plies=%s "
            "total_seconds=%.2f timeout=%s error_type=%s error=%s phases=%s%s%s",
            self.task_id,
            self.game_id,
            self.depth,
            self.move_count,
            total_seconds,
            timeout,
            type(exc).__name__,
            exc,
            self.phases,
            " " if payload else "",
            payload,
        )


def count_plies_in_pgn(pgn: Optional[str]) -> int:
    """Count half-moves in a PGN mainline (for ETA / timeout diagnostics)."""
    if not pgn or not str(pgn).strip():
        return 0
    try:
        import io

        import chess.pgn

        game = chess.pgn.read_game(io.StringIO(str(pgn)))
        if not game:
            return 0
        return len(list(game.mainline_moves()))
    except Exception:
        return 0
