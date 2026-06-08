"""Extract structured critical moments from single-game Stockfish move analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _eval_swing_pawns(eval_change: Any) -> float:
    raw = _safe_float(eval_change, 0.0)
    if raw > 0:
        return 0.0
    swing = abs(raw)
    if swing > 20:
        swing = swing / 100.0
    return swing


def _moment_type(classification: str, swing: float) -> str:
    lowered = str(classification or "").lower().replace("_", " ")
    if lowered in {"blunder", "mistake", "inaccuracy"}:
        return lowered
    if swing >= 1.5:
        return "blunder"
    if swing >= 0.5:
        return "mistake"
    if swing >= 0.2:
        return "inaccuracy"
    return "moment"


def extract_critical_moments(
    analyzed_moves: List[Dict[str, Any]],
    *,
    player_color: Optional[str] = None,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Return top N negative eval swings for the analyzed player."""
    if not analyzed_moves:
        return []

    candidates: List[Dict[str, Any]] = []
    for move in analyzed_moves:
        if not isinstance(move, dict):
            continue

        is_white = bool(move.get("is_white"))
        if player_color == "white" and not is_white:
            continue
        if player_color == "black" and is_white:
            continue

        swing = _eval_swing_pawns(move.get("eval_change"))
        classification = str(move.get("classification") or "")
        is_bad = swing >= 0.2 or classification.lower() in {"blunder", "mistake", "inaccuracy"}
        if not is_bad and not move.get("is_critical"):
            continue
        if swing <= 0 and classification.lower() not in {"blunder", "mistake", "inaccuracy"}:
            continue

        candidates.append(
            {
                "move_number": move.get("move_number"),
                "fen": move.get("position") or move.get("fen"),
                "played_move": move.get("san") or move.get("move"),
                "best_move": move.get("best_move_san") or move.get("best_move"),
                "played_move_uci": move.get("move"),
                "best_move_uci": move.get("best_move"),
                "eval_swing": round(swing, 2),
                "type": _moment_type(classification, swing),
                "classification": classification,
                "player_color": "white" if is_white else "black",
            }
        )

    candidates.sort(key=lambda item: _safe_float(item.get("eval_swing")), reverse=True)
    return candidates[: max(1, int(limit))]
