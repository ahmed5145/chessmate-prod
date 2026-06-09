"""Tests for coach alignment score (SRG-11)."""

from core.analysis.alignment_score import compute_coach_alignment_score


def test_high_alignment_when_most_moments_match_batch_phase():
    score = compute_coach_alignment_score(
        priority={"title": "Opening prep"},
        batch_worst_phase="middlegame",
        single_game_moments=[
            {"move_number": 8, "phase": "opening"},
            {"move_number": 10, "phase": "opening"},
            {"move_number": 22, "phase": "opening"},
            {"move_number": 40, "phase": "middlegame"},
        ],
    )

    assert score is not None
    assert score["target_phase"] == "opening"
    assert score["confirmed_moments"] == 3
    assert score["relevant_moments"] == 4
    assert score["alignment_pct"] == 75
    assert score["tier"] == "high"


def test_mismatch_note_when_swings_are_in_different_phase():
    score = compute_coach_alignment_score(
        priority={"title": "Fix opening prep"},
        batch_worst_phase="opening",
        single_game_moments=[
            {"move_number": 50, "phase": "endgame"},
            {"move_number": 52, "phase": "endgame"},
        ],
    )

    assert score["confirmed_moments"] == 0
    assert score["alignment_pct"] == 0
    assert score["tier"] == "low"
    assert "Batch flagged opening" in score["mismatch_note"]
    assert "endgame" in score["mismatch_note"]


def test_returns_none_without_moments():
    assert (
        compute_coach_alignment_score(
            priority={"title": "Tactics"},
            batch_worst_phase="middlegame",
            single_game_moments=[],
        )
        is None
    )
