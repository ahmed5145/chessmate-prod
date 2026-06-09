"""Tests for SRG-19 auto-picked proof games in the priority inbox."""

from core.models import BatchAnalysisReport, Profile
from core.priority_inbox import (
    get_priority_inbox_payload,
    seed_priority_inbox_from_batch,
)
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase


class TestProofGamesInbox(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="proofuser", password="pass")
        ensure_profile(self.user, credits=10)

    def _moment(self, *, move_number, phase, eval_swing, theme="missed_tactic"):
        return {
            "move_number": move_number,
            "phase": phase,
            "eval_swing": eval_swing,
            "tactical_theme": theme,
            "type": "mistake",
        }

    def test_auto_picks_phase_matched_proof_games_for_three_priorities(self):
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="proof-batch",
            status="completed",
            games_count=5,
            batch_summary={
                "worst_phase": "opening",
                "recurring_weaknesses": [
                    {"pattern": "opening prep", "frequency": "3/5 games"},
                ],
                "top_critical_moments": [],
            },
            coaching_report={
                "top_3_priorities": [
                    {
                        "rank": 1,
                        "title": "Opening prep",
                        "specific_drill": "Review losses",
                    },
                    {
                        "rank": 2,
                        "title": "Middlegame tactics",
                        "specific_drill": "Train forks",
                    },
                    {
                        "rank": 3,
                        "title": "Endgame technique",
                        "specific_drill": "King activity",
                    },
                ]
            },
            per_game_results=[
                {
                    "game_id": "game_0",
                    "saved_game_id": 201,
                    "opening_name": "Sicilian Defense",
                    "opponent": "alpha",
                    "player_color": "white",
                    "critical_moments": [
                        self._moment(move_number=8, phase="opening", eval_swing=0.9)
                    ],
                },
                {
                    "game_id": "game_1",
                    "saved_game_id": 202,
                    "opening_name": "Italian Game",
                    "opponent": "beta",
                    "player_color": "white",
                    "critical_moments": [
                        self._moment(
                            move_number=22,
                            phase="middlegame",
                            eval_swing=1.6,
                            theme="fork",
                        )
                    ],
                },
                {
                    "game_id": "game_2",
                    "saved_game_id": 203,
                    "opening_name": "Ruy Lopez",
                    "opponent": "gamma",
                    "player_color": "white",
                    "critical_moments": [
                        self._moment(
                            move_number=55,
                            phase="endgame",
                            eval_swing=1.3,
                            theme="technique",
                        )
                    ],
                },
            ],
        )

        seed_priority_inbox_from_batch(batch)
        profile = Profile.objects.get(user=self.user)
        items = get_priority_inbox_payload(profile)["pending_items"]

        assert len(items) == 3
        assert items[0]["linked_game_id"] == 201
        assert items[0]["linked_move"] == 8
        assert "Sicilian Defense example: vs alpha, move 8" == items[0]["proof_label"]

        assert items[1]["linked_game_id"] == 202
        assert items[1]["linked_move"] == 22
        assert "Italian Game example: vs beta, move 22" == items[1]["proof_label"]

        assert items[2]["linked_game_id"] == 203
        assert items[2]["linked_move"] == 55

        linked_games = {item["linked_game_id"] for item in items}
        assert len(linked_games) == 3

    def test_batch_with_moments_always_links_at_least_one_proof_game(self):
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="proof-min",
            status="completed",
            games_count=5,
            batch_summary={"worst_phase": "middlegame"},
            coaching_report={
                "top_3_priorities": [
                    {
                        "rank": 1,
                        "title": "Time management",
                        "specific_drill": "Use a clock",
                    },
                    {
                        "rank": 2,
                        "title": "Piece activity",
                        "specific_drill": "Find active squares",
                    },
                ]
            },
            per_game_results=[
                {
                    "game_id": "game_0",
                    "saved_game_id": 301,
                    "opening_name": "French Defense",
                    "opponent": "delta",
                    "player_color": "black",
                    "critical_moments": [
                        self._moment(move_number=17, phase="middlegame", eval_swing=2.1)
                    ],
                }
            ],
        )

        seed_priority_inbox_from_batch(batch)
        profile = Profile.objects.get(user=self.user)
        items = get_priority_inbox_payload(profile)["pending_items"]

        linked = [item for item in items if item.get("linked_game_id")]
        assert len(linked) >= 1
        assert linked[0]["linked_game_id"] == 301
        assert linked[0]["linked_move"] == 17
        assert "mode=review" in (linked[0].get("href") or "")
