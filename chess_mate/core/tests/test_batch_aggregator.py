"""
Test batch_aggregator with two test games from step 4.
Verifies schema completeness and field types.
"""

import pytest
from core.analysis.batch_aggregator import aggregate_batch


def _make_game_result(
    game_id: str,
    result: str,
    opening_name: str,
    opening_drop: float,
    endgame_drop: float,
    tactical_theme: str,
):
    """Create a lightweight per-game result fixture for batch aggregation tests."""
    return {
        "game_id": game_id,
        "result": result,
        "player_color": "white",
        "opening_name": opening_name,
        "analysis_failed": False,
        "phase_breakdown": {
            "opening": {
                "moves": 8,
                "avg_eval_drop": opening_drop,
                "blunders": 0,
                "mistakes": 1,
            },
            # Keep middlegame empty to validate no_data sentinel behavior
            "middlegame": {
                "moves": 0,
                "avg_eval_drop": 0.0,
                "blunders": 0,
                "mistakes": 0,
            },
            "endgame": {
                "moves": 6,
                "avg_eval_drop": endgame_drop,
                "blunders": 1,
                "mistakes": 0,
            },
        },
        "move_quality": {
            "brilliant": 0,
            "best": 1,
            "excellent": 2,
            "good": 6,
            "inaccuracy": 1,
            "mistake": 1,
            "blunder": 1,
        },
        "critical_moments": [
            {
                "phase": "endgame",
                "tactical_theme": tactical_theme,
                "eval_swing": 0.9,
            }
        ],
    }


def test_batch_aggregator_schema_structure():
    """Test that batch aggregator produces all required fields with correct types."""
    # Use lightweight fixtures instead of engine-backed analysis to keep test deterministic.
    clean_result = _make_game_result("clean-1", "1-0", "Italian Game", 0.18, 0.22, "pin")
    blunder_result = _make_game_result("blunder-1", "0-1", "Sicilian Defense", 0.38, 0.70, "fork")
    clean_result_2 = _make_game_result("clean-2", "1-0", "Italian Game", 0.12, 0.25, "pin")
    clean_result_3 = _make_game_result("clean-3", "1/2-1/2", "French Defense", 0.20, 0.28, "hanging_piece")
    blunder_result_2 = _make_game_result("blunder-2", "0-1", "Caro-Kann Defense", 0.42, 0.75, "fork")

    per_game_results = [
        clean_result,
        blunder_result,
        clean_result_2,
        clean_result_3,
        blunder_result_2,
    ]
    pgn_list = [
        '[Date "2026.05.01"]',
        '[Date "2026.05.02"]',
        '[Date "2026.05.03"]',
        '[Date "2026.05.04"]',
        '[Date "2026.05.05"]',
    ]

    # Aggregate
    batch_summary = aggregate_batch(per_game_results, pgn_list)

    # Verify top-level fields
    assert isinstance(batch_summary, dict)
    assert "games_analyzed" in batch_summary
    assert "date_range" in batch_summary
    assert "overall_accuracy" in batch_summary
    assert "win_loss_draw" in batch_summary
    assert "phase_performance" in batch_summary
    assert "recurring_weaknesses" in batch_summary
    assert "strength_patterns" in batch_summary
    assert "most_common_blunder_type" in batch_summary
    assert "worst_phase" in batch_summary
    assert "best_phase" in batch_summary
    assert "all_phases_solid" in batch_summary

    # Verify field types
    assert isinstance(batch_summary["games_analyzed"], int)
    assert batch_summary["games_analyzed"] == 5

    assert isinstance(batch_summary["date_range"], str)

    assert isinstance(batch_summary["overall_accuracy"], (float, int, type(None)))
    if batch_summary["overall_accuracy"] is not None:
        assert 0.0 <= batch_summary["overall_accuracy"] <= 1.0

    assert isinstance(batch_summary["win_loss_draw"], dict)
    assert "wins" in batch_summary["win_loss_draw"]
    assert "losses" in batch_summary["win_loss_draw"]
    assert "draws" in batch_summary["win_loss_draw"]
    assert isinstance(batch_summary["win_loss_draw"]["wins"], int)
    assert isinstance(batch_summary["win_loss_draw"]["losses"], int)
    assert isinstance(batch_summary["win_loss_draw"]["draws"], int)

    # Verify phase_performance structure
    assert isinstance(batch_summary["phase_performance"], dict)
    for phase_name in ["opening", "middlegame", "endgame"]:
        assert phase_name in batch_summary["phase_performance"]
        phase_data = batch_summary["phase_performance"][phase_name]
        assert isinstance(phase_data, dict)
        assert "score" in phase_data
        assert "trend" in phase_data
        if phase_data["score"] is not None:
            assert 0.0 <= phase_data["score"] <= 1.0
        assert phase_data["trend"] in [
            "strong",
            "weak",
            "average",
            "inconsistent",
            "no_data",
        ]

    # Opening phase must include primary_openings
    opening_phase = batch_summary["phase_performance"]["opening"]
    assert "primary_openings" in opening_phase
    assert isinstance(opening_phase["primary_openings"], list)

    # Middlegame/endgame must include worst_aspect from enum
    for phase_name in ["middlegame", "endgame"]:
        phase_data = batch_summary["phase_performance"][phase_name]
        assert "worst_aspect" in phase_data
        assert phase_data["worst_aspect"] in [
            "tactical_oversight",
            "time_pressure",
            "positional",
            "technique",
        ]

    # Verify recurring_weaknesses structure
    assert isinstance(batch_summary["recurring_weaknesses"], list)
    for weakness in batch_summary["recurring_weaknesses"]:
        assert isinstance(weakness, dict)
        assert "pattern" in weakness
        assert "frequency" in weakness
        assert "avg_eval_swing" in weakness
        assert "impact" in weakness
        assert "example_game_ids" in weakness

        assert isinstance(weakness["pattern"], str)
        assert isinstance(weakness["frequency"], str)
        assert isinstance(weakness["avg_eval_swing"], (float, int))
        assert weakness["impact"] in ["critical", "high", "medium"]
        assert isinstance(weakness["example_game_ids"], list)

    # Verify strength_patterns structure
    assert isinstance(batch_summary["strength_patterns"], list)
    for pattern in batch_summary["strength_patterns"]:
        assert isinstance(pattern, dict)
        assert "pattern" in pattern
        assert "frequency" in pattern
        assert isinstance(pattern["pattern"], str)
        assert isinstance(pattern["frequency"], str)

    # Verify simple fields
    assert isinstance(batch_summary["most_common_blunder_type"], str)
    assert isinstance(batch_summary["worst_phase"], str)
    assert isinstance(batch_summary["best_phase"], str)
    assert isinstance(batch_summary["all_phases_solid"], bool)

    # No-data phase sentinel behavior
    middlegame = batch_summary["phase_performance"]["middlegame"]
    assert middlegame["score"] == 0.5
    assert middlegame["trend"] == "no_data"


