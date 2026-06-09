"""Pure helper tests for core.ai_feedback.AIFeedbackGenerator (no OpenAI calls)."""

import time
from unittest.mock import MagicMock, patch

import pytest
from core.ai_feedback import AIFeedbackGenerator, RateLimiter
from django.test import override_settings

TEST_SETTINGS = {
    "OPENAI_API_KEY": "test-key",
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ai-feedback-pure-tests",
        }
    },
}


@pytest.fixture
def generator():
    with patch("core.ai_feedback.OpenAI") as mock_openai:
        mock_openai.return_value = MagicMock()
        with override_settings(**TEST_SETTINGS):
            gen = AIFeedbackGenerator(api_key="test-key")
            gen._extract_tactical_patterns = MagicMock(return_value=[])
            gen._extract_positional_patterns = MagicMock(return_value=[])
            gen._extract_endgame_patterns = MagicMock(return_value=[])
            yield gen


def _sample_games_analysis():
    return [
        {
            "metadata": {
                "result": "win",
                "time_control": "blitz",
                "username": "alice",
            },
            "analysis": {
                "results": [
                    {
                        "accuracy": 80,
                        "is_tactical": True,
                        "evaluation_improvement": 1,
                        "time_spent": 5,
                    },
                    {"accuracy": 70, "time_spent": 15},
                    {"accuracy": 90, "is_tactical": False, "time_spent": 3},
                ]
            },
        },
        {
            "metadata": {
                "result": "loss",
                "time_control": "rapid",
                "username": "alice",
            },
            "analysis": {
                "results": [
                    {"accuracy": 60, "time_spent": 8},
                    {
                        "accuracy": 55,
                        "is_tactical": True,
                        "evaluation_improvement": 0,
                        "time_spent": 4,
                    },
                ]
            },
        },
    ]


def test_rate_limiter_blocks_after_max_calls():
    limiter = RateLimiter(max_calls=2, time_window=60)
    assert limiter.can_make_request() is True
    now = time.time()
    limiter.calls.extend([now, now])
    assert limiter.can_make_request() is False


def test_calculate_phase_accuracy_empty_defaults_to_65(generator):
    assert generator._calculate_phase_accuracy([]) == 65.0


def test_calculate_phase_accuracy_counts_good_moves(generator):
    moves = [{"score": 20}, {"score": 150}, {"score": -30}]
    assert generator._calculate_phase_accuracy(moves) == pytest.approx(66.7, abs=0.1)


def test_calculate_tactical_metrics_detects_swings(generator):
    moves = [
        {"score": 0},
        {"score": 250},
        {"score": 100},
        {"score": -250},
    ]
    score, missed = generator._calculate_tactical_metrics(moves)
    assert score > 0
    assert missed >= 1


def test_calculate_tactical_metrics_handles_string_scores(generator):
    moves = [{"score": "0"}, {"score": "300"}]
    score, missed = generator._calculate_tactical_metrics(moves)
    assert score >= 0
    assert missed >= 0


def test_extract_sections_parses_headers_and_bullets(generator):
    text = """
Strengths
- Solid opening development
Weaknesses
- Missed forks in the middlegame
Suggestions
- Drill forks daily
"""
    sections = generator._extract_sections(text)
    assert "Solid opening development" in sections["strengths"]
    assert "Missed forks in the middlegame" in sections["weaknesses"]
    assert "Drill forks daily" in sections["suggestions"]


def test_aggregate_metrics_summarizes_batch(generator):
    metrics = generator._aggregate_metrics(_sample_games_analysis())
    assert metrics["total_games"] == 2
    assert metrics["overall"]["win_rate"] == 50.0
    assert metrics["tactics"]["opportunities"] == 2
    assert "blitz" in metrics["time_management"]["time_controls"]


def test_aggregate_metrics_empty_returns_default_feedback(generator):
    assert generator._aggregate_metrics([]) == generator._get_default_feedback()


def test_generate_fallback_feedback_includes_phase_analysis(generator):
    game_analysis = [{"score": 10}, {"score": 20}, {"score": 300}]
    feedback = generator._generate_fallback_feedback(game_analysis)
    assert "opening" in feedback
    assert "analysis" in feedback["opening"]
    assert feedback["study_plan"]["focus_areas"]


def test_parse_batch_ai_response_structures_ai_sections(generator):
    metrics = generator._aggregate_metrics(_sample_games_analysis())
    response = """
Strengths
- Good time management
Weaknesses
- Endgame technique
Suggestions
- Study rook endings
"""
    parsed = generator._parse_batch_ai_response(response, metrics)
    assert parsed["overall_metrics"]["overall"]["win_rate"] == 50.0
    assert "Good time management" in parsed["ai_analysis"]["strengths"]
    assert parsed["player_profile"]["username"] == "alice"


def test_parse_batch_ai_response_falls_back_on_parse_error(generator):
    metrics = generator._aggregate_metrics(_sample_games_analysis())
    with patch.object(generator, "_extract_sections", side_effect=RuntimeError("boom")):
        parsed = generator._parse_batch_ai_response("bad", metrics)
    assert parsed == generator._get_default_feedback()
