from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from core.models import Game
from core.task_manager import TaskManager


@pytest.fixture
def task_manager():
    manager = TaskManager(redis_client=None)
    manager.tasks.clear()
    manager.game_tasks.clear()
    return manager


@pytest.mark.django_db
def test_abandon_stale_queued_task_clears_mapping_and_resets_game(task_manager, django_user_model):
    user = django_user_model.objects.create_user(username="queue_user", password="pass")
    game = Game.objects.create(
        user=user,
        white="White",
        black="Black",
        pgn='[Event "Test"]\n\n1. e4 e5 2. Nf3 Nc6 *\n',
        analysis_status="analyzing",
    )
    task_id = task_manager.create_task(game_id=game.id, task_type=task_manager.TYPE_ANALYSIS)
    task_manager.tasks[task_id]["created_at"] = (datetime.now() - timedelta(minutes=5)).isoformat()
    task_manager.tasks[task_id]["updated_at"] = task_manager.tasks[task_id]["created_at"]

    with patch.object(task_manager, "_workers_ping", return_value=False):
        assert task_manager._is_stale_queued_task(task_id, task_manager.tasks[task_id]) is True

    task_manager.abandon_stale_queued_task(task_id, game.id, reason="no_workers")
    game.refresh_from_db()

    assert task_manager._get_task_id_for_game(game.id) is None
    assert game.analysis_status == "not_analyzed"
    assert task_manager.tasks[task_id]["status"] == "FAILURE"


def test_get_active_tasks_for_game_drops_stale_pending(task_manager):
    game_id = 173
    task_id = task_manager.create_task(game_id=game_id, task_type=task_manager.TYPE_ANALYSIS)
    task_manager.tasks[task_id]["created_at"] = (datetime.now() - timedelta(minutes=5)).isoformat()
    task_manager.tasks[task_id]["updated_at"] = task_manager.tasks[task_id]["created_at"]

    with patch.object(task_manager, "_workers_ping", return_value=False):
        active = task_manager.get_active_tasks_for_game(game_id)

    assert active == []
    assert str(game_id) not in task_manager.game_tasks


def test_get_task_status_reports_queue_wait_when_worker_busy(task_manager):
    game_id = 55
    task_id = task_manager.create_task(game_id=game_id, task_type=task_manager.TYPE_ANALYSIS)

    with patch.object(task_manager, "_workers_busy_elsewhere", return_value=True):
        status = task_manager.get_task_status(game_id=game_id)

    assert "finishing another review first" in status["message"]
    assert status["status"] == "PENDING"


@pytest.mark.django_db
def test_release_analysis_queue_endpoint(authenticated_client, test_user):
    game = Game.objects.create(
        user=test_user,
        white="White",
        black="Black",
        pgn='[Event "Test"]\n\n1. e4 e5 *\n',
        analysis_status="analyzing",
    )
    manager = TaskManager(redis_client=None)
    manager.tasks.clear()
    manager.game_tasks.clear()
    manager.create_task(game_id=game.id, task_type=manager.TYPE_ANALYSIS)

    with patch("core.game_views.task_manager", manager):
        response = authenticated_client.post(f"/api/v1/games/{game.id}/release-analysis/")

    assert response.status_code == 200
    assert response.json()["status"] == "released"
    game.refresh_from_db()
    assert game.analysis_status == "not_analyzed"
    assert manager._get_task_id_for_game(game.id) is None
