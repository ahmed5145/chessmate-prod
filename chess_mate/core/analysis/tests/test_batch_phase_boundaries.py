"""Tests for batch phase boundary normalization (M6)."""

from core.analysis.batch_phase_boundaries import (
    endgame_start_from_metadata,
    normalize_phase_boundaries,
    phase_for_half_move_index,
)


def test_metadata_middlegame_length_is_count_not_end_index():
    meta = {"opening_length": 10, "middlegame_length": 20}
    assert endgame_start_from_metadata(meta, 44) == 30


def test_normalize_prevents_tiny_middlegame():
    opening, endgame = normalize_phase_boundaries(44, 2, 12)
    assert opening >= 6
    assert endgame > opening + 4
    assert endgame <= 44


def test_move_13_not_endgame_in_typical_game():
    opening, endgame = normalize_phase_boundaries(44, 10, 30)
    assert phase_for_half_move_index(13, opening, endgame) == "middlegame"


def test_short_game_has_no_endgame_slice():
    opening, endgame = normalize_phase_boundaries(10, 3, 8)
    assert endgame == 10
