"""Helpers for serving cached single-game analysis without re-running Stockfish."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import GameAnalysis


def has_complete_cached_analysis(game_id: int) -> bool:
    """True when a finished depth-20 report with moves exists for this game."""
    if not game_id:
        return False
    try:
        analysis = GameAnalysis.objects.get(game_id=game_id)
    except GameAnalysis.DoesNotExist:
        return False

    data = analysis.analysis_data if isinstance(analysis.analysis_data, dict) else {}
    if data.get("status") != "complete":
        return False
    moves = data.get("moves") or []
    return bool(moves)


def cached_analysis_response(game_id: int) -> Dict[str, Any]:
    """API payload when POST /analyze/ is skipped in favor of stored results."""
    return {
        "status": "cached",
        "message": "Using saved depth-20 report",
        "game_id": game_id,
        "credits_charged": 0,
        "cached": True,
    }
