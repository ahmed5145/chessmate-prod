"""Pure unit tests for batch_rerun helpers."""

from core.batch_rerun import _normalize_game_ids


class TestNormalizeGameIds:
    def test_returns_empty_for_missing_or_invalid_input(self):
        assert _normalize_game_ids(None) == []
        assert _normalize_game_ids("1,2,3") == []

    def test_preserves_none_entries_and_coerces_ints(self):
        assert _normalize_game_ids([None, "12", 34, "bad", 56.7]) == [None, 12, 34, 56]
