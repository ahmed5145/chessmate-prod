"""Tests for dashboard insight formatting and opponent resolution."""

from datetime import timedelta

import pytest
from core.models import Game
from core.stats_helpers import (
    build_dashboard_focus_insight,
    build_dashboard_hero_metrics,
    build_dashboard_next_action,
    build_dashboard_since_last_visit,
    build_single_game_context,
    format_dashboard_insights,
    mark_dashboard_visit,
    parse_last_dashboard_visit,
    resolve_game_opponent_display,
)
from django.utils import timezone


class _ProfileStub:
    def __init__(self, chess_com_username="", lichess_username=""):
        self.chess_com_username = chess_com_username
        self.lichess_username = lichess_username

    def get_platform_username(self, platform):
        if platform == "chess.com":
            return self.chess_com_username
        if platform == "lichess":
            return self.lichess_username
        return None


def test_resolve_opponent_uses_platform_username_when_stored_opponent_missing():
    profile = _ProfileStub(chess_com_username="AhmeddM1")
    row = {
        "white": "StellarOstrich",
        "black": "AhmeddM1",
        "platform": "chess.com",
        "opponent": "",
    }
    assert resolve_game_opponent_display(row, profile) == "StellarOstrich"


@pytest.mark.django_db
def test_build_single_game_context_includes_platform_and_opponent(test_user):
    game = Game.objects.create(
        user=test_user,
        platform="lichess",
        game_id="ctx-1",
        pgn="1. e4 e5",
        white="testuser",
        black="rival",
        result="win",
        opponent="rival",
        opening_name="Sicilian Defense",
        game_url="https://lichess.org/abc",
    )
    context = build_single_game_context(game, test_user.profile)
    assert context["opponent"] == "rival"
    assert context["platform"] == "lichess"
    assert context["platform_game_url"] == "https://lichess.org/abc"
    assert context["opening_name"] == "Sicilian Defense"


def test_resolve_opponent_prefers_stored_opponent_field():
    profile = _ProfileStub(chess_com_username="AhmeddM1")
    row = {
        "white": "AhmeddM1",
        "black": "StellarOstrich",
        "platform": "chess.com",
        "opponent": "StellarOstrich",
    }
    assert resolve_game_opponent_display(row, profile) == "StellarOstrich"


def test_batch_insights_when_no_game_analysis_rows():
    insights = format_dashboard_insights(
        [],
        total_games=12,
        latest_batch_coach={
            "summary": "Focus on opening preparation.",
            "overall_accuracy_pct": 72.5,
        },
        latest_batch_summary={
            "overall_accuracy_pct": 72.5,
            "top_priorities": [{"title": "Reduce opening inaccuracies"}],
        },
    )
    assert insights
    assert "import and analyze" not in insights[0]["text"].lower()
    assert any("accuracy" in item["text"].lower() for item in insights)


def test_build_dashboard_next_action_import_when_empty():
    action = build_dashboard_next_action(total_games=0, analyzed_games=0)
    assert action["type"] == "import_games"
    assert action["cta_to"] == "/fetch-games"


def test_build_dashboard_next_action_open_batch_report():
    action = build_dashboard_next_action(
        total_games=12,
        analyzed_games=8,
        latest_batch_coach={"batch_id": 9, "summary": "Work on opening prep."},
    )
    assert action["type"] == "open_batch_report"
    assert action["cta_to"] == "/batch-report/9"


def test_build_dashboard_next_action_batch_coach_without_single_game_prereq():
    action = build_dashboard_next_action(
        total_games=10,
        analyzed_games=0,
        latest_batch_coach=None,
    )
    assert action["type"] == "start_batch_coach"
    assert action["cta_to"] == "/batch-analysis"


def test_build_dashboard_next_action_import_when_under_five_games():
    action = build_dashboard_next_action(
        total_games=3,
        analyzed_games=0,
        recent_games=[{"id": 5, "status": "pending"}],
    )
    assert action["type"] == "import_for_batch"
    assert action["cta_to"] == "/fetch-games"
    assert any(link["to"] == "/game/5/analysis" for link in action["secondary_links"])


def test_build_dashboard_focus_insight_prefers_priority():
    focus = build_dashboard_focus_insight(
        insights=[
            {"type": "warning", "text": "Top focus area: opening preparation"},
            {
                "type": "success",
                "text": "Latest batch coach: 71.0% overall accuracy across your games.",
            },
        ],
        latest_batch_coach={"batch_id": 4, "summary": "Fallback summary"},
        total_games=10,
    )
    assert "Top focus area" in focus["text"]
    assert focus["href"] == "/batch-report/4"


def test_build_dashboard_focus_insight_skips_summary_when_hero_opens_report():
    focus = build_dashboard_focus_insight(
        insights=[],
        latest_batch_coach={"batch_id": 8, "summary": "Same text shown in hero."},
        total_games=10,
        hero_action_type="open_batch_report",
    )
    assert focus["text"] != "Same text shown in hero."
    assert focus["href"] == "/batch-report/8"


def test_build_dashboard_hero_metrics_thresholds():
    metrics = build_dashboard_hero_metrics(
        total_games=20,
        analyzed_games=6,
        average_accuracy=74.2,
        win_rate=52.0,
    )
    labels = [item["label"] for item in metrics]
    assert "Analyzed" in labels
    assert "Avg accuracy" in labels
    assert "Win rate" in labels


def test_format_dashboard_insights_preserves_game_id():
    insights = format_dashboard_insights(
        [
            {
                "game_id": 42,
                "opponent": "Rival",
                "mistake_count": 3,
                "summary": "Missed tactic on move 12.",
            }
        ],
        total_games=1,
    )
    assert insights[0]["game_id"] == 42


def test_parse_last_dashboard_visit_reads_iso_timestamp():
    parsed = parse_last_dashboard_visit(
        {"last_dashboard_visit_at": "2025-06-01T12:00:00+00:00"}
    )
    assert parsed is not None
    assert parsed.year == 2025


@pytest.mark.django_db
def test_build_dashboard_since_last_visit_counts_activity(test_user):
    since = timezone.now() - timedelta(days=1)
    Game.objects.create(
        user=test_user,
        platform="lichess",
        game_id="since-visit-1",
        pgn="1. e4 e5",
        white="testuser",
        black="rival",
        result="win",
        analysis_status="analyzed",
        analysis_completed_at=timezone.now(),
    )
    summary = build_dashboard_since_last_visit(test_user, since)
    assert summary["show_banner"] is True
    assert summary["games_analyzed"] >= 1


@pytest.mark.django_db
def test_mark_dashboard_visit_updates_preferences(test_user):
    profile = test_user.profile
    profile.preferences = {}
    profile.save(update_fields=["preferences"])
    mark_dashboard_visit(profile)
    profile.refresh_from_db()
    assert profile.preferences.get("last_dashboard_visit_at")
