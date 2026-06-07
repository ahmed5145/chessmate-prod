"""Tests for dashboard insight formatting."""

from core.stats_helpers import format_dashboard_insights


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
