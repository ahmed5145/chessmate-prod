"""
Move classification thresholds for the batch coach pipeline (Stockfish path).

All evaluation values are in **pawns from White's perspective** (matches StockfishAnalyzer).
These thresholds are the single source of truth for batch reports (contract §4, M2).
"""

from __future__ import annotations

# Deterioration magnitude (pawns lost for the player who moved)
INACCURACY_PAWNS = 0.2
MISTAKE_PAWNS = 0.5
BLUNDER_PAWNS = 1.5

# Minimum deterioration to include in critical_moments shortlist
CRITICAL_MOMENT_MIN_PAWNS = 0.2


def player_eval_deterioration(is_white: bool, eval_before: float, eval_after: float) -> float:
    """
    How much the moving side worsened their position (non-negative pawns).

    eval_before / eval_after are always White POV.
    """
    try:
        before = float(eval_before)
        after = float(eval_after)
    except (TypeError, ValueError):
        return 0.0

    if is_white:
        return max(0.0, before - after)
    return max(0.0, after - before)


def classify_deterioration(deterioration: float) -> str:
    """Map deterioration (pawns) to move_quality label."""
    d = max(0.0, float(deterioration))
    if d >= BLUNDER_PAWNS:
        return "blunder"
    if d >= MISTAKE_PAWNS:
        return "mistake"
    if d >= INACCURACY_PAWNS:
        return "inaccuracy"
    return "good"
