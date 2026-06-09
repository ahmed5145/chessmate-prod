"""
Sanitize opening / middlegame / endgame half-move boundaries for batch reports (M6).
"""

from __future__ import annotations

MIN_OPENING_HALF_MOVES = 6
MIN_MIDDLEGAME_HALF_MOVES = 4
MIN_ENDGAME_HALF_MOVES = 4


def endgame_start_from_metadata(metadata: dict, total_half_moves: int) -> int:
    """
    Derive endgame start index from MetricsCalculator metadata.

    metadata.opening_length = opening end index
    metadata.middlegame_length = middlegame half-move COUNT (not end index)
    """
    opening_end = int(metadata.get("opening_length", 0) or 0)
    middlegame_count = int(metadata.get("middlegame_length", 0) or 0)
    if middlegame_count > 0 and opening_end >= 0:
        return opening_end + middlegame_count
    legacy = int(metadata.get("endgame_start", 0) or 0)
    if legacy > opening_end:
        return legacy
    return max(opening_end, int(total_half_moves * 2 / 3))


def normalize_phase_boundaries(
    total_half_moves: int,
    opening_end: int,
    endgame_start: int,
) -> tuple[int, int]:
    """
    Return (opening_end, endgame_start) with minimum phase sizes and sane ordering.
    endgame slice is [endgame_start, total); middlegame is [opening_end, endgame_start).
    """
    total = max(0, int(total_half_moves))
    if total == 0:
        return 0, 0

    if total <= 12:
        opening = min(4, max(2, total // 3))
        return opening, total

    opening = max(0, min(int(opening_end), total // 4))
    opening = max(MIN_OPENING_HALF_MOVES, opening)
    opening = min(opening, total // 3)

    endgame = max(int(endgame_start), opening + MIN_MIDDLEGAME_HALF_MOVES)
    endgame = min(endgame, total - MIN_ENDGAME_HALF_MOVES)

    if endgame <= opening:
        endgame = min(
            total, opening + max(MIN_MIDDLEGAME_HALF_MOVES, (total - opening) // 2)
        )

    if total - endgame < MIN_ENDGAME_HALF_MOVES:
        endgame = total

    return opening, endgame


def phase_for_half_move_index(
    index: int,
    opening_end: int,
    endgame_start: int,
) -> str:
    if index < opening_end:
        return "opening"
    if index < endgame_start:
        return "middlegame"
    return "endgame"
