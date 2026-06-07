"""Pure unit tests for stats_helpers normalization helpers."""

from core.stats_helpers import (
    _accuracy_from_per_game_result,
    _batch_accuracy_from_summary,
    _extract_accuracy_from_analysis_data,
    _normalize_accuracy_value,
)


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


class TestExtractAccuracyFromAnalysisData:
    def test_returns_none_for_invalid_payload(self):
        assert _extract_accuracy_from_analysis_data(None, None, None) is None
        assert _extract_accuracy_from_analysis_data("bad", None, None) is None

    def test_reads_metrics_overall_accuracy(self):
        payload = {"metrics": {"overall": {"accuracy": 0.78}}}
        assert _extract_accuracy_from_analysis_data(payload, None, None) == 78.0

    def test_reads_summary_nested_overall_user_accuracy(self):
        payload = {"summary": {"overall": {"user_accuracy": 83.2}}}
        assert _extract_accuracy_from_analysis_data(payload, None, None) == 83.2

    def test_reads_analysis_results_summary_player_accuracy(self):
        payload = {
            "analysis_results": {
                "summary": {"player_accuracy": 0.91},
            }
        }
        assert _extract_accuracy_from_analysis_data(payload, None, None) == 91.0


class TestAccuracyFromPerGameResult:
    def test_reads_top_level_accuracy_fields(self):
        assert _accuracy_from_per_game_result({"accuracy_pct": 74.1}) == 74.1

    def test_reads_nested_metrics_overall_accuracy(self):
        result = {"metrics": {"overall": {"accuracy": 0.66}}}
        assert _accuracy_from_per_game_result(result) == 66.0

    def test_returns_none_for_invalid_rows(self):
        assert _accuracy_from_per_game_result(None) is None
        assert _accuracy_from_per_game_result({}) is None


class TestBatchAccuracyFromSummary:
    def test_prefers_overall_accuracy_pct(self):
        summary = {"overall_accuracy_pct": 71.2, "overall_accuracy": 0.5}
        assert _batch_accuracy_from_summary(summary) == 71.2

    def test_falls_back_to_scaled_overall_accuracy(self):
        summary = {"overall_accuracy": 0.63}
        assert _batch_accuracy_from_summary(summary) == 63.0

    def test_returns_none_for_missing_summary(self):
        assert _batch_accuracy_from_summary(None) is None
        assert _batch_accuracy_from_summary({}) is None
