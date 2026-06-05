from core.rating_band_coaching import rating_band_coaching


def test_rating_band_intermediate():
    result = rating_band_coaching(1550)
    assert result["band"] == "intermediate"
    assert "1400" in result["label"]
    assert result["daily_drill"]


def test_rating_band_none():
    assert rating_band_coaching(None) is None
