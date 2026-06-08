"""Tests for batch → single-game deep link builders."""

from core.batch_deep_links import build_worst_moment_deep_review_url
from core.models import BatchAnalysisReport


def test_build_worst_moment_deep_review_url_from_top_moments(test_user, settings):
    settings.FRONTEND_URL = "https://app.chessmate.test"
    report = BatchAnalysisReport.objects.create(
        user=test_user,
        task_id="deep_link_001",
        status="completed",
        games_count=3,
        batch_summary={
            "top_critical_moments": [
                {
                    "move_number": 22,
                    "saved_game_id": 501,
                    "played_move": "Qh5",
                }
            ]
        },
    )

    url = build_worst_moment_deep_review_url(report)
    assert url == f"https://app.chessmate.test/game/501/analysis?batch={report.pk}&move=22"
