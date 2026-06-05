from unittest.mock import patch

from core.analysis.per_game_coach_generator import (
    attach_coach_notes_to_results,
    generate_per_game_coach_notes,
)


def _sample_game(game_id="game_0"):
    return {
        "game_id": game_id,
        "opening_name": "Italian Game",
        "result": "0-1",
        "critical_moments": [
            {
                "move_number": 12,
                "type": "blunder",
                "phase": "middlegame",
                "played_move": "Qh5",
                "best_move": "Nf3",
                "tactical_theme": "hanging_piece",
                "eval_swing": 2.4,
                "explanation": "Left the queen exposed.",
            }
        ],
    }


def test_template_coach_notes_without_openai():
    with patch("openai.OpenAI", side_effect=Exception("OpenAI unavailable")):
        notes = generate_per_game_coach_notes([_sample_game()], player_rating=1400)

    assert "game_0" in notes
    assert "move 12" in notes["game_0"].lower()
    assert "hanging piece" in notes["game_0"].lower() or "hanging_piece" in notes["game_0"]


def test_attach_coach_notes_to_results():
    games = [_sample_game()]
    updated = attach_coach_notes_to_results(games, {"game_0": "Focus on move 12."})
    assert updated[0]["coach_note"] == "Focus on move 12."
