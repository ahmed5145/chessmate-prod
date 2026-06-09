"""Tests for batch Stockfish re-run (ops / classification refresh)."""

import pytest
from core.batch_rerun import (
    BatchRerunError,
    collect_batch_pgns,
    prepare_batch_rerun,
    queue_batch_rerun,
    resolve_batch_game_ids,
)
from core.models import BatchAnalysisReport, Game
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth import get_user_model


@pytest.mark.django_db
class TestBatchRerun:
    def setup_method(self):
        self.user = get_user_model().objects.create_user(
            username="rerun_user",
            email="rerun@example.com",
            password="testpass123",
        )
        ensure_profile(self.user, credits=50)
        self.games = []
        for i in range(5):
            self.games.append(
                Game.objects.create(
                    user=self.user,
                    platform="lichess",
                    game_id=f"rerun-{i}",
                    pgn=f'[Event "Test"]\n[White "A"]\n[Black "B"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 {i}',
                    white="A",
                    black="B",
                    result="win",
                )
            )
        self.batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="rerun-task-1",
            status="completed",
            games_count=5,
            game_ids=[g.id for g in self.games],
            per_game_results=[
                {"saved_game_id": g.id, "game_id": f"game_{idx}"}
                for idx, g in enumerate(self.games)
            ],
        )

    def test_resolve_batch_game_ids_from_metadata(self):
        assert resolve_batch_game_ids(self.batch) == [g.id for g in self.games]

    def test_collect_batch_pgns(self):
        pgns, source_ids = collect_batch_pgns(self.batch)
        assert len(pgns) == 5
        assert source_ids == [g.id for g in self.games]

    def test_prepare_batch_rerun_clears_outputs(self):
        self.batch.batch_summary = {"games_analyzed": 5}
        self.batch.coaching_report = {"executive_summary": "test"}
        self.batch.save()
        prepare_batch_rerun(self.batch)
        self.batch.refresh_from_db()
        assert self.batch.status == "in_progress"
        assert self.batch.batch_summary is None
        assert self.batch.coaching_report is None

    def test_queue_batch_rerun_rejects_in_progress(self):
        self.batch.status = "in_progress"
        self.batch.save(update_fields=["status"])
        with pytest.raises(BatchRerunError, match="in_progress"):
            queue_batch_rerun(self.batch, eager=True)

    def test_queue_batch_rerun_eager(self, monkeypatch):
        subtask_calls = []
        aggregate_calls = []

        def fake_subtask(pgn, game_id, batch_id, user_id, saved_id=None):
            subtask_calls.append(game_id)
            return {
                "game_id": game_id,
                "status": "success",
                "result": {"game_id": game_id},
            }

        def fake_aggregate(results, batch_id, pgn_list, user_id):
            aggregate_calls.append(batch_id)

        monkeypatch.setattr("core.tasks.analyze_single_game_subtask", fake_subtask)
        monkeypatch.setattr("core.tasks.aggregate_and_report_task", fake_aggregate)

        message = queue_batch_rerun(self.batch, eager=True)
        assert "Re-analyzed" in message
        assert len(subtask_calls) == 5
        assert aggregate_calls == ["rerun-task-1"]