def test_batch_aggregator_data_consistency():
    """Test that aggregated data makes logical sense."""
    clean_result = _make_game_result("clean-1", "1-0", "Italian Game", 0.18, 0.22, "pin")
    blunder_result = _make_game_result("blunder-1", "0-1", "Sicilian Defense", 0.38, 0.70, "fork")
    clean_result_2 = _make_game_result("clean-2", "1-0", "Italian Game", 0.12, 0.25, "pin")
    clean_result_3 = _make_game_result("clean-3", "1/2-1/2", "French Defense", 0.20, 0.28, "hanging_piece")
    blunder_result_2 = _make_game_result("blunder-2", "0-1", "Caro-Kann Defense", 0.42, 0.75, "fork")

    per_game_results = [
        clean_result,
        blunder_result,
        clean_result_2,
        clean_result_3,
        blunder_result_2,
    ]
    pgn_list = [
        '[Date "2026.05.01"]',
        '[Date "2026.05.02"]',
        '[Date "2026.05.03"]',
        '[Date "2026.05.04"]',
        '[Date "2026.05.05"]',
    ]

    batch_summary = aggregate_batch(per_game_results, pgn_list)

    # Verify win/loss/draw counts
    total = (
        batch_summary["win_loss_draw"]["wins"]
        + batch_summary["win_loss_draw"]["losses"]
        + batch_summary["win_loss_draw"]["draws"]
    )
    assert total == batch_summary["games_analyzed"]

    # Verify phase counts exist
    for phase_name in ["opening", "middlegame", "endgame"]:
        phase_data = batch_summary["phase_performance"][phase_name]
        assert "score" in phase_data
        assert "trend" in phase_data

    # Strength pattern entries require detail
    for pattern in batch_summary["strength_patterns"]:
        assert "detail" in pattern
        assert isinstance(pattern["detail"], str)
        assert pattern["detail"].strip() != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
