"""Tests for cross-batch moment timeline (SRG-10)."""

from core.models import BatchAnalysisReport, Game, Profile
from core.moment_timeline import (
    build_moment_signature,
    enrich_batch_report_payload,
    record_batch_timeline_events,
    record_single_game_timeline_events,
    summarize_timeline_for_signature,
)
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase


class TestMomentTimeline(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="timelineuser", password="pass")
        ensure_profile(self.user, credits=10)
        self.profile = Profile.objects.get(user=self.user)
        self.game = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="timelineuser",
            black="opponent",
            result="loss",
            pgn="1. e4 e5",
            analysis_status="analyzed",
            eco_code="B90",
        )

    def _batch(self, task_id, pattern="hanging_piece", swing=1.2):
        return BatchAnalysisReport.objects.create(
            user=self.user,
            task_id=task_id,
            status="completed",
            games_count=5,
            coaching_report={"top_3_priorities": []},
            batch_summary={
                "recurring_weaknesses": [
                    {
                        "pattern": pattern,
                        "frequency": "3 games",
                        "avg_eval_swing": swing,
                    }
                ],
                "top_critical_moments": [
                    {
                        "type": "blunder",
                        "phase": "middlegame",
                        "tactical_theme": pattern,
                        "move_number": 14,
                        "eval_swing": swing,
                        "saved_game_id": self.game.id,
                    }
                ],
            },
        )

    def test_signature_normalizes_pattern_and_phase(self):
        signature = build_moment_signature("Hanging Piece", "middlegame", "B90")
        assert signature == "hanging_piece|middlegame|B90"

    def test_timeline_hidden_with_single_event(self):
        batch = self._batch("task-one")
        record_batch_timeline_events(batch)
        signature = build_moment_signature("hanging_piece", "middlegame")
        summary = summarize_timeline_for_signature(self.profile, signature)
        assert summary["show"] is False
        assert summary["event_count"] == 1

    def test_same_pattern_in_two_batches_shows_timeline(self):
        first = self._batch("task-a")
        second = self._batch("task-b")
        record_batch_timeline_events(first)
        record_batch_timeline_events(second)

        signature = build_moment_signature("hanging_piece", "middlegame")
        summary = summarize_timeline_for_signature(self.profile, signature)
        assert summary["show"] is True
        assert summary["batch_count"] == 2
        assert "2 batches" in summary["headline"]
        assert summary["months_label"]

    def test_trend_copy_when_swing_improves(self):
        first = self._batch("task-old", swing=1.5)
        second = self._batch("task-new", swing=0.8)
        record_batch_timeline_events(first)
        record_batch_timeline_events(second)

        signature = build_moment_signature("hanging_piece", "middlegame")
        summary = summarize_timeline_for_signature(self.profile, signature)
        assert summary["show"] is True
        assert summary["trend_copy"]
        assert "down" in summary["trend_copy"]

    def test_single_game_events_contribute_to_timeline(self):
        record_single_game_timeline_events(
            self.profile,
            self.game,
            [
                {
                    "type": "blunder",
                    "phase": "opening",
                    "tactical_theme": "missed_fork",
                    "move_number": 8,
                    "eval_swing": 1.1,
                }
            ],
        )
        record_batch_timeline_events(
            BatchAnalysisReport.objects.create(
                user=self.user,
                task_id="task-single-theme",
                status="completed",
                games_count=5,
                coaching_report={"top_3_priorities": []},
                batch_summary={
                    "top_critical_moments": [
                        {
                            "type": "blunder",
                            "phase": "opening",
                            "tactical_theme": "missed_fork",
                            "move_number": 8,
                            "eval_swing": 0.9,
                            "saved_game_id": self.game.id,
                        }
                    ]
                },
            )
        )

        signature = build_moment_signature("missed_fork", "opening", "B90")
        summary = summarize_timeline_for_signature(self.profile, signature)
        assert summary["show"] is True
        assert summary["event_count"] >= 2

    def test_enrich_batch_report_payload_attaches_timelines(self):
        first = self._batch("task-enrich-1")
        second = self._batch("task-enrich-2")
        record_batch_timeline_events(first)
        record_batch_timeline_events(second)

        payload = {
            "batch_summary": second.batch_summary,
        }
        enriched = enrich_batch_report_payload(payload, self.profile)
        weakness = enriched["batch_summary"]["recurring_weaknesses"][0]
        moment = enriched["batch_summary"]["top_critical_moments"][0]
        assert weakness["timeline"]["show"] is True
        assert moment["timeline"]["show"] is True

    def test_batch_dedupes_same_batch_rerun(self):
        batch = self._batch("task-dedupe")
        record_batch_timeline_events(batch)
        record_batch_timeline_events(batch)

        signature = build_moment_signature("hanging_piece", "middlegame")
        summary = summarize_timeline_for_signature(self.profile, signature)
        assert summary["event_count"] == 1
