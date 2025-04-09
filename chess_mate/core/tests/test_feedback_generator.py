import json
import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from core.analysis.feedback_generator import FeedbackGenerator

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_openai_response() -> Dict[str, Any]:
    """Fixture providing a properly formatted mock OpenAI response."""
    return {
        "feedback": {
            "source": "openai",
            "strengths": ["Good opening play", "Solid pawn structure"],
            "weaknesses": ["Missed tactical opportunities", "Time management"],
            "critical_moments": [
                {"move": 15, "description": "Missed winning combination"},
                {"move": 24, "description": "Defensive resource overlooked"},
            ],
            "improvement_areas": ["Tactical awareness", "Time management"],
            "opening": {
                "analysis": "Solid opening choice with good development",
                "suggestion": "Consider more active piece placement",
            },
            "middlegame": {
                "analysis": "Maintained positional advantage",
                "suggestion": "Look for tactical opportunities",
            },
            "endgame": {
                "analysis": "Technical conversion needed improvement",
                "suggestion": "Practice endgame techniques",
            },
        }
    }


@pytest.fixture
def game_metrics() -> Dict[str, Any]:
    """Fixture providing sample game metrics."""
    return {
        "overall": {
            "total_moves": 40,
            "accuracy": 85.5,
            "mistakes": 2,
            "blunders": 1,
            "average_centipawn_loss": 25,
            "time_management_score": 75.0,
        },
        "phases": {
            "opening": {"accuracy": 90.0, "mistakes": 0},
            "middlegame": {"accuracy": 82.0, "mistakes": 1},
            "endgame": {"accuracy": 84.0, "mistakes": 1},
        },
    }


@pytest.fixture
def feedback_generator():
    """Fixture providing FeedbackGenerator instance."""
    return FeedbackGenerator()


def test_initialize_openai(feedback_generator):
    """Test OpenAI client initialization."""
    with patch("core.analysis.feedback_generator.OpenAI") as mock_openai:
        feedback_generator._initialize_openai()
        assert feedback_generator.openai_client is not None
        mock_openai.assert_called_once()


def test_generate_feedback_with_openai(feedback_generator, game_metrics, mock_openai_response):
    """Test feedback generation with OpenAI."""
    with patch("core.analysis.feedback_generator.OpenAI") as mock_openai:
        # Setup mock OpenAI client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_openai_response)))]
        mock_client.chat.completions.create.return_value = mock_completion
        feedback_generator.openai_client = mock_client

        # Generate feedback
        feedback = feedback_generator.generate_feedback(game_metrics)

        # Log the generated feedback for debugging
        logger.debug(f"Generated feedback: {feedback}")

        # Verify the feedback structure
        assert isinstance(feedback, dict)
        assert "source" in feedback
        assert "strengths" in feedback
        assert "weaknesses" in feedback
        assert "critical_moments" in feedback
        assert "improvement_areas" in feedback
        assert "opening" in feedback
        assert "middlegame" in feedback
        assert "endgame" in feedback
        assert "metrics" in feedback

        # Verify specific content
        assert feedback["source"] == "openai"
        assert feedback["strengths"] == mock_openai_response["feedback"]["strengths"]
        assert feedback["weaknesses"] == mock_openai_response["feedback"]["weaknesses"]
        assert len(feedback["critical_moments"]) == len(mock_openai_response["feedback"]["critical_moments"])
        assert feedback["metrics"] == {
            "total_moves": 40,
            "accuracy": 85.5,
            "mistakes": 2,
            "blunders": 1,
            "average_centipawn_loss": 25,
            "time_management_score": 75.0,
        }


def test_generate_feedback_without_openai(feedback_generator, game_metrics):
    """Test feedback generation without OpenAI (fallback mode)."""
    feedback_generator.openai_client = None
    feedback = feedback_generator.generate_feedback(game_metrics)

    # Log the generated feedback for debugging
    logger.debug(f"Generated feedback without OpenAI: {feedback}")

    # Verify the feedback structure
    assert isinstance(feedback, dict)
    assert "source" in feedback
    assert feedback["source"] == "statistical"
    assert "metrics" in feedback
    assert feedback["metrics"] == {
        "total_moves": 40,
        "accuracy": 85.5,
        "mistakes": 2,
        "blunders": 1,
        "average_centipawn_loss": 25,
        "time_management_score": 75.0,
    }


def test_generate_feedback_with_invalid_metrics(feedback_generator):
    """Test feedback generation with invalid metrics."""
    invalid_metrics = {"invalid": "data"}
    feedback = feedback_generator.generate_feedback(invalid_metrics)

    # Verify the feedback structure
    assert isinstance(feedback, dict)
    assert "source" in feedback
    assert feedback["source"] == "statistical"
    assert "metrics" in feedback
    assert feedback["metrics"] == {}


def test_parse_ai_response_invalid_json(feedback_generator):
    """Test handling of invalid JSON in AI response."""
    invalid_response = "Invalid JSON"
    result = feedback_generator._parse_ai_response(invalid_response)
    assert result is None


def test_parse_ai_response_missing_fields(feedback_generator):
    """Test handling of missing required fields in AI response."""
    incomplete_response = json.dumps({"feedback": {"source": "openai"}})
    result = feedback_generator._parse_ai_response(incomplete_response)
    assert result is None
