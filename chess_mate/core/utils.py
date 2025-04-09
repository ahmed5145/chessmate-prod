import chess
import chess.engine
import chess.pgn
from django.conf import settings
from django.http import JsonResponse


def generate_feedback_without_ai(analysis_data, stats):
    """
    Generate structured feedback without using AI.

    Args:
        analysis_data (dict): Analysis data from the game
        stats (dict): Statistics about the game

    Returns:
        str: Formatted feedback string
    """
    template = """
Opening Analysis:
• Based on your opening moves, {opening_feedback}
• Key suggestion: {opening_suggestion}

Middlegame Strategy:
• Your positional play shows {middlegame_feedback}
• Focus areas: {middlegame_areas}

Tactical Awareness:
• Statistics show {tactical_feedback}
• Recommendation: {tactical_suggestion}

Time Management:
• Analysis indicates {time_feedback}
• Key improvement: {time_suggestion}

Endgame Technique:
• Your endgame play {endgame_feedback}
• Practice suggestion: {endgame_suggestion}
"""

    # Opening feedback
    if stats["common_mistakes"].get("mistakes", 0) > 1:
        opening_feedback = "you might benefit from deeper opening preparation"
        opening_suggestion = "study the main lines of your chosen openings"
    else:
        opening_feedback = "you have a good grasp of opening principles"
        opening_suggestion = "consider expanding your opening repertoire"

    # Middlegame feedback
    if stats.get("average_accuracy", 0) < 70:
        middlegame_feedback = "room for improvement in positional understanding"
        middlegame_areas = "piece coordination and pawn structure management"
    else:
        middlegame_feedback = "good strategic understanding"
        middlegame_areas = "complex position evaluation and long-term planning"

    # Tactical feedback
    blunders = stats["common_mistakes"].get("blunders", 0)
    if blunders > 0.5:
        tactical_feedback = f"an average of {blunders:.1f} blunders per game"
        tactical_suggestion = "practice tactical puzzles daily"
    else:
        tactical_feedback = "good tactical awareness"
        tactical_suggestion = "work on finding more advanced tactical opportunities"

    # Time management
    time_pressure = stats["common_mistakes"].get("time_pressure", 0)
    if time_pressure > 0.3:
        time_feedback = "you often get into time trouble"
        time_suggestion = "practice better time allocation in the opening and middlegame"
    else:
        time_feedback = "generally good time management"
        time_suggestion = "fine-tune your time usage in critical positions"

    # Endgame feedback
    if stats.get("average_accuracy", 0) > 80:
        endgame_feedback = "shows strong technical understanding"
        endgame_suggestion = "study more complex endgame positions"
    else:
        endgame_feedback = "could benefit from more practice"
        endgame_suggestion = "focus on basic endgame principles and common patterns"

    return template.format(
        opening_feedback=opening_feedback,
        opening_suggestion=opening_suggestion,
        middlegame_feedback=middlegame_feedback,
        middlegame_areas=middlegame_areas,
        tactical_feedback=tactical_feedback,
        tactical_suggestion=tactical_suggestion,
        time_feedback=time_feedback,
        time_suggestion=time_suggestion,
        endgame_feedback=endgame_feedback,
        endgame_suggestion=endgame_suggestion,
    )


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
    if len(move) < 2 or len(move) > 7:
        return False

    # Handle castling
    if move in ["O-O", "O-O-O"]:
        return True

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

    # Check for promotion format (e.g., "e8=Q")
    if "=" in move:
        parts = move.split("=")
        if len(parts) != 2 or parts[1] not in valid_pieces:
            return False

    return True
