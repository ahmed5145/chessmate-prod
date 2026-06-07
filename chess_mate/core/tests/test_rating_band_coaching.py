from core.rating_band_coaching import rating_band_coaching


def test_rating_band_intermediate():
    result = rating_band_coaching(1550)
    assert result["band"] == "intermediate"
    assert "1400" in result["label"]
    assert result["daily_drill"]


def test_rating_band_none():
    assert rating_band_coaching(None) is None


def test_rating_band_tailors_to_opening_weakness():
    result = rating_band_coaching(
        1950,
        worst_phase="opening",
        repertoire_gaps=[{"opening_name": "Sicilian Defense"}],
    )
    assert "opening" in result["focus"].lower()
    assert "endgame" not in result["daily_drill"].lower() or "opening" in result["daily_drill"].lower()


def test_rating_band_tailors_to_endgame_when_data_exists():
    result = rating_band_coaching(
        1950,
        worst_phase="endgame",
        endgame_insights=[{"endgame_type": "rook_and_pawn", "label": "Rook and pawn", "study_focus": "Study Lucena."}],
    )
    assert "rook" in result["focus"].lower() or "endgame" in result["focus"].lower()
