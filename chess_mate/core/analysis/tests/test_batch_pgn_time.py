import pytest

from core.analysis.batch_pgn_time import compute_time_management_from_pgn

PGN_WITH_CLOCKS = """
[Event "ClockTest"]
[White "Player"]
[Black "Opponent"]
[Result "*"]

1. e4 {[%clk 0:10:00]} 1... e5 {[%clk 0:10:00]} 2. Nf3 {[%clk 0:09:50]} 2... Nc6 {[%clk 0:09:55]}
3. Bb5 {[%clk 0:09:48]} 3... a6 {[%clk 0:09:50]} *
"""

PGN_NO_CLOCKS = """
[Event "NoClock"]
[White "A"]
[Black "B"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
"""


def test_compute_time_management_detects_clock_data():
    result = compute_time_management_from_pgn(
        PGN_WITH_CLOCKS,
        player_color="white",
        opening_end=6,
        endgame_start=6,
        critical_move_numbers=[3],
    )
    assert result["has_clock_data"] is True
    assert result["moves_timed"] >= 2
    assert result["avg_seconds_per_move"] > 0
    assert result["rushed_critical_count"] >= 1
    assert result["pattern"] == "rushed_critical_moments"


def test_compute_time_management_without_clocks():
    result = compute_time_management_from_pgn(
        PGN_NO_CLOCKS,
        player_color="white",
        opening_end=2,
        endgame_start=4,
    )
    assert result["has_clock_data"] is False
