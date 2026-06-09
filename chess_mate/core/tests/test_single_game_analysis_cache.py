"""Tests for cached single-game analysis short-circuit."""

import pytest
from core.models import GameAnalysis
from core.single_game_analysis_cache import (
    cached_analysis_response,
    has_complete_cached_analysis,
)


@pytest.mark.django_db
class TestSingleGameAnalysisCache:
    def test_has_complete_cached_analysis_false_when_missing(self):
        assert has_complete_cached_analysis(999999) is False

    def test_has_complete_cached_analysis_false_without_moves(self, test_game):
        GameAnalysis.objects.create(
            game=test_game,
            analysis_data={"status": "complete", "moves": []},
            feedback={},
            depth=20,
        )
        assert has_complete_cached_analysis(test_game.id) is False

    def test_has_complete_cached_analysis_true_when_complete(self, test_game):
        GameAnalysis.objects.create(
            game=test_game,
            analysis_data={
                "status": "complete",
                "moves": [{"move_number": 1, "san": "e4"}],
            },
            feedback={},
            depth=20,
        )
        assert has_complete_cached_analysis(test_game.id) is True

    def test_cached_analysis_response_shape(self, test_game):
        payload = cached_analysis_response(test_game.id)
        assert payload["status"] == "cached"
        assert payload["cached"] is True
        assert payload["credits_charged"] == 0
        assert payload["game_id"] == test_game.id
