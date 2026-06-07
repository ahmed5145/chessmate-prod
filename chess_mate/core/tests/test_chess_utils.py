"""Tests for core.chess_utils PGN validation and metadata extraction."""

from core.chess_utils import extract_metadata_from_pgn, validate_pgn

VALID_PGN = """[Event "Test Game"]
[Date "2025.01.01"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]
[ECO "C50"]
[Opening "Italian Game"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 1-0
"""

SHORT_OPENING_PGN = """[Event "Mini"]
[Date "2025.01.02"]
[White "A"]
[Black "B"]
[Result "1-0"]

1. e4 e5 2. Nf3 1-0
"""

MIDDLEGAME_PGN = """[Event "Middlegame"]
[Date "2025.01.03"]
[White "A"]
[Black "B"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5
"""

ENDGAME_PGN = """[Event "Endgame"]
[Date "2025.01.04"]
[White "A"]
[Black "B"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O
9. h3 Nb8 10. d4 Nbd7 11. c4 c6 12. Nc3 Bb7 13. Bg5 b4 14. Nb1 h6 15. Bh4 c5
16. dxe5 dxe5 17. Nbd2 Qc7 18. Bg3 Rfd8 19. Qe2 Bc8 20. Rad1 Qb7 21. Nh4 Qc7
22. Qe3 Qb7 23. Nhf3 Qc7 24. Qe2 Qb7 25. Nh4 Qc7
"""


def test_validate_pgn_rejects_empty_or_non_string():
    assert validate_pgn("") == (False, "PGN is empty or not a string")
    assert validate_pgn(None) == (False, "PGN is empty or not a string")


def test_validate_pgn_rejects_too_short_input():
    assert validate_pgn("short") == (False, "PGN is too short")


def test_validate_pgn_accepts_minimal_valid_game():
    is_valid, error = validate_pgn(VALID_PGN)
    assert is_valid is True
    assert error is None


def test_validate_pgn_rejects_game_without_moves():
    headers_only = """[Event "X"]
[Date "2025.01.01"]
[White "A"]
[Black "B"]
[Result "*"]

"""
    is_valid, error = validate_pgn(headers_only)
    assert is_valid is False
    assert "no moves" in error.lower()


def test_extract_metadata_from_pgn_populates_headers_and_phase():
    metadata = extract_metadata_from_pgn(VALID_PGN)
    assert metadata["white"] == "Alice"
    assert metadata["black"] == "Bob"
    assert metadata["eco"] == "C50"
    assert metadata["opening"] == "Italian Game"
    assert metadata["ply_count"] > 0
    assert metadata["phase"] == "opening"


def test_extract_metadata_opening_middlegame_endgame_thresholds():
    opening = extract_metadata_from_pgn(SHORT_OPENING_PGN)
    assert opening["phase"] == "opening"

    middlegame = extract_metadata_from_pgn(MIDDLEGAME_PGN)
    assert middlegame["phase"] == "middlegame"

    endgame = extract_metadata_from_pgn(ENDGAME_PGN)
    assert endgame["phase"] == "endgame"


def test_extract_metadata_returns_defaults_for_empty_pgn():
    metadata = extract_metadata_from_pgn("")
    assert metadata["white"] is None
    assert metadata["ply_count"] == 0
    assert "phase" not in metadata
