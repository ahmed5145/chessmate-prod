"""
Build per-game Stockfish result schema (PRD section 11).
This module calls existing `StockfishAnalyzer` and `MetricsCalculator` and
assembles the exact per-game schema required by the PRD.
"""

import json
import logging
import os
from typing import Any, Dict, List

import chess

from ..eco_codes import get_opening_name
from .explanation_templates import get_explanation
from .metrics_calculator import MetricsCalculator
from .stockfish_analyzer import StockfishAnalyzer

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ECO_PATH = os.path.join(DATA_DIR, "eco_openings.json")


def _load_eco_openings() -> Dict[str, str]:
    try:
        with open(ECO_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        logger.warning("ECO openings data not available or unreadable; continuing with empty map")
        return {}


_ECO_MAP = _load_eco_openings()


def _detect_opening_name_from_pgn(pgn: str) -> (str, float):
    """Heuristic: match the longest prefix of the PGN moves against ECO map.
    Return (opening_name, opening_accuracy_placeholder).

    Opening accuracy is computed later; here we return name and placeholder 0.0.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn)) if "io" in globals() else None
    except Exception:
        game = None

    # Fallback: build SAN-like prefix from PGN string
    moves_str = " ".join(pgn.split())[:500]

    # Try match longest prefix in ECO map
    for length in range(10, 0, -1):
        # build prefix of first `length` tokens
        tokens = moves_str.split()
        if len(tokens) < length:
            continue
        prefix = " ".join(tokens[:length])
        if prefix in _ECO_MAP:
            code = _ECO_MAP[prefix]
            return get_opening_name(code), 0.0

    return "Unknown", 0.0


import io


def build_game_result(pgn: str, game_id: str = None, depth: int = None) -> Dict[str, Any]:
    """Produce the per-game result JSON object as defined in PRD section 11.

    Args:
        pgn: game PGN text
        game_id: optional identifier to include in result

    Returns:
        Dict matching the required per-game schema
    """
    analyzer = StockfishAnalyzer.get_instance()
    if depth is None:
        depth = int(os.environ.get("BATCH_ANALYSIS_DEPTH", os.environ.get("STOCKFISH_DEPTH", "20")))

    # Analyze game (per-move). Use analyze_position directly to avoid
    # incompatible keyword arguments in some analyzer versions.
    analyzed_moves = []
    try:
        reader = io.StringIO(pgn)
        game = chess.pgn.read_game(reader)
        board = game.board() if game else chess.Board()
        for i, move in enumerate(game.mainline_moves() if game else []):
            is_white = board.turn
            result = analyzer.analyze_position(board, depth=depth)

            # Record SAN and FEN before making the move
            try:
                san = board.san(move)
            except Exception:
                san = move.uci()
            uci = move.uci()
            fen_before = board.fen()

            # Execute the move
            board.push(move)

            # Store the analysis similar to analyzer.analyze_game
            analyzed_move = {
                "move_number": i // 2 + 1,
                "move": uci,
                "san": san,
                "is_white": is_white,
                "fen": result.get("fen", fen_before),
                "position_score": result.get("score", 0.0),
                "evaluation": result.get("score", 0.0),
                "best_move": (result.get("pv") and result.get("pv")[0]) or "",
                "best_line": result.get("pv", [])[:5] if result.get("pv") else [],
                "depth": result.get("depth", 0),
                "time": result.get("time", 0.0),
            }
            if "centipawn_loss" in result:
                analyzed_move["centipawn_loss"] = result["centipawn_loss"]
            if "classification" in result:
                analyzed_move["classification"] = result["classification"]

            analyzed_moves.append(analyzed_move)
    except Exception as e:
        logger.error(f"Failed to analyze game via analyze_position loop: {e}")
        # Return complete schema-compliant dict with analysis_failed flag
        # Do NOT try to compute phase_breakdown with empty analyzed_moves
        # Instead, return early with all zeros and failed marker
        return {
            "game_id": game_id,
            "total_moves": 0,
            "result": "",
            "player_color": "white",
            "opening_name": "Unknown",
            "opening_accuracy": 0.0,
            "phase_breakdown": {
                "opening": {
                    "moves": 0,
                    "avg_eval_drop": 0.0,
                    "blunders": 0,
                    "mistakes": 0,
                },
                "middlegame": {
                    "moves": 0,
                    "avg_eval_drop": 0.0,
                    "blunders": 0,
                    "mistakes": 0,
                },
                "endgame": {
                    "moves": 0,
                    "avg_eval_drop": 0.0,
                    "blunders": 0,
                    "mistakes": 0,
                },
            },
            "move_quality": {
                "brilliant": 0,
                "best": 0,
                "excellent": 0,
                "good": 0,
                "inaccuracy": 0,
                "mistake": 0,
                "blunder": 0,
            },
            "critical_moments": [],
            "tactical_patterns_missed": [],
            "analysis_failed": True,
        }

    # Calculate metrics
    metrics = MetricsCalculator.calculate_game_metrics(analyzed_moves, [])

    metadata = metrics.get("metadata", {})
    total_moves = metadata.get("total_moves", len(analyzed_moves))

    # Extract opening name from ECO header tag (present in chess.com/lichess imports)
    opening_name = "Unknown"
    try:
        pgn_io = io.StringIO(pgn)
        pgn_game = chess.pgn.read_game(pgn_io)
        if pgn_game:
            eco_code = pgn_game.headers.get("ECO", "")
            if eco_code:
                opening_name = get_opening_name(eco_code) or "Unknown"
    except Exception:
        pass

    # Compute opening_accuracy: percentage of opening-phase moves that match engine top-3
    opening_length = int(metadata.get("opening_length", 0))
    opening_matches = 0
    opening_evaluated = 0

    for i, mv in enumerate(analyzed_moves[:opening_length]):
        best_line = mv.get("best_line") or []
        if not best_line:
            continue
        # compare UCI strings
        played = mv.get("move")
        top3 = [b for b in best_line[:3]]
        if played in top3:
            opening_matches += 1
        opening_evaluated += 1

    opening_accuracy = (opening_matches / opening_evaluated) if opening_evaluated > 0 else None

    # Compute avg_eval_drop per phase by scanning moves
    # Build per-move eval_before using position_score and approximate eval_after by next move's position_score
    eval_befores = [m.get("position_score", 0.0) for m in analyzed_moves]
    eval_afters = [
        eval_befores[i + 1] if i + 1 < len(eval_befores) else eval_befores[i] for i in range(len(eval_befores))
    ]
    eval_drops = [max(0.0, eval_befores[i] - eval_afters[i]) for i in range(len(eval_befores))]

    # Determine phase boundaries (in move indices, not half-moves)
    opening_end = int(metadata.get("opening_length", 0))
    middlegame_end = int(metadata.get("middlegame_length", opening_end))

    # Clamp boundaries to total moves to ensure no moves are double-counted
    opening_end = min(opening_end, len(analyzed_moves))
    middlegame_end = min(middlegame_end, len(analyzed_moves))

    def _avg_drop_for_slice(start: int, end: int) -> float:
        if end <= start:
            return 0.0
        slice_vals = eval_drops[start:end]
        return float(sum(slice_vals) / len(slice_vals)) if slice_vals else 0.0

    # Initialize phase_breakdown with zeros (will be filled during classification pass)
    phase_breakdown = {
        "opening": {
            "moves": 0,
            "avg_eval_drop": _avg_drop_for_slice(0, opening_end),
            "blunders": 0,
            "mistakes": 0,
        },
        "middlegame": {
            "moves": 0,
            "avg_eval_drop": _avg_drop_for_slice(opening_end, middlegame_end),
            "blunders": 0,
            "mistakes": 0,
        },
        "endgame": {
            "moves": 0,
            "avg_eval_drop": _avg_drop_for_slice(middlegame_end, len(analyzed_moves)),
            "blunders": 0,
            "mistakes": 0,
        },
    }

    # Initialize move_quality counters
    mq_keys = [
        "brilliant",
        "best",
        "excellent",
        "good",
        "inaccuracy",
        "mistake",
        "blunder",
    ]
    move_quality_out = {k: 0 for k in mq_keys}

    # Compute move classifications and deteriorations in a single pass
    # This ensures move_quality and critical_moments use the same logic
    move_classifications = {}  # idx -> classification string
    move_deteriorations = {}  # idx -> positive float (magnitude of deterioration)
    has_mate = {}  # idx -> bool (mate score detected)

    for i in range(len(analyzed_moves)):
        eval_before = float(eval_befores[i])
        eval_after = float(eval_afters[i])

        # Detect and cap mate scores (very high eval values like 100.0 or mate objects)
        is_mate_before = False
        is_mate_after = False
        if eval_before >= 10.0:
            is_mate_before = True
            eval_before = 10.0
        if eval_after >= 10.0:
            is_mate_after = True
            eval_after = 10.0

        eval_befores[i] = eval_before
        eval_afters[i] = eval_after
        has_mate[i] = is_mate_before or is_mate_after

        # Compute deterioration: positive means position got worse
        # If eval_after < eval_before, position deteriorated by that amount
        if eval_after < eval_before:
            deterioration = eval_before - eval_after
        else:
            # Position improved or stayed same; not a critical move
            deterioration = 0.0

        move_deteriorations[i] = deterioration

        # Classify based on deterioration thresholds
        if deterioration >= 1.5:
            classification = "blunder"
        elif deterioration >= 0.5:
            classification = "mistake"
        elif deterioration >= 0.2:
            classification = "inaccuracy"
        else:
            classification = "good"

        move_classifications[i] = classification

        # Determine which phase this move belongs to
        if i < opening_end:
            phase = "opening"
        elif i < middlegame_end:
            phase = "middlegame"
        else:
            phase = "endgame"

        # Increment both move_quality and phase_breakdown counters together
        move_quality_out[classification] += 1
        phase_breakdown[phase]["moves"] += 1
        if classification == "blunder":
            phase_breakdown[phase]["blunders"] += 1
        elif classification == "mistake":
            phase_breakdown[phase]["mistakes"] += 1

    # Critical moments: top 3 worst moves by deterioration (only >= 0.2 threshold)
    critical_moves_candidates = [
        (idx, move_deteriorations[idx]) for idx in range(len(analyzed_moves)) if move_deteriorations[idx] >= 0.2
    ]
    # Sort by deterioration (descending)
    critical_moves_candidates.sort(key=lambda x: x[1], reverse=True)
    # Take top 3 (not padded with trivial moves)
    selected_indices = [idx for idx, _ in critical_moves_candidates[:3]]

    critical_moments = []
    for idx in selected_indices:
        mv = analyzed_moves[idx]
        move_number = mv.get("move_number")
        # Determine phase for this move
        if idx < opening_end:
            phase = "opening"
        elif idx < middlegame_end:
            phase = "middlegame"
        else:
            phase = "endgame"

        eval_before = float(eval_befores[idx])
        eval_after = float(eval_afters[idx])
        # eval_swing is positive magnitude of deterioration
        eval_swing = move_deteriorations[idx]

        fen = mv.get("fen") or ""
        played_move = mv.get("san") or mv.get("move")
        best_move = mv.get("best_move") or (
            mv.get("best_line") and mv.get("best_line")[0] if mv.get("best_line") else ""
        )

        # Determine tactical theme using heuristics
        try:
            board_before = chess.Board(fen) if fen else None
        except Exception:
            board_before = None

        tactical_theme = "missed_tactic"
        explanation = ""
        if board_before is not None:
            try:
                uci = mv.get("move")
                move_obj = chess.Move.from_uci(uci) if uci else None
                board_after = board_before.copy()
                if move_obj:
                    board_after.push(move_obj)

                # heuristic fork detection: any opponent piece attacking >=2 of our high-value pieces
                opponent_color = not board_after.turn
                attacked_counts = 0
                for sq in chess.SQUARES:
                    piece = board_after.piece_at(sq)
                    if piece and piece.color == opponent_color:
                        # count how many of our pieces this piece attacks
                        attacked = 0
                        for target_sq in chess.SQUARES:
                            target_piece = board_after.piece_at(target_sq)
                            if target_piece and target_piece.color == (not opponent_color):
                                if board_after.is_attacked_by(opponent_color, target_sq):
                                    attacked += 1
                        if attacked >= 2:
                            tactical_theme = "fork"
                            break

                # pin detection
                if tactical_theme == "missed_tactic":
                    for sq in chess.SQUARES:
                        piece = board_after.piece_at(sq)
                        if piece and piece.color == board_after.turn:
                            try:
                                if board_after.is_pinned(board_after.turn, sq):
                                    tactical_theme = "pin"
                                    break
                            except Exception:
                                continue

                # skewer detection: find sliding attacks on high-value piece with lesser piece behind
                if tactical_theme == "missed_tactic":
                    for sq in chess.SQUARES:
                        piece = board_after.piece_at(sq)
                        if (
                            piece
                            and piece.color == (not board_after.turn)
                            and piece.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN]
                        ):
                            # check rays
                            for dir_sq in chess.SQUARES:
                                # naive: skip complex ray logic; check if this attacker attacks a queen and behind is rook
                                pass
                    # fallback: detect hanging piece
                if tactical_theme == "missed_tactic":
                    # detect hanging: moved-to square attacked and not defended
                    if move_obj:
                        to_sq = move_obj.to_square
                        if board_after.is_attacked_by(not board_after.turn, to_sq) and not board_after.is_attacked_by(
                            board_after.turn, to_sq
                        ):
                            tactical_theme = "hanging_piece"

            except Exception:
                tactical_theme = "missed_tactic"

        # generate explanation via template
        explanation = get_explanation(
            tactical_theme,
            played_move,
            best_move,
            {
                "lost_piece_name": mv.get("captured_piece_name", "piece"),
                "attacking_piece_name": "opponent piece",
                "pinned_piece_name": mv.get("captured_piece_name", "piece"),
                "valuable_piece_name": "your queen",
                "less_valuable_piece_name": "a rook",
                "eval_difference": abs(eval_swing),
            },
        )

        moment = {
            "move_number": move_number,
            "phase": phase,
            "type": move_classifications[idx],
            "eval_before": eval_before,
            "eval_after": eval_after,
            "eval_swing": eval_swing,
            "fen": fen,
            "played_move": played_move,
            "best_move": best_move,
            "tactical_theme": tactical_theme,
            "explanation": explanation,
        }
        # Add is_mate flag if mate was detected in eval scores
        if has_mate.get(idx, False):
            moment["is_mate"] = True
        critical_moments.append(moment)

    # tactical_patterns_missed: unique tactical themes from critical moments
    tactical_patterns = list({cm.get("tactical_theme", "missed_tactic") for cm in critical_moments})

    result = {
        "game_id": game_id,
        "total_moves": total_moves,
        "result": "",
        "player_color": "white",
        "opening_name": opening_name,
        "opening_accuracy": opening_accuracy,
        "phase_breakdown": phase_breakdown,
        "move_quality": move_quality_out,
        "critical_moments": critical_moments,
        "tactical_patterns_missed": tactical_patterns,
    }

    # fill result.result and player_color from PGN header if available
    # Also extract WhiteElo and BlackElo for rating derivation
    white_elo = None
    black_elo = None
    try:
        reader = io.StringIO(pgn)
        game = chess.pgn.read_game(reader)
        if game:
            result["result"] = game.headers.get("Result", "")
            # determine player's color as white by default
            result["player_color"] = "white"
            # Extract ELO ratings from headers
            try:
                white_elo_str = game.headers.get("WhiteElo")
                white_elo = int(white_elo_str) if white_elo_str else None
            except (ValueError, TypeError):
                white_elo = None
            try:
                black_elo_str = game.headers.get("BlackElo")
                black_elo = int(black_elo_str) if black_elo_str else None
            except (ValueError, TypeError):
                black_elo = None
    except Exception:
        pass

    # Add ELO ratings to result
    result["white_elo"] = white_elo
    result["black_elo"] = black_elo

    return result
