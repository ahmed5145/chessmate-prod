"""
Batch-level metric helpers (ACPL, Chess.com-style accuracy, eval stability).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .batch_move_classification import player_eval_deterioration

# Chess.com-style per-move accuracy from centipawn loss (community-fitted curve).
_ACCURACY_A = 103.1668
_ACCURACY_B = 0.04354
_ACCURACY_C = 3.1669


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


def move_accuracy_percent(cp_loss: float) -> float:
    """Map centipawn loss to 0–100 accuracy (Chess.com-style)."""
    cp = max(0.0, float(cp_loss))
    raw = _ACCURACY_A * math.exp(-_ACCURACY_B * cp) - _ACCURACY_C
    return max(0.0, min(100.0, raw))


def _filter_player_moves(
    analyzed_moves: List[Dict[str, Any]],
    player_color: str,
) -> List[Dict[str, Any]]:
    is_white_player = player_color == "white"
    return [mv for mv in analyzed_moves if bool(mv.get("is_white", True)) == is_white_player]


def compute_game_accuracy(
    analyzed_moves: List[Dict[str, Any]],
    player_color: str = "white",
) -> float:
    """Mean Chess.com-style accuracy % for the player's moves only."""
    player_moves = _filter_player_moves(analyzed_moves, player_color)
    if not player_moves:
        return 0.0
    scores = [move_accuracy_percent(move_centipawn_loss(mv)) for mv in player_moves]
    return round(sum(scores) / len(scores), 1)


def compute_phase_accuracy(
    analyzed_moves: List[Dict[str, Any]],
    start: int,
    end: int,
    player_color: str,
) -> Optional[float]:
    """Accuracy % for the player's moves within a half-move index slice."""
    if end <= start:
        return None
    player_moves = _filter_player_moves(analyzed_moves[start:end], player_color)
    if not player_moves:
        return None
    scores = [move_accuracy_percent(move_centipawn_loss(mv)) for mv in player_moves]
    return round(sum(scores) / len(scores), 1)


def compute_batch_accuracy(per_game_results: List[Dict[str, Any]]) -> float:
    """Weighted mean game accuracy (by player move count)."""
    weighted_sum = 0.0
    weight = 0
    for result in per_game_results:
        accuracy = result.get("accuracy")
        if accuracy is None:
            continue
        moves = int(result.get("player_moves", 0) or 0) or 1
        weighted_sum += float(accuracy) * moves
        weight += moves

    if weight == 0:
        return 0.0
    return round(weighted_sum / weight, 1)


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
