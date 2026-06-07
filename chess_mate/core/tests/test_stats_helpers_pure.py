"""Pure unit tests for stats_helpers normalization helpers."""

from core.stats_helpers import _normalize_accuracy_value


class TestNormalizeAccuracyValue:
    def test_returns_none_for_missing_or_non_positive_values(self):
        assert _normalize_accuracy_value(None) is None
        assert _normalize_accuracy_value("bad") is None
        assert _normalize_accuracy_value(0) is None
        assert _normalize_accuracy_value(-3.2) is None

    def test_scales_legacy_zero_to_one_scores_to_percent(self):
        assert _normalize_accuracy_value(0.824) == 82.4
        assert _normalize_accuracy_value(1) == 100.0

    def test_rounds_percent_style_values(self):
        assert _normalize_accuracy_value(72.456) == 72.5
        assert _normalize_accuracy_value("81.2") == 81.2
