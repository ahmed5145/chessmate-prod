"""Tests for opening name compaction."""

from core.opening_name_utils import compact_opening_name


def test_compact_opening_name_strips_ellipsis_move_tree():
    raw = "Sicilian Defense Open Dragon Classical Attack...8.O O O O 9.f4 Qb6"
    assert compact_opening_name(raw) == "Sicilian Defense Open Dragon Classical Attack"


def test_compact_opening_name_keeps_named_variations():
    raw = "Queen's Pawn Game: London System"
    assert compact_opening_name(raw) == "Queen's Pawn Game: London System"


def test_compact_opening_name_drops_trailing_move_segments():
    raw = "Sicilian Defense: Dragon Variation, Yugoslav Attack, 10.O-O-O"
    assert compact_opening_name(raw) == "Sicilian Defense: Dragon Variation, Yugoslav Attack"
