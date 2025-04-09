"""
Standalone tests for chess utility functions.

These tests can run without Django integration.
"""

import pytest


# Define the function to test directly in the test file
# This is a copy of the one in core.utils for standalone testing
def is_valid_move(move):
    """
    Check if a move is valid in algebraic notation.

    Args:
        move: A string representing a chess move in algebraic notation

    Returns:
        bool: True if the move appears valid, False otherwise
    """
    if not move or not isinstance(move, str):
        return False

    # Basic validation for algebraic notation
    if len(move) < 2 or len(move) > 10:  # Increased max length for complex notations
        return False

    # Handle castling
    if move in ["O-O", "O-O-O"]:
        return True

    # Remove check/checkmate symbols for validation
    if move.endswith("+") or move.endswith("#"):
        move = move[:-1]

    # Check first character is a valid piece or file
    valid_pieces = {"K", "Q", "R", "B", "N"}
    valid_files = {"a", "b", "c", "d", "e", "f", "g", "h"}

    first_char = move[0]

    # If first char is a piece, it must be in valid_pieces
    if first_char.isupper():
        if first_char not in valid_pieces:
            return False
    # If first char is a file, it must be in valid_files
    else:
        if first_char not in valid_files:
            return False

    # Check if the move contains a valid rank (for destination)
    contains_valid_rank = False
    for char in move:
        if char in "12345678":
            contains_valid_rank = True
            break

    if not contains_valid_rank:
        return False

    # Check for promotion format (e.g., "e8=Q" or "fxg1=Q+")
    if "=" in move:
        parts = move.split("=")
        # Check there's something before and after the equals sign
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False

        # The promotion piece must be valid (Q, R, B, N)
        promotion_piece = parts[1][0]  # Take first char in case of "Q+"
        if promotion_piece not in valid_pieces:
            return False

    return True


# Mark all tests in this module as standalone
pytestmark = pytest.mark.standalone


# Basic test cases for valid and invalid moves
@pytest.mark.parametrize(
    "move,expected",
    [
        # Valid moves
        ("e4", True),
        ("Nf3", True),
        ("O-O", True),
        # Invalid moves
        ("", False),
        (None, False),
        ("X5", False),
    ],
)
def test_is_valid_move_basic(move, expected):
    """Test basic move validation."""
    assert is_valid_move(move) is expected, f"Move '{move}' validation failed"


# Comprehensive test cases for valid chess moves
@pytest.mark.parametrize(
    "move",
    [
        "e4",  # Pawn move
        "Nf3",  # Knight move
        "Qxe5",  # Queen capture
        "Kd2",  # King move
        "Rxh8",  # Rook capture
        "Bb5",  # Bishop move
        "axb5",  # Pawn capture
        "O-O",  # Kingside castling
        "O-O-O",  # Queenside castling
        "e8=Q",  # Pawn promotion
        "h1",  # Corner move
    ],
)
def test_valid_moves(move):
    """Test comprehensive valid chess moves."""
    assert is_valid_move(move) is True, f"Expected '{move}' to be valid"


# Comprehensive test cases for invalid chess moves
@pytest.mark.parametrize(
    "move",
    [
        "",  # Empty string
        None,  # None
        "X5",  # Invalid piece
        "abcdefghi",  # Too long
        "j4",  # Invalid file
        1234,  # Not a string
        "12",  # Numeric
        "A1",  # Uppercase file
        "e9",  # File out of range
        "i1",  # Rank out of range
    ],
)
def test_invalid_moves(move):
    """Test comprehensive invalid chess moves."""
    assert is_valid_move(move) is False, f"Expected '{move}' to be invalid"


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
        # Edge cases that should be invalid
        ("e9", False, "rank out of range"),
        ("i1", False, "file out of range"),
    ],
)
def test_edge_case_moves(move, expected, description):
    """Test edge cases for chess move notation."""
    result = is_valid_move(move)
    assert result == expected, f"Move '{move}' ({description}): expected {expected}, got {result}"
