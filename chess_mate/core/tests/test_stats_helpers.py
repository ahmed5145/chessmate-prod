"""Tests for dashboard/profile stats helpers."""

from datetime import timedelta

import pytest
from core.models import BatchAnalysisReport, Game, GameAnalysis, Profile
from core.stats_helpers import (
    compute_user_achievements,
    compute_user_average_accuracy,
    get_game_counts,
)
from django.contrib.auth.models import User
from django.utils import timezone


@pytest.fixture
def stats_user():
    user = User.objects.create_user(username="statsuser", email="stats@example.com", password="pass12345")
    profile = Profile.objects.create(
        user=user,
        credits=10,
        chess_com_username="statsuser",
    )
    return user, profile


@pytest.mark.django_db
class TestAverageAccuracy:
    def test_reads_metrics_overall_accuracy(self, stats_user):
        user, profile = stats_user
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="statsuser",
            black="opponent",
            result="win",
            pgn='[Event "Test"]\n1. e4 e5',
            analysis_status="analyzed",
            date_played=timezone.now(),
        )
        GameAnalysis.objects.create(
            game=game,
            analysis_data={
                "metrics": {
                    "overall": {
                        "accuracy": 82.4,
                        "mistakes": 2,
                        "blunders": 0,
                    }
                }
            },
            accuracy_white=82.4,
            accuracy_black=70.0,
        )

        assert compute_user_average_accuracy(user, profile) == 82.4

    def test_uses_batch_summary_when_game_metrics_missing(self, stats_user):
        user, profile = stats_user
        BatchAnalysisReport.objects.create(
            user=user,
            task_id="batch-task-1",
            status="completed",
            games_count=10,
            batch_summary={"overall_accuracy_pct": 76.3},
            coaching_report={"executive_summary": "Solid opening play."},
        )

        assert compute_user_average_accuracy(user, profile, {"overall_accuracy_pct": 76.3}) == 76.3

    def test_completed_analysis_status_counts_toward_accuracy(self, stats_user):
        user, profile = stats_user
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="statsuser",
            black="opponent",
            result="win",
            pgn='[Event "Test"]\n1. e4 e5',
            status="pending",
            analysis_status="completed",
            analysis={
                "summary": {
                    "overall": {"accuracy": 71.2, "mistakes": 1, "blunders": 0},
                }
            },
            date_played=timezone.now(),
        )

        assert compute_user_average_accuracy(user, profile) == 71.2
        assert get_game_counts(user)["analyzed"] == 1

    def test_reads_per_game_batch_results_when_summary_missing(self, stats_user):
        user, profile = stats_user
        BatchAnalysisReport.objects.create(
            user=user,
            task_id="batch-task-3",
            status="completed",
            games_count=2,
            batch_summary={},
            per_game_results=[{"accuracy": 88.5}, {"accuracy": 79.0}],
            coaching_report={},
        )

        assert compute_user_average_accuracy(user, profile) == 83.8


@pytest.mark.django_db
class TestBatchAchievements:
    def test_batch_achievements_progress(self, stats_user):
        user, profile = stats_user
        BatchAnalysisReport.objects.create(
            user=user,
            task_id="batch-task-2",
            status="completed",
            games_count=25,
            batch_summary={"overall_accuracy_pct": 84.0},
            coaching_report={},
        )

        achievements = compute_user_achievements(profile)
        by_name = {item["name"]: item for item in achievements}

        assert by_name["Batch Starter"]["completed"] is True
        assert by_name["Deep Batch"]["completed"] is True
        assert by_name["Full Roster Batch"]["progress"] == 25
        assert by_name["Sharp Batch"]["completed"] is True
