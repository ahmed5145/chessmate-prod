"""Blunder-free streak across consecutive depth-20 single-game reviews."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.utils import timezone

STREAK_SWING_THRESHOLD = 1.0
PREFERENCES_KEY = "single_game_streak"


def get_single_game_streak(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Read streak state from profile preferences."""
    prefs = preferences if isinstance(preferences, dict) else {}
    raw = prefs.get(PREFERENCES_KEY)
    if not isinstance(raw, dict):
        return {"count": 0, "last_game_id": None, "updated_at": None}

    count = int(raw.get("count") or 0)
    if count < 0:
        count = 0
    return {
        "count": count,
        "last_game_id": raw.get("last_game_id"),
        "updated_at": raw.get("updated_at"),
    }


def _is_player_move(move: Dict[str, Any], player_color: str) -> bool:
    is_white = move.get("is_white")
    if is_white is None:
        is_white = move.get("isWhite")
    if is_white is None:
        return False
    return bool(is_white) == (player_color == "white")


def _eval_loss_pawns(move: Dict[str, Any]) -> float:
    raw = move.get("eval_change")
    if raw is None:
        raw = move.get("evaluation_change")
    if raw is None:
        raw = move.get("delta")
    try:
        change = float(raw)
    except (TypeError, ValueError):
        return 0.0

    if abs(change) > 20:
        change = change / 100.0

    return abs(change) if change < 0 else 0.0


def _normalize_classification(move: Dict[str, Any]) -> str:
    value = str(move.get("classification") or move.get("type") or "").lower()
    return value.replace(" ", "_").strip()


def _is_missed_win(move: Dict[str, Any], player_color: str, loss: float) -> bool:
    if loss < STREAK_SWING_THRESHOLD:
        return False
    eval_before = move.get("eval_before")
    if eval_before is None:
        return False
    try:
        white_eval = float(eval_before)
    except (TypeError, ValueError):
        return False
    player_eval = white_eval if player_color == "white" else -white_eval
    return player_eval >= 2.0


def move_breaks_streak(move: Dict[str, Any], player_color: str) -> bool:
    """True when a player move is a 1+ pawn blunder or missed win."""
    if not _is_player_move(move, player_color):
        return False

    loss = _eval_loss_pawns(move)
    if loss < STREAK_SWING_THRESHOLD:
        return False

    classification = _normalize_classification(move)
    if classification in {"blunder", "missed_win"}:
        return True
    if loss >= 1.5:
        return True
    if _is_missed_win(move, player_color, loss):
        return True
    return False


def game_breaks_streak(analysis_data: Any, player_color: str) -> bool:
    """Scan stored analysis moves for a streak-breaking swing."""
    if not isinstance(analysis_data, dict):
        return False
    moves = analysis_data.get("moves") or []
    if not isinstance(moves, list):
        return False
    return any(
        isinstance(move, dict) and move_breaks_streak(move, player_color)
        for move in moves
    )


def update_single_game_streak(
    profile,
    *,
    game_id: int,
    analysis_data: Any,
    player_color: str,
) -> Dict[str, Any]:
    """
    Update profile preferences streak after a successful depth-20 analysis.
    Returns the new streak payload.
    """
    breaks = game_breaks_streak(analysis_data, player_color)
    prefs = profile.preferences if isinstance(profile.preferences, dict) else {}
    state = get_single_game_streak(prefs)
    last_game_id = state.get("last_game_id")
    count = int(state.get("count") or 0)

    if breaks:
        count = 0
    elif last_game_id != game_id:
        count += 1

    new_state = {
        "count": count,
        "last_game_id": game_id,
        "updated_at": timezone.now().isoformat(),
    }
    prefs = dict(prefs)
    prefs[PREFERENCES_KEY] = new_state
    profile.preferences = prefs
    profile.save(update_fields=["preferences"])
    return new_state
