"""
Template-based move explanation generator for tactical themes.

Generates human-readable explanations for chess moves based on tactical patterns,
without AI calls. Used for per-move explanations in the batch analysis report.

Tactical themes supported:
- hanging_piece: An undefended piece was lost
- fork: Multiple pieces attacked simultaneously
- pin: Piece cannot move without exposing more valuable piece
- skewer: Valuable piece forced to move, revealing less valuable piece behind it
- missed_tactic: Catchall for any unclassified tactical theme or fallback

Each template function accepts:
  - played_move: The move that was played (e.g., "Nxd5")
  - best_move: The engine's best move alternative (e.g., "Rd1")
  - context: Dict with board state info (piece_names, squares, etc.)

Returns a concise, actionable explanation string.
"""


def _explain_hanging_piece(played_move: str, best_move: str, context: dict) -> str:
    """Explain a hanging piece (undefended piece loss)."""
    attacking_piece = context.get("attacking_piece_name", "The opponent's piece")
    lost_piece = context.get("lost_piece_name", "a piece")
    defending_move = best_move

    return (
        f"You played {played_move}, leaving {lost_piece} undefended. "
        f"{attacking_piece} captured it on the next move. "
        f"{defending_move} would have protected your piece or created a counter-threat."
    )


def _explain_fork(played_move: str, best_move: str, context: dict) -> str:
    """Explain a missed fork (attacking multiple pieces)."""
    your_piece = context.get("your_piece_name", "a piece")
    targeted_pieces = context.get("targeted_pieces", "two pieces")

    return (
        f"After {played_move}, you missed {best_move}, which forks "
        f"{targeted_pieces} simultaneously. Your opponent can then defend both, "
        f"but forks win material because one piece must be sacrificed."
    )


def _explain_pin(played_move: str, best_move: str, context: dict) -> str:
    """Explain a pinned piece (cannot move without exposing more valuable piece)."""
    pinned_piece = context.get("pinned_piece_name", "a piece")
    valuable_piece = context.get("valuable_piece_name", "your queen")
    pin_direction = context.get("pin_direction", "")

    return (
        f"After {played_move}, {pinned_piece} is pinned to {valuable_piece} "
        f"along the {pin_direction}. "
        f"{best_move} unpins the piece or removes the attacking piece, "
        f"restoring full mobility."
    )


def _explain_skewer(played_move: str, best_move: str, context: dict) -> str:
    """Explain a skewer (valuable piece forced to move, revealing less valuable piece)."""
    valuable_piece = context.get("valuable_piece_name", "your queen")
    less_valuable = context.get("less_valuable_piece_name", "a rook")

    return (
        f"After {played_move}, you missed {best_move}, which is a skewer: "
        f"it attacks {valuable_piece} first, forcing it to move and exposing "
        f"{less_valuable} for capture. Compared to a fork, the order of value is reversed."
    )


def _format_eval_difference(value) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "a stronger evaluation"
    return f"a {numeric:.2f}-pawn advantage"


def _explain_missed_tactic(played_move: str, best_move: str, context: dict) -> str:
    """Fallback explanation for unclassified tactical themes."""
    position_evaluation = _format_eval_difference(context.get("eval_difference"))

    return (
        f"After {played_move}, the position deteriorated. "
        f"{best_move} was stronger and would have maintained {position_evaluation}. "
        f"Look for forcing moves (checks, captures, threats) in tactical positions."
    )


# Dispatch table: tactical_theme -> explanation function
_THEME_HANDLERS = {
    "hanging_piece": _explain_hanging_piece,
    "fork": _explain_fork,
    "pin": _explain_pin,
    "skewer": _explain_skewer,
    "missed_tactic": _explain_missed_tactic,
}


def get_explanation(tactical_theme: str, played_move: str, best_move: str, context: dict) -> str:
    """
    Generate a human-readable explanation for a chess move based on tactical theme.

    Args:
        tactical_theme: The tactical classification (e.g., "hanging_piece", "fork")
        played_move: The move that was played (e.g., "Nxd5")
        best_move: The engine's best move recommendation (e.g., "Rd1")
        context: Dict with board state information:
                 - piece_names: Names of pieces involved
                 - squares: Board coordinates
                 - eval_difference: Evaluation swing in pawns
                 - Other theme-specific fields

    Returns:
        A concise, actionable explanation string in English.
        If tactical_theme is unrecognized, returns missed_tactic fallback.
    """
    handler = _THEME_HANDLERS.get(tactical_theme, _explain_missed_tactic)
    return handler(played_move, best_move, context)
