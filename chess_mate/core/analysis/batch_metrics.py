"""
Batch-level metric helpers (ACPL, eval stability).
"""

from __future__ import annotations

from typing import Any, Dict, List

from .batch_move_classification import player_eval_deterioration


def move_centipawn_loss(move: Dict[str, Any]) -> float:
    """Centipawn loss for one half-move from the moving player's perspective."""
    if move.get("centipawn_loss") is not None:
        try:
            return max(0.0, float(move["centipawn_loss"]))
        except (TypeError, ValueError):
            pass

    before = float(move.get("eval_before", move.get("position_score", 0.0)))
    after = float(move.get("eval_after", before))
    is_white = bool(move.get("is_white", True))
    deterioration_pawns = player_eval_deterioration(is_white, before, after)
    return deterioration_pawns * 100.0


def compute_game_acpl(analyzed_moves: List[Dict[str, Any]]) -> float:
    if not analyzed_moves:
        return 0.0
    losses = [move_centipawn_loss(mv) for mv in analyzed_moves]
    return round(sum(losses) / len(losses), 1)


def compute_batch_acpl(per_game_results: List[Dict[str, Any]]) -> float:
    """Mean ACPL across games (each game's ACPL weighted by total_moves)."""
    weighted_sum = 0.0
    weight = 0
    for result in per_game_results:
        acpl = result.get("acpl")
        if acpl is None:
            continue
        moves = int(result.get("total_moves", 0) or 0) or 1
        weighted_sum += float(acpl) * moves
        weight += moves

    if weight == 0:
        return 0.0
    return round(weighted_sum / weight, 1)
