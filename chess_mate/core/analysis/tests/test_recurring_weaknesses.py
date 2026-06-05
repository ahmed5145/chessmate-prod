"""Tests for recurring weakness filtering (M7)."""

from core.analysis.batch_aggregator import _find_recurring_weaknesses


def _game(game_id, moments):
    return {"game_id": game_id, "critical_moments": moments}


def test_generic_themes_dropped_when_specific_exists():
    games = [
        _game(
            f"g{i}",
            [
                {
                    "type": "blunder",
                    "eval_swing": 1.0,
                    "tactical_theme": "missed_tactic",
                },
                {
                    "type": "blunder",
                    "eval_swing": 1.2,
                    "tactical_theme": "fork",
                },
            ],
        )
        for i in range(5)
    ]
    recurring = _find_recurring_weaknesses(games)
    patterns = [r["pattern"] for r in recurring]
    assert "fork" in patterns
    assert "missed_tactic" not in patterns


def test_inaccuracy_moments_ignored():
    games = [
        _game(
            f"g{i}",
            [{"type": "inaccuracy", "eval_swing": 2.0, "tactical_theme": "pin"}],
        )
        for i in range(5)
    ]
    assert _find_recurring_weaknesses(games) == []
