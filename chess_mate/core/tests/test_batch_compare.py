from core.batch_compare import build_compare_narrative, metric_delta, weakness_themes
from core.batch_observability import classify_analysis_error


def test_metric_delta_accuracy():
    current = {"overall_accuracy_pct": 52.0}
    other = {"overall_accuracy_pct": 48.0}
    assert metric_delta(current, other, "overall_accuracy_pct") == 4.0


def test_build_compare_narrative_improved_accuracy():
    metrics = {"overall_accuracy_pct_delta": 4.5, "overall_eval_stability_delta": None}
    weaknesses = {"persisting": [], "resolved": ["hanging_piece"], "new": []}
    text = build_compare_narrative(
        metrics=metrics,
        weaknesses=weaknesses,
        current_summary={"worst_phase": "middlegame"},
        other_summary={"worst_phase": "endgame"},
    )
    assert "move match improved" in text.lower()
    assert "hanging piece" in text.lower()


def test_classify_analysis_error_oom():
    assert classify_analysis_error("Killed - out of memory") == "stockfish_oom"


def test_weakness_themes_extracts_pattern_theme_type_label():
    summary = {
        "recurring_weaknesses": [
            {"pattern": "hanging_piece"},
            {"theme": "fork"},
            {"type": "pin"},
            {"label": "skewer"},
            "ignored",
        ]
    }
    assert weakness_themes(summary) == {"hanging_piece", "fork", "pin", "skewer"}


def test_metric_delta_returns_none_on_missing_or_invalid():
    assert (
        metric_delta({}, {"overall_accuracy_pct": 50}, "overall_accuracy_pct") is None
    )
    assert (
        metric_delta(
            {"overall_accuracy_pct": "bad"},
            {"overall_accuracy_pct": 50},
            "overall_accuracy_pct",
        )
        is None
    )


def test_build_compare_narrative_declined_accuracy():
    text = build_compare_narrative(
        metrics={"overall_accuracy_pct_delta": -3.2},
        weaknesses={"persisting": [], "resolved": [], "new": []},
        current_summary={},
        other_summary={},
    )
    assert "move match dipped" in text.lower()


def test_build_compare_narrative_eval_stability_slipped():
    text = build_compare_narrative(
        metrics={"overall_eval_stability_delta": -0.05},
        weaknesses={"persisting": [], "resolved": [], "new": []},
        current_summary={},
        other_summary={},
    )
    assert "eval stability slipped" in text.lower()


def test_build_compare_narrative_default_when_no_deltas():
    text = build_compare_narrative(
        metrics={},
        weaknesses={"persisting": [], "resolved": [], "new": []},
        current_summary={},
        other_summary={},
    )
    assert "metrics are similar" in text.lower()


def test_build_compare_narrative_worst_phase_shift():
    text = build_compare_narrative(
        metrics={},
        weaknesses={"persisting": [], "resolved": [], "new": []},
        current_summary={"worst_phase": "endgame"},
        other_summary={"worst_phase": "middlegame"},
    )
    assert "weakest phase shifted from middlegame to endgame" in text.lower()
