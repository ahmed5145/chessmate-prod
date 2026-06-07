"""Tests for ECO opening name resolution."""

from core.eco_codes import get_opening_name


def test_get_opening_name_b73_exact():
    assert "Dragon" in get_opening_name("B73")
    assert get_opening_name("B73") != "Unknown Opening"


def test_get_opening_name_prefix_fallback():
    # B81 is not in the sparse map; should fall back to B80
    name = get_opening_name("B81")
    assert name != "Unknown Opening"
    assert "Scheveningen" in name
