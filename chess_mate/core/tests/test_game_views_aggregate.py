"""Unit tests for batch aggregate metrics builder in game_views."""

from unittest.mock import patch

import pytest
from core import game_views
from core.models import Game, GameAnalysis
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User

ANALYSIS_DATA = {
    "metrics": {
        "overall": {
            "accuracy": 85.0,
            "mistakes": 2,
            "blunders": 1,
            "inaccuracies": 5,
            "total_moves": 40,
        },
        "phases": {
            "opening": {"accuracy": 90, "mistakes": 0, "best_moves": 3, "opportunities": 4},
            "middlegame": {"accuracy": 55, "mistakes": 2, "best_moves": 1, "opportunities": 2},
            "endgame": {"accuracy": 70, "mistakes": 0, "best_moves": 2, "opportunities": 3},
        },
        "time_management": {
            "avg_time_per_move": 12,
            "time_pressure_percentage": 15,
        },
    },
    "feedback": {
        "strengths": ["Good opening play"],
        "weaknesses": ["Missed tactics"],
        "improvement_areas": ["Practice forks"],
    },
    "moves": [
        {
            "is_critical": True,
            "move_number": 18,
            "san": "Qh5",
            "classification": "blunder",
            "eval_change": -3.2,
        }
    ],
}


@pytest.fixture
def aggregate_user():
    user = User.objects.create_user(username="agguser", email="agg@example.com", password="pass12345")
    ensure_profile(user, email_verified=True, credits=10)
    return user


class TestBuildBatchAggregateMetrics:
    def test_returns_empty_dict_without_game_ids(self):
        assert game_views._build_batch_aggregate_metrics([]) == {}
        assert game_views._build_batch_aggregate_metrics([{"name": "bad"}]) == {}

    @pytest.mark.django_db
    def test_returns_empty_dict_when_analyses_missing(self):
        assert game_views._build_batch_aggregate_metrics([{"game_id": 999999}]) == {}

    @pytest.mark.django_db
    @patch("core.game_views.CoachingFeedbackGenerator")
    def test_builds_aggregate_metrics_from_analyses(self, mock_generator, aggregate_user):
        game = Game.objects.create(
            user=aggregate_user,
            platform="lichess",
            white="agguser",
            black="opponent",
            result="loss",
            pgn='[Event "Test"]\n1. e4 e5',
            raw_game_data={},
            opening_name="Italian Game: Classical Variation",
            analysis_status="completed",
        )
        GameAnalysis.objects.create(game=game, analysis_data=ANALYSIS_DATA)

        mock_generator.build_training_block.return_value = {
            "phase_motifs": {"weakest_phase": "middlegame"},
            "impact_metrics": {"accuracy_gap": 12.0},
        }
        mock_generator.return_value.generate_feedback.side_effect = ValueError("skip ai")

        result = game_views._build_batch_aggregate_metrics([{"game_id": game.id}])

        assert result["games_analyzed"] == 1
        assert result["overall"]["accuracy"] == 85.0
        assert result["middlegame"]["accuracy"] == 55.0
        assert result["coach_report"]["top_strengths"]
        assert result["coach_report"]["critical_moments"][0]["san"] == "Qh5"
        assert result["ai_feedback"]["source"] == "statistical"
        assert result["phase_motifs"]["weakest_phase"] == "middlegame"
