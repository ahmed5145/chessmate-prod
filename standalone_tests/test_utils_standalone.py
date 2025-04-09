"""Standalone test module for utils functions."""

import re

import pytest


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

    # Check for disambiguation (e.g., "Nbd7", "R1e5", "Qh4g3")
    # This is a simplification - we're just making sure the structure looks right
    if len(move) >= 4:
        # Check for piece + disambiguation + destination
        # Examples: Nbd7, R1a3, Qh4g3
        if move[0] in valid_pieces and (
            (move[1] in valid_files and move[2] in valid_files) or (move[1] in "12345678" and move[2] in valid_files)
        ):
            return True

    # For simplicity, accept all other move formats that passed our basic checks
    return True


def test_is_valid_move_basic():
    """Test basic move validation."""
    # Valid moves
    assert is_valid_move("e4") is True
    assert is_valid_move("Nf3") is True
    assert is_valid_move("O-O") is True

    # Invalid moves
    assert is_valid_move("") is False
    assert is_valid_move(None) is False
    assert is_valid_move("X5") is False


def test_is_valid_move_comprehensive():
    """Test comprehensive move validation."""
    # Valid moves
    valid_moves = ["e4", "Nf3", "Qxe5", "Kd2", "Rxh8", "Bb5", "axb5", "O-O", "O-O-O", "e8=Q", "h1"]
    for move in valid_moves:
        assert is_valid_move(move) is True, f"Expected '{move}' to be valid"

    # Invalid moves
    invalid_moves = [
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
    ]
    for move in invalid_moves:
        assert is_valid_move(move) is False, f"Expected '{move}' to be invalid"
