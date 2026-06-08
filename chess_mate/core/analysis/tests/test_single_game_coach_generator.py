"""Tests for structured single-game coaching output."""

from core.analysis.single_game_coach_generator import generate_single_game_coaching


def test_template_coaching_without_openai_key(settings):
    settings.OPENAI_API_KEY = ""
    coaching = generate_single_game_coaching(
        analyzed_moves=[],
        metrics_summary={"overall": {"accuracy": 72.5, "mistakes": 3}, "phases": {}},
        critical_moments=[
            {
                "move_number": 18,
                "played_move": "Qh5",
                "best_move": "Nf3",
            }
        ],
        game_context={"opening_name": "Sicilian Defense"},
    )
    assert coaching["takeaway"]
    assert coaching["do_today"]
    assert coaching["source"] == "template"
    assert coaching["critical_moments"][0]["move_number"] == 18


def test_template_coaching_references_batch_priority(settings):
    settings.OPENAI_API_KEY = ""
    coaching = generate_single_game_coaching(
        analyzed_moves=[],
        metrics_summary={"overall": {"accuracy": 70, "mistakes": 2}, "phases": {}},
        critical_moments=[{"move_number": 5, "played_move": "e4", "best_move": "d4"}],
        batch_context={
            "priority": {
                "title": "Reduce opening inaccuracies",
                "specific_drill": "Practice 10 opening puzzles.",
            }
        },
    )
    assert "batch priority" in coaching["takeaway"].lower()
    assert "opening inaccuracies" in coaching["takeaway"]
    assert coaching["do_today"] == "Practice 10 opening puzzles."
