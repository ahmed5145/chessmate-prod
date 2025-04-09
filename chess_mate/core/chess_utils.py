"""
Utility functions for chess-related operations.
"""

import io
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import chess.pgn

logger = logging.getLogger(__name__)


def validate_pgn(pgn_text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a string is a properly formatted PGN (Portable Game Notation).

    Args:
        pgn_text: String containing the PGN to validate

    Returns:
        Tuple of (is_valid, error_message) where is_valid is a boolean and
        error_message is None if valid or an error string if invalid
    """
    if not pgn_text or not isinstance(pgn_text, str):
        return False, "PGN is empty or not a string"

    # Check for minimum PGN requirements
    if len(pgn_text) < 10:
        return False, "PGN is too short"

    # Try to parse the PGN using chess.pgn
    try:
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)

        if game is None:
            return False, "Failed to parse PGN"

        # Check for minimum required headers
        required_headers = ["Event", "Date", "White", "Black", "Result"]
        missing_headers = [h for h in required_headers if h not in game.headers]

        if missing_headers:
            return False, f"Missing required headers: {', '.join(missing_headers)}"

        # Check if game has moves
        if not game.variations:
            return False, "PGN contains no moves"

        return True, None
    except Exception as e:
        logger.error(f"Error validating PGN: {str(e)}")
        return False, f"Invalid PGN format: {str(e)}"


def extract_metadata_from_pgn(pgn_text: str) -> Dict[str, Any]:
    """
    Extract metadata from a PGN string.

    Args:
        pgn_text: String containing the PGN

    Returns:
        Dictionary with game metadata
    """
    metadata = {
        "event": None,
        "date": None,
        "white": None,
        "black": None,
        "result": None,
        "white_elo": None,
        "black_elo": None,
        "eco": None,
        "opening": None,
        "time_control": None,
        "termination": None,
        "site": None,
        "round": None,
        "ply_count": 0,
    }

    try:
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)

        if game is None:
            return metadata

        # Extract headers
        headers = game.headers
        metadata["event"] = headers.get("Event")
        metadata["date"] = headers.get("Date")
        metadata["white"] = headers.get("White")
        metadata["black"] = headers.get("Black")
        metadata["result"] = headers.get("Result")
        metadata["white_elo"] = headers.get("WhiteElo")
        metadata["black_elo"] = headers.get("BlackElo")
        metadata["eco"] = headers.get("ECO")
        metadata["opening"] = headers.get("Opening")
        metadata["time_control"] = headers.get("TimeControl")
        metadata["termination"] = headers.get("Termination")
        metadata["site"] = headers.get("Site")
        metadata["round"] = headers.get("Round")

        # Count number of half-moves (ply)
        ply_count = 0
        current_node = game
        while current_node.variations:
            current_node = current_node.variations[0]
            ply_count += 1

        metadata["ply_count"] = ply_count

        # Determine game phase based on ply count
        if ply_count <= 10:
            metadata["phase"] = "opening"
        elif ply_count <= 40:
            metadata["phase"] = "middlegame"
        else:
            metadata["phase"] = "endgame"

        return metadata
    except Exception as e:
        logger.error(f"Error extracting PGN metadata: {str(e)}")
        return metadata
