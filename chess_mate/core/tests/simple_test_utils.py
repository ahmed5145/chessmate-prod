"""Simple tests for utils module that don't require Django."""

import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.utils import is_valid_move


def test_is_valid_move_basic():
    """Basic tests for the is_valid_move function."""
    # Valid moves
    assert is_valid_move("e4") is True
    assert is_valid_move("Nf3") is True
    assert is_valid_move("O-O") is True

    # Invalid moves
    assert is_valid_move("") is False
    assert is_valid_move(None) is False
    assert is_valid_move("X5") is False
