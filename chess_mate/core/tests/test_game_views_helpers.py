"""Unit tests for pure helper functions in game_views."""

from core import game_views


class TestNormalizeIntList:
    def test_returns_empty_for_non_list(self):
        assert game_views._normalize_int_list(None) == []
        assert game_views._normalize_int_list("1,2") == []

    def test_coerces_and_skips_invalid_values(self):
        assert game_views._normalize_int_list(["1", 2, "bad", 3.9]) == [1, 2, 3]


class TestTopItemsByFrequency:
    def test_returns_top_items_by_count_then_name(self):
        items = ["fork", "pin", "fork", "pin", "pin", "", "  "]
        assert game_views._top_items_by_frequency(items, limit=2) == ["pin", "fork"]

    def test_respects_limit(self):
        items = ["a", "b", "c", "a", "b", "c", "a"]
        assert game_views._top_items_by_frequency(items, limit=1) == ["a"]


class TestCleanFeedbackItems:
    def test_removes_blocked_fallback_phrases(self):
        items = [
            "Missed a knight fork on move 12",
            "Unable to analyze game properly",
            "Generic feedback from the engine",
            "Keep improving your opening plans",
        ]
        cleaned = game_views._clean_feedback_items(items)
        assert cleaned == [
            "Missed a knight fork on move 12",
            "Keep improving your opening plans",
        ]


class TestNormalizeOpeningName:
    def test_collapses_whitespace(self):
        assert game_views._normalize_opening_name("  Sicilian   Defense  ") == "Sicilian Defense"

    def test_truncates_long_variation_strings(self):
        long_name = "A" * 120
        normalized = game_views._normalize_opening_name(long_name, max_len=20)
        assert normalized.endswith("...")
        assert len(normalized) == 20
