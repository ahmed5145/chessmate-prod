from core.batch_compare import build_compare_narrative, metric_delta
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
