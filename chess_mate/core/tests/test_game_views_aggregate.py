"""Unit tests for batch aggregate metrics builder in game_views."""

from unittest.mock import MagicMock, patch

from core import game_views


def _analysis_fixture(game_id=101, accuracy=85.0):
    analysis = MagicMock()
    analysis.game.id = game_id
    analysis.game.opening_name = "Italian Game: Classical Variation"
    analysis.analysis_data = {
        "metrics": {
            "overall": {
                "accuracy": accuracy,
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
    return analysis


class TestBuildBatchAggregateMetrics:
    def test_returns_empty_dict_without_game_ids(self):
        assert game_views._build_batch_aggregate_metrics([]) == {}
        assert game_views._build_batch_aggregate_metrics([{"name": "bad"}]) == {}

    @patch("core.game_views.CoachingFeedbackGenerator")
    @patch("core.game_views.GameAnalysis")
    def test_builds_aggregate_metrics_from_analyses(self, mock_game_analysis, mock_generator):
        mock_game_analysis.objects.select_related.return_value.filter.return_value = [
            _analysis_fixture()
        ]
        mock_generator.build_training_block.return_value = {
            "phase_motifs": {"weakest_phase": "middlegame"},
            "impact_metrics": {"accuracy_gap": 12.0},
        }
        mock_generator.return_value.generate_feedback.side_effect = ValueError("skip ai")

        result = game_views._build_batch_aggregate_metrics([{"game_id": 101}])

        assert result["games_analyzed"] == 1
        assert result["overall"]["accuracy"] == 85.0
        assert result["middlegame"]["accuracy"] == 55.0
        assert result["coach_report"]["top_strengths"]
        assert result["coach_report"]["critical_moments"][0]["san"] == "Qh5"
        assert result["ai_feedback"]["source"] == "statistical"
        assert result["phase_motifs"]["weakest_phase"] == "middlegame"

    @patch("core.game_views.GameAnalysis")
    def test_returns_empty_dict_when_analyses_missing(self, mock_game_analysis):
        mock_game_analysis.objects.select_related.return_value.filter.return_value = []

        assert game_views._build_batch_aggregate_metrics([{"game_id": 999}]) == {}
