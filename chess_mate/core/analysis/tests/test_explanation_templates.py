from core.analysis.explanation_templates import get_explanation


def test_missed_tactic_formats_eval_difference_to_two_decimals():
    text = get_explanation(
        "missed_tactic",
        "Qc7",
        "d7h3",
        {"eval_difference": 2.5999999999999996},
    )
    assert "2.60" in text
    assert "5999999999999996" not in text
