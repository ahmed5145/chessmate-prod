"""
Re-queue Stockfish batch analysis for completed reports (admin / ops).

Used after classification or aggregation fixes so old batches pick up new logic
without charging credits again.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .models import BatchAnalysisReport, Game

logger = logging.getLogger(__name__)


class BatchRerunError(Exception):
    """Raised when a batch cannot be re-queued."""


def _normalize_game_ids(raw_ids: Any) -> List[Optional[int]]:
    if not raw_ids:
        return []
    if not isinstance(raw_ids, list):
        return []
    out: List[Optional[int]] = []
    for item in raw_ids:
        if item is None:
            out.append(None)
            continue
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def resolve_batch_game_ids(batch_report: BatchAnalysisReport) -> List[int]:
    """Collect saved Game PKs from batch metadata and per-game results."""
    seen = set()
    ordered: List[int] = []

    for gid in _normalize_game_ids(batch_report.game_ids):
        if gid is not None and gid not in seen:
            seen.add(gid)
            ordered.append(gid)

    for entry in batch_report.per_game_results or []:
        if not isinstance(entry, dict):
            continue
        saved_id = entry.get("saved_game_id")
        if saved_id is None:
            continue
        try:
            saved_id = int(saved_id)
        except (TypeError, ValueError):
            continue
        if saved_id not in seen:
            seen.add(saved_id)
            ordered.append(saved_id)

    return ordered


def collect_batch_pgns(batch_report: BatchAnalysisReport) -> Tuple[List[str], List[int]]:
    """Load PGN strings for a batch's saved games (same user)."""
    game_ids = resolve_batch_game_ids(batch_report)
    if not game_ids:
        raise BatchRerunError("No saved game IDs found on this batch report.")

    pgns: List[str] = []
    source_ids: List[int] = []
    missing: List[int] = []

    for game_id in game_ids:
        try:
            game = Game.objects.get(pk=game_id, user_id=batch_report.user_id)
        except Game.DoesNotExist:
            missing.append(game_id)
            continue
        pgn = (game.pgn or "").strip()
        if not pgn:
            missing.append(game_id)
            continue
        pgns.append(pgn)
        source_ids.append(game.id)

    if missing:
        logger.warning(
            "Batch %s rerun: skipped %s game(s) without PGN: %s",
            batch_report.id,
            len(missing),
            missing[:10],
        )

    if len(pgns) < 5:
        raise BatchRerunError(f"Need at least 5 games with PGN to rerun (found {len(pgns)}).")

    return pgns, source_ids


def prepare_batch_rerun(batch_report: BatchAnalysisReport) -> None:
    """Reset persisted analysis so the chord callback can overwrite it."""
    batch_report.status = "in_progress"
    batch_report.batch_summary = None
    batch_report.coaching_report = None
    batch_report.per_game_results = None
    batch_report.completed_games = []
    batch_report.failed_games = []
    batch_report.aggregate_metrics = {}
    batch_report.save(
        update_fields=[
            "status",
            "batch_summary",
            "coaching_report",
            "per_game_results",
            "completed_games",
            "failed_games",
            "aggregate_metrics",
            "updated_at",
        ]
    )


def queue_batch_rerun(batch_report: BatchAnalysisReport, *, eager: bool = False) -> str:
    """
    Re-analyze a batch with current Stockfish + aggregation logic.

    Returns a status message. Does not charge credits.
    """
    if batch_report.status not in ("completed", "partial", "failed"):
        raise BatchRerunError(
            f"Batch {batch_report.id} is {batch_report.status}; " "wait for it to finish or cancel it first."
        )

    pgns, source_ids = collect_batch_pgns(batch_report)
    prepare_batch_rerun(batch_report)
    batch_report.games_count = len(pgns)
    batch_report.game_ids = source_ids
    batch_report.save(update_fields=["games_count", "game_ids", "updated_at"])

    task_id = batch_report.task_id
    user_id = batch_report.user_id

    if eager:
        from .tasks import aggregate_and_report_task, analyze_single_game_subtask

        results: List[Dict[str, Any]] = []
        for i, pgn in enumerate(pgns):
            saved_id = source_ids[i] if i < len(source_ids) else None
            try:
                results.append(analyze_single_game_subtask(pgn, f"game_{i}", task_id, user_id, saved_id))
            except Exception as exc:
                logger.exception("Batch %s eager rerun game %s failed: %s", batch_report.id, i, exc)
                results.append({"game_id": f"game_{i}", "status": "failed", "error": str(exc)})
        aggregate_and_report_task(results, task_id, pgns, user_id)
        return f"Re-analyzed batch {batch_report.id} inline ({len(pgns)} games)."

    from .tasks import analyze_batch_task

    analyze_batch_task.delay(task_id, pgns, user_id, source_ids)
    return f"Queued re-analysis for batch {batch_report.id} ({len(pgns)} games)."
