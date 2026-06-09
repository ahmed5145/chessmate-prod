"""Tests for dashboard one thing today (SRG-12)."""

from core.models import BatchAnalysisReport, Game, GameAnalysis, Profile
from core.stats_helpers import build_one_thing_today, fetch_latest_single_worst_moment
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase


class TestDashboardOneThing(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="onetoday", password="pass")
        self.profile = ensure_profile(self.user, credits=10)

    def test_prefers_oldest_pending_inbox_item(self):
        payload = build_one_thing_today(
            total_games=10,
            analyzed_games=3,
            priority_inbox={
                "pending_items": [
                    {
                        "title": "Fix hanging pieces",
                        "proof_label": "Italian example: vs rival, move 14",
                        "href": "/game/5/analysis?mode=review&batch=2&priority=1&move=14",
                    }
                ]
            },
            latest_batch_coach={"batch_id": 2},
            latest_batch_moment={"saved_game_id": 9, "move_number": 20},
        )

        assert payload["source"] == "inbox"
        assert payload["cta_to"].startswith("/game/5/analysis")
        assert "mode=review" in payload["cta_to"]

    def test_falls_back_to_latest_batch_moment(self):
        payload = build_one_thing_today(
            total_games=10,
            analyzed_games=3,
            priority_inbox={"pending_items": []},
            latest_batch_coach={"batch_id": 7},
            latest_batch_moment={
                "saved_game_id": 12,
                "move_number": 18,
                "opponent": "alpha",
                "opening_name": "Sicilian Defense",
            },
        )

        assert payload["source"] == "batch"
        assert "/game/12/analysis" in payload["cta_to"]
        assert "batch=7" in payload["cta_to"]
        assert "move=18" in payload["cta_to"]

    def test_fetch_latest_single_worst_moment(self):
        game = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="onetoday",
            black="foe",
            result="loss",
            opening_name="French Defense",
            pgn="1. e4 e6",
            analysis_status="analyzed",
        )
        GameAnalysis.objects.create(
            game=game,
            feedback={
                "coaching": {
                    "critical_moments": [
                        {"move_number": 9, "phase": "opening", "eval_swing": 0.4},
                        {"move_number": 22, "phase": "middlegame", "eval_swing": 1.8},
                    ]
                }
            },
            analysis_data={"status": "complete"},
        )

        moment = fetch_latest_single_worst_moment(
            self.user, Profile.objects.get(user=self.user)
        )
        assert moment["game_id"] == game.id
        assert moment["move_number"] == 22

    def test_single_game_moment_used_when_no_inbox_or_batch(self):
        game = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="onetoday",
            black="foe",
            result="loss",
            opening_name="Caro-Kann",
            pgn="1. e4 c6",
            analysis_status="analyzed",
        )
        single = {
            "game_id": game.id,
            "move_number": 15,
            "opponent": "foe",
            "opening_name": "Caro-Kann",
        }
        payload = build_one_thing_today(
            total_games=6,
            analyzed_games=1,
            priority_inbox={"pending_items": []},
            latest_single_moment=single,
        )

        assert payload["source"] == "single_game"
        assert f"/game/{game.id}/analysis" in payload["cta_to"]
        assert "move=15" in payload["cta_to"]
