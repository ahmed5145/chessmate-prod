"""Tests for single-game critical moment extraction."""

from core.analysis.single_game_moments import extract_critical_moments


def test_extract_critical_moments_returns_worst_swings_for_white():
    moves = [
        {
            "move_number": 5,
            "san": "e4",
            "move": "e2e4",
            "is_white": True,
            "eval_change": 0.1,
            "classification": "good",
            "position": "fen-good",
        },
        {
            "move_number": 12,
            "san": "Qh5",
            "move": "d1h5",
            "best_move": "g1f3",
            "best_move_san": "Nf3",
            "is_white": True,
            "eval_change": -2.4,
            "classification": "blunder",
            "position": "fen-blunder",
        },
        {
            "move_number": 12,
            "san": "Nf6",
            "move": "g8f6",
            "is_white": False,
            "eval_change": 2.4,
            "classification": "good",
            "position": "fen-reply",
        },
    ]

    moments = extract_critical_moments(moves, player_color="white", limit=2)
    assert len(moments) == 1
    assert moments[0]["move_number"] == 12
    assert moments[0]["played_move"] == "Qh5"
    assert moments[0]["type"] == "blunder"
    assert moments[0]["eval_swing"] == 2.4


def test_extract_critical_moments_empty_when_no_bad_moves():
    moves = [
        {"move_number": 1, "san": "d4", "is_white": True, "eval_change": 0.2, "classification": "good"},
    ]
    assert extract_critical_moments(moves, player_color="white") == []
