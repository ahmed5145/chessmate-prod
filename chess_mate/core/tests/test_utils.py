"""Tests for core.utils module."""

from unittest import TestCase

import pytest
from core.utils import is_valid_move


class TestChessUtils(TestCase):
    """Test suite for chess utility functions."""

    def test_is_valid_move_valid_inputs(self):
        """Test is_valid_move with valid chess moves."""
        valid_moves = ["e4", "Nf3", "Qxe5", "Kd2", "Rxh8", "Bb5", "axb5", "O-O", "O-O-O"]
        for move in valid_moves:
            self.assertTrue(is_valid_move(move), f"Expected '{move}' to be valid")

    def test_is_valid_move_invalid_inputs(self):
        """Test is_valid_move with invalid inputs."""
        invalid_moves = [
            "",  # Empty string
            None,  # None
            "X5",  # Invalid piece
            "abcdefghi",  # Too long
            "j4",  # Invalid file
            1234,  # Not a string
            "12",  # Numeric
            "A1",  # Uppercase file
        ]
        for move in invalid_moves:
            self.assertFalse(is_valid_move(move), f"Expected '{move}' to be invalid")

    def test_is_valid_move_edge_cases(self):
        """Test is_valid_move with edge cases."""
        # Edge cases that should be valid
        self.assertTrue(is_valid_move("e8=Q"), "Promotion should be valid")
        self.assertTrue(is_valid_move("h1"), "Corner move should be valid")

        # Edge cases that should be invalid
        self.assertFalse(is_valid_move("e9"), "File out of range should be invalid")
        self.assertFalse(is_valid_move("i1"), "Rank out of range should be invalid")
