"""
Extract per-game time usage from PGN %clk tags (Lichess/Chess.com exports).
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

import chess.pgn

from .batch_phase_boundaries import phase_for_half_move_index


def compute_time_management_from_pgn(
    pgn: str,
    player_color: str,
    opening_end: int,
    endgame_start: int,
    critical_move_numbers: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Summarize how the user spent clock on their moves.

    Returns has_clock_data=False when PGN lacks usable clock annotations.
    """
    critical_moves = set(critical_move_numbers or [])
    player_is_white = player_color == "white"

    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except Exception:
        return {"has_clock_data": False}

    if game is None:
        return {"has_clock_data": False}

    board = game.board()
    node = game
    previous_clock = {True: None, False: None}
    player_spends: List[Dict[str, Any]] = []
    half_move_index = 0

    for move in game.mainline_moves():
        is_white = board.turn == chess.WHITE
        node = node.variation(0)
        move_clock = None
        try:
            move_clock = node.clock()
        except Exception:
            move_clock = None

        time_spent = None
        previous = previous_clock.get(is_white)
        if isinstance(previous, (int, float)) and isinstance(move_clock, (int, float)):
            delta = float(previous) - float(move_clock)
            if delta >= 0:
                time_spent = delta

        if isinstance(move_clock, (int, float)):
            previous_clock[is_white] = float(move_clock)

        if is_white == player_is_white and time_spent is not None:
            move_number = half_move_index // 2 + 1
            phase = phase_for_half_move_index(
                half_move_index, opening_end, endgame_start
            )
            player_spends.append(
                {
                    "move_number": move_number,
                    "seconds": time_spent,
                    "phase": phase,
                    "is_critical": move_number in critical_moves,
                }
            )

        board.push(move)
        half_move_index += 1

    if not player_spends:
        return {"has_clock_data": False}

    seconds = [row["seconds"] for row in player_spends]
    avg_seconds = sum(seconds) / len(seconds)
    rushed_threshold = max(3.0, avg_seconds * 0.35)
    rushed_moves = [row for row in player_spends if row["seconds"] < rushed_threshold]
    rushed_critical = [row for row in rushed_moves if row["is_critical"]]

    phase_buckets: Dict[str, List[float]] = {
        "opening": [],
        "middlegame": [],
        "endgame": [],
    }
    for row in player_spends:
        phase_buckets.setdefault(row["phase"], []).append(row["seconds"])

    def _phase_avg(phase: str) -> Optional[float]:
        values = phase_buckets.get(phase) or []
        if not values:
            return None
        return round(sum(values) / len(values), 1)

    opening_avg = _phase_avg("opening")
    endgame_avg = _phase_avg("endgame")
    pattern = None
    if rushed_critical:
        pattern = "rushed_critical_moments"
    elif opening_avg and endgame_avg and endgame_avg < opening_avg * 0.25:
        pattern = "low_endgame_time"
    elif len(rushed_moves) >= max(3, len(player_spends) // 4):
        pattern = "generally_fast"

    return {
        "has_clock_data": True,
        "moves_timed": len(player_spends),
        "avg_seconds_per_move": round(avg_seconds, 1),
        "rushed_move_count": len(rushed_moves),
        "rushed_critical_count": len(rushed_critical),
        "opening_avg_seconds": opening_avg,
        "endgame_avg_seconds": endgame_avg,
        "pattern": pattern,
    }
