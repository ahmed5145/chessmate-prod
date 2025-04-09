"""Test utility functions."""


def is_valid_move(move):
    """Check if a move is valid in algebraic notation."""
    if not move or not isinstance(move, str):
        return False

    # Basic validation for algebraic notation
    if len(move) < 2 or len(move) > 7:
        return False

    # Check first character is a piece or file
    valid_first_chars = {"K", "Q", "R", "B", "N", "a", "b", "c", "d", "e", "f", "g", "h"}
    if move[0] not in valid_first_chars:
        return False

    return True


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
