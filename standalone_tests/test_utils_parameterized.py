"""Parameterized tests for utility functions."""

import pytest
from test_utils_standalone import (
    is_valid_move,  # Reuse the function we've already tested
)

# Valid moves with descriptions
VALID_MOVES = [
    ("e4", "pawn move"),
    ("Nf3", "knight move"),
    ("Qxe5", "queen capture"),
    ("Kd2", "king move"),
    ("Rxh8", "rook capture"),
    ("Bb5", "bishop move"),
    ("axb5", "pawn capture"),
    ("O-O", "kingside castling"),
    ("O-O-O", "queenside castling"),
    ("e8=Q", "pawn promotion to queen"),
    ("h1", "move to corner square"),
]

# Invalid moves with descriptions
INVALID_MOVES = [
    ("", "empty string"),
    (None, "None value"),
    ("X5", "invalid piece"),
    ("abcdefghi", "too long"),
    ("j4", "invalid file"),
    (1234, "not a string"),
    ("12", "numeric only"),
    ("A1", "uppercase file"),
    ("e9", "rank out of range"),
    ("i1", "file out of range"),
]


@pytest.mark.parametrize("move,description", VALID_MOVES)
def test_valid_moves(move, description):
    """Test that valid chess moves are correctly identified."""
    assert is_valid_move(move) is True, f"Move '{move}' ({description}) should be valid"


@pytest.mark.parametrize("move,description", INVALID_MOVES)
def test_invalid_moves(move, description):
    """Test that invalid chess moves are correctly rejected."""
    assert is_valid_move(move) is False, f"Move '{move}' ({description}) should be invalid"


# Edge cases for different chess move notations
@pytest.mark.parametrize(
    "move,expected,description",
    [
        # Test advanced notation cases
        ("exd5", True, "pawn capture with file"),
        ("Nxd5+", True, "knight capture with check"),
        ("Qh4#", True, "queen move with checkmate"),
        ("fxg1=Q+", True, "pawn promotion with capture and check"),
        ("Kh1+", True, "king move with check"),
        # Ambiguous moves
        ("Nbd7", True, "disambiguated knight move (file)"),
        ("R1a3", True, "disambiguated rook move (rank)"),
        ("Qb1a2", True, "disambiguated queen move (square)"),
    ],
)
def test_edge_case_moves(move, expected, description):
    """Test edge cases for chess move notation."""
    # This test might fail if is_valid_move doesn't support all notations
    # We're marking it as a separate test to isolate these advanced cases
    result = is_valid_move(move)
    # Use this format for better error messages
    assert result == expected, f"Move '{move}' ({description}): expected {expected}, got {result}"
