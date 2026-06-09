"""Tests for win/loss × phase heatmap (SRG-18)."""

from core.models import BatchAnalysisReport, Game
from core.phase_heatmap import build_phase_result_heatmap
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase


def _phase(moves, accuracy, avg_eval_drop=0.1):
    return {
        "moves": moves,
        "accuracy": accuracy,
        "avg_eval_drop": avg_eval_drop,
        "blunders": 0,
        "mistakes": 0,
        "inaccuracies": 0,
    }


def _per_game(saved_id, result, player_color, phase_acc, phase="middlegame"):
    breakdown = {
        "opening": _phase(8, 70),
        "middlegame": _phase(12, 70),
        "endgame": _phase(4, 70),
    }
    breakdown[phase] = _phase(12, phase_acc, avg_eval_drop=0.4)
    return {
        "saved_game_id": saved_id,
        "result": result,
        "player_color": player_color,
        "phase_breakdown": breakdown,
        "critical_moments": [
            {"phase": phase, "move_number": 18, "eval_swing": 0.8},
        ],
    }


class TestPhaseHeatmap(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="heatmapuser", password="pass")
        ensure_profile(self.user, credits=10)
        for index in range(6):
            Game.objects.create(
                user=self.user,
                platform="lichess",
                white="heatmapuser",
                black=f"opp{index}",
                result="loss",
                pgn="1. e4 e5",
                analysis_status="analyzed",
            )

    def test_hidden_when_fewer_than_five_analyzed_games(self):
        user = User.objects.create_user(username="smalluser", password="pass")
        ensure_profile(user, credits=10)
        for index in range(3):
            Game.objects.create(
                user=user,
                platform="lichess",
                white="smalluser",
                black=f"o{index}",
                result="loss",
                pgn="1. e4 e5",
                analysis_status="analyzed",
            )
        payload = build_phase_result_heatmap(user)
        assert payload["show"] is False

    def test_highlights_loss_middlegame_with_example_link(self):
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="heatmap-batch",
            status="completed",
            games_count=6,
            per_game_results=[
                _per_game(101, "0-1", "white", 48, "middlegame"),
                _per_game(102, "0-1", "white", 50, "middlegame"),
                _per_game(103, "0-1", "white", 52, "middlegame"),
                _per_game(104, "1-0", "white", 78, "opening"),
                _per_game(105, "1-0", "white", 80, "opening"),
                _per_game(106, "1/2-1/2", "white", 74, "endgame"),
            ],
        )
        payload = build_phase_result_heatmap(self.user)
        assert payload["show"] is True
        loss_mid = next(cell for cell in payload["cells"] if cell["result"] == "loss" and cell["phase"] == "middlegame")
        assert loss_mid["highlight"] is True
        assert loss_mid["game_count"] >= 3
        assert loss_mid["example_games"][0]["href"].startswith("/game/101/analysis?mode=review")
        assert payload["top_insight"]["headline"] == "You lose winning middlegames"
