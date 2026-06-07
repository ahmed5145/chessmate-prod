"""Tests for dashboard insight formatting and opponent resolution."""

from core.stats_helpers import format_dashboard_insights, resolve_game_opponent_display


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
        latest_batch_coach={"summary": "Focus on opening preparation.", "overall_accuracy_pct": 72.5},
        latest_batch_summary={
            "overall_accuracy_pct": 72.5,
            "top_priorities": [{"title": "Reduce opening inaccuracies"}],
        },
    )
    assert insights
    assert "import and analyze" not in insights[0]["text"].lower()
    assert any("accuracy" in item["text"].lower() for item in insights)
