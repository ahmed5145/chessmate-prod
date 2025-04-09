"""Simple test for utils module."""

import pytest

from chess_mate.core.utils import is_valid_move


def test_is_valid_move():
    """Test the is_valid_move function."""
    # Valid moves
    assert is_valid_move("e4") is True
    assert is_valid_move("Nf3") is True
    assert is_valid_move("Qxe5") is True

    # Invalid moves
    assert is_valid_move("") is False
    assert is_valid_move(None) is False
    assert is_valid_move("X5") is False
    assert is_valid_move("abcdefghi") is False
