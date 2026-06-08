"""Tests for batch context resolution on single-game drill-down."""

from django.contrib.auth.models import User

from core.analysis.single_game_context import (
    game_qualifies_for_batch_waiver,
    resolve_batch_context_for_game,
)
from core.models import BatchAnalysisReport
from core.tests.profile_helpers import ensure_profile


def test_resolve_batch_context_links_moment_and_priority(test_user):
    report = BatchAnalysisReport.objects.create(
        user=test_user,
        task_id="batch_ctx_001",
        status="completed",
        games_count=5,
        batch_summary={
            "worst_phase": "opening",
            "recurring_weaknesses": [{"pattern": "hanging_pieces"}],
            "top_critical_moments": [
                {
                    "move_number": 12,
                    "type": "mistake",
                    "saved_game_id": 77,
                    "played_move": "Nf3",
                    "best_move": "d4",
                    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                }
            ],
            "phase_performance": {
                "opening": {"score": 0.55, "trend": "weak"},
            },
        },
        coaching_report={
            "top_3_priorities": [
                {"rank": 1, "title": "Fix opening prep"},
                {"rank": 2, "title": "Scan for tactics"},
            ]
        },
        per_game_results=[
            {
                "game_id": "game_0",
                "saved_game_id": 77,
                "opening_name": "Italian Game",
                "eco_code": "C50",
                "result": "0-1",
                "critical_moments": [
                    {
                        "move_number": 12,
                        "type": "mistake",
                        "played_move": "Nf3",
                        "best_move": "d4",
                    }
                ],
            }
        ],
    )

    context = resolve_batch_context_for_game(
        test_user,
        77,
        batch_id=report.pk,
        move_number=12,
        priority_index=1,
        single_game_moments=[{"move_number": 12, "type": "blunder"}],
    )

    assert context is not None
    assert context["batch_id"] == report.pk
    assert context["priority"]["title"] == "Fix opening prep"
    assert context["linked_moment"]["move_number"] == 12
    assert context["opening_name"] == "Italian Game"
    assert context["pattern_label"] == "Fix opening prep"
    assert "depth-14" in (context.get("classification_disclaimer") or "")


def test_game_qualifies_for_batch_waiver(test_user):
    report = BatchAnalysisReport.objects.create(
        user=test_user,
        task_id="batch_ctx_002",
        status="completed",
        games_count=1,
        per_game_results=[{"game_id": "game_0", "saved_game_id": 88}],
    )

    assert game_qualifies_for_batch_waiver(test_user, 88, report.pk) is True
    assert game_qualifies_for_batch_waiver(test_user, 99, report.pk) is False


def test_resolve_batch_context_returns_none_for_foreign_batch(test_user):
    other = User.objects.create_user(username="other_ctx", password="pass")
    ensure_profile(other)

    report = BatchAnalysisReport.objects.create(
        user=other,
        task_id="batch_ctx_003",
        status="completed",
        games_count=1,
        per_game_results=[{"saved_game_id": 10}],
    )

    assert resolve_batch_context_for_game(test_user, 10, batch_id=report.pk) is None
