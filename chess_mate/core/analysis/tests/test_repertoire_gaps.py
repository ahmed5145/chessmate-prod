from core.analysis.batch_aggregator import _compute_repertoire_gaps


def test_repertoire_gaps_filters_struggling_openings():
    opening_insights = [
        {
            "opening_name": "Sicilian Defense",
            "record": "0W-3L-0D",
            "status": "struggling",
            "player_color": "black",
            "recommendation": "Review theory.",
        },
        {
            "opening_name": "Italian Game",
            "record": "3W-0L-0D",
            "status": "strong",
            "player_color": "white",
        },
    ]

    gaps = _compute_repertoire_gaps(opening_insights)

    assert len(gaps) == 1
    assert gaps[0]["opening_name"] == "Sicilian Defense"
    assert gaps[0]["player_color"] == "black"
    assert "repertoire gap" in gaps[0]["summary"]
