from unittest.mock import patch

import pytest
from core.batch_coaching import regenerate_batch_coaching
from core.models import BatchAnalysisReport, Profile
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_regenerate_batch_coaching_rejects_pending():
    user = get_user_model().objects.create_user(username="coach_user", password="x")
    ensure_profile(user, credits=10)
    batch = BatchAnalysisReport.objects.create(
        user=user,
        task_id="pending-task",
        status="in_progress",
        games_count=5,
    )
    ok, message = regenerate_batch_coaching(batch)
    assert ok is False
    assert "must finish" in message


@pytest.mark.django_db
@patch("core.batch_coaching.generate_coaching_report")
@patch("core.batch_coaching.generate_per_game_coach_notes")
def test_regenerate_batch_coaching_success(mock_notes, mock_generate):
    user = get_user_model().objects.create_user(username="coach_ok", password="x")
    ensure_profile(user, credits=10)
    per_game = [
        {
            "game_id": f"game_{i}",
            "phase_breakdown": {
                "opening": {"moves": 1, "avg_eval_drop": 0.1, "blunders": 0, "mistakes": 0},
                "middlegame": {"moves": 0, "avg_eval_drop": 0.0, "blunders": 0, "mistakes": 0},
                "endgame": {"moves": 0, "avg_eval_drop": 0.0, "blunders": 0, "mistakes": 0},
            },
            "move_quality": {"blunder": 0, "mistake": 0, "good": 1},
        }
        for i in range(5)
    ]
    batch = BatchAnalysisReport.objects.create(
        user=user,
        task_id="done-task",
        status="partial",
        games_count=5,
        batch_summary={"player_rating": 1500, "games_analyzed": 5},
        per_game_results=per_game,
        failed_games=[],
    )
    mock_generate.return_value = {"executive_summary": "Focus on tactics."}
    mock_notes.return_value = {"game_0": "Worst moment note."}

    ok, message = regenerate_batch_coaching(batch)
    assert ok is True
    batch.refresh_from_db()
    assert batch.coaching_report["executive_summary"] == "Focus on tactics."
    assert batch.status == "completed"
