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
from .batch_metrics import (
    compute_game_accuracy,
    compute_game_acpl,
    compute_phase_accuracy,
)
from .batch_move_classification import (
    CRITICAL_MOMENT_MIN_PAWNS,
    classify_deterioration,
    is_delivered_checkmate,
    player_eval_deterioration,
    player_has_winning_mate,
)
from .batch_pgn_metadata import extract_platform_metadata_from_pgn
from .batch_pgn_time import compute_time_management_from_pgn
from .batch_phase_boundaries import (
    endgame_start_from_metadata,
    normalize_phase_boundaries,
    phase_for_half_move_index,
)
from .explanation_templates import get_explanation
from .metrics_calculator import MetricsCalculator
from .moment_insights import classify_endgame_material, classify_tactical_theme
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


def infer_player_color_from_headers(
    white: str,
    black: str,
    *,
    chess_com_username: str = "",
    lichess_username: str = "",
) -> str:
    """Match PGN player names to linked platform usernames; default white."""
    for username in (chess_com_username, lichess_username):
        name = (username or "").strip()
        if not name:
            continue
        if white and white.strip().lower() == name.lower():
            return "white"
        if black and black.strip().lower() == name.lower():
            return "black"
    return "white"


def _resolve_player_color_from_pgn(
    pgn: str,
    *,
    chess_com_username: str = "",
    lichess_username: str = "",
) -> str:
    """Infer which side the user played before classifying moves."""
    try:
        reader = io.StringIO(pgn)
        game = chess.pgn.read_game(reader)
        if game:
            return infer_player_color_from_headers(
                game.headers.get("White", ""),
                game.headers.get("Black", ""),
                chess_com_username=chess_com_username,
                lichess_username=lichess_username,
            )
    except Exception:
        pass
    return "white"


def build_game_result(
    pgn: str,
    game_id: str = None,
    depth: int = None,
    *,
    saved_game_id: int | None = None,
    chess_com_username: str = "",
    lichess_username: str = "",
) -> Dict[str, Any]:
    """Produce the per-game result JSON object as defined in PRD section 11.

    Args:
        pgn: game PGN text
        game_id: optional identifier to include in result
        saved_game_id: ChessMate Game PK when batch was built from saved games
        chess_com_username: profile username for color inference
        lichess_username: profile username for color inference

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
            is_white = board.turn == chess.WHITE
            result_before = analyzer.analyze_position(board, depth=depth)
            eval_before = float(result_before.get("score", 0.0))

            try:
                san = board.san(move)
            except Exception:
                san = move.uci()
            uci = move.uci()
            fen_before = board.fen()

            board.push(move)

            result_after = analyzer.analyze_position(board, depth=depth)
            eval_after = float(result_after.get("score", 0.0))

            analyzed_move = {
                "move_number": i // 2 + 1,
                "move": uci,
                "san": san,
                "is_white": is_white,
                "fen": fen_before,
                "position_score": eval_before,
                "evaluation": eval_before,
                "eval_before": eval_before,
                "eval_after": eval_after,
                "best_move": (result_before.get("pv") and result_before.get("pv")[0]) or "",
                "best_line": result_before.get("pv", [])[:5] if result_before.get("pv") else [],
                "depth": result_before.get("depth", 0),
                "time": result_before.get("time", 0.0),
            }
            if "centipawn_loss" in result_before:
                analyzed_move["centipawn_loss"] = result_before["centipawn_loss"]
            if "classification" in result_before:
                analyzed_move["classification"] = result_before["classification"]

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
    eco_code = None
    try:
        pgn_io = io.StringIO(pgn)
        pgn_game = chess.pgn.read_game(pgn_io)
        if pgn_game:
            raw_eco = (pgn_game.headers.get("ECO") or "").strip().upper()
            if raw_eco:
                eco_code = raw_eco[:3]
                opening_name = get_opening_name(eco_code) or "Unknown"
            opening_header = (pgn_game.headers.get("Opening") or "").strip()
            if opening_header and opening_header not in ("?", "Unknown"):
                from ..opening_name_utils import compact_opening_name

                opening_name = compact_opening_name(opening_header) or opening_header
    except Exception:
        pass

    # Compute opening_accuracy: percentage of opening-phase moves that match engine top-3
    player_color = _resolve_player_color_from_pgn(
        pgn,
        chess_com_username=chess_com_username,
        lichess_username=lichess_username,
    )
    player_is_white = player_color == "white"

    opening_length = int(metadata.get("opening_length", 0))
    opening_matches = 0
    opening_evaluated = 0

    for mv in analyzed_moves[:opening_length]:
        if bool(mv.get("is_white", True)) != player_is_white:
            continue
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

    # Per-move deterioration from true pre/post engine evals (White POV, player-relative)
    eval_befores = []
    eval_afters = []
    eval_drops = []
    for mv in analyzed_moves:
        before = float(mv.get("eval_before", mv.get("position_score", 0.0)))
        after = float(mv.get("eval_after", before))
        is_white = bool(mv.get("is_white", True))
        eval_befores.append(before)
        eval_afters.append(after)
        eval_drops.append(player_eval_deterioration(is_white, before, after))

    # Phase boundaries (half-move indices). middlegame_length in metadata is a COUNT, not end index.
    raw_opening_end = int(metadata.get("opening_length", 0) or 0)
    raw_endgame_start = endgame_start_from_metadata(metadata, len(analyzed_moves))
    opening_end, endgame_start = normalize_phase_boundaries(
        len(analyzed_moves),
        raw_opening_end,
        raw_endgame_start,
    )

    def _is_player_half_move_index(idx: int) -> bool:
        return bool(analyzed_moves[idx].get("is_white", True)) == player_is_white

    def _avg_drop_for_slice(start: int, end: int) -> float:
        if end <= start:
            return 0.0
        slice_vals = [
            eval_drops[i]
            for i in range(start, end)
            if _is_player_half_move_index(i)
        ]
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
            "avg_eval_drop": _avg_drop_for_slice(opening_end, endgame_start),
            "blunders": 0,
            "mistakes": 0,
        },
        "endgame": {
            "moves": 0,
            "avg_eval_drop": _avg_drop_for_slice(endgame_start, len(analyzed_moves)),
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
        mv = analyzed_moves[i]
        is_white = bool(mv.get("is_white", True))

        is_mate_before = eval_before >= 10.0 or eval_before <= -10.0
        is_mate_after = eval_after >= 10.0 or eval_after <= -10.0
        if eval_before >= 10.0:
            eval_before = 10.0
        elif eval_before <= -10.0:
            eval_before = -10.0
        if eval_after >= 10.0:
            eval_after = 10.0
        elif eval_after <= -10.0:
            eval_after = -10.0
        eval_befores[i] = eval_before
        eval_afters[i] = eval_after
        has_mate[i] = is_mate_before or is_mate_after

        played_san = mv.get("san") or ""
        if is_delivered_checkmate(played_san) or player_has_winning_mate(is_white, eval_after):
            deterioration = 0.0
            classification = "best"
        else:
            deterioration = player_eval_deterioration(is_white, eval_before, eval_after)
            classification = classify_deterioration(deterioration)
        move_deteriorations[i] = deterioration
        move_classifications[i] = classification

        phase = phase_for_half_move_index(i, opening_end, endgame_start)

        # Only count the user's moves — opponent errors matter only if the user failed to capitalize
        if not _is_player_half_move_index(i):
            continue

        move_quality_out[classification] += 1
        phase_breakdown[phase]["moves"] += 1
        if classification == "blunder":
            phase_breakdown[phase]["blunders"] += 1
        elif classification == "mistake":
            phase_breakdown[phase]["mistakes"] += 1

    # Critical moments: top 3 worst moves by deterioration (only >= 0.2 threshold)
    def _skip_critical_moment(idx: int) -> bool:
        mv = analyzed_moves[idx]
        san = mv.get("san") or mv.get("played_move") or ""
        is_white = bool(mv.get("is_white", True))
        eval_after = float(eval_afters[idx])
        if is_delivered_checkmate(san):
            return True
        if player_has_winning_mate(is_white, eval_after):
            return True
        return False

    critical_moves_candidates = [
        (idx, move_deteriorations[idx])
        for idx in range(len(analyzed_moves))
        if _is_player_half_move_index(idx)
        and move_deteriorations[idx] >= CRITICAL_MOMENT_MIN_PAWNS
        and not _skip_critical_moment(idx)
    ]
    # Sort by deterioration (descending)
    critical_moves_candidates.sort(key=lambda x: x[1], reverse=True)
    # Take top 3 (not padded with trivial moves)
    selected_indices = [idx for idx, _ in critical_moves_candidates[:3]]

    critical_moments = []
    for idx in selected_indices:
        mv = analyzed_moves[idx]
        move_number = mv.get("move_number")
        phase = phase_for_half_move_index(idx, opening_end, endgame_start)

        eval_before = float(eval_befores[idx])
        eval_after = float(eval_afters[idx])
        # eval_swing is positive magnitude of deterioration
        eval_swing = move_deteriorations[idx]

        fen = mv.get("fen") or ""
        played_move = mv.get("san") or mv.get("move")
        best_move = mv.get("best_move") or (
            mv.get("best_line") and mv.get("best_line")[0] if mv.get("best_line") else ""
        )

        played_uci = mv.get("move")
        best_uci = best_move if isinstance(best_move, str) else None
        if best_uci and hasattr(best_move, "uci"):
            best_uci = best_move.uci()

        if is_delivered_checkmate(played_move) or player_has_winning_mate(bool(mv.get("is_white", True)), eval_after):
            continue

        tactical_theme = classify_tactical_theme(fen, played_uci, best_uci, eval_swing=eval_swing)

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

        mover = "white" if bool(mv.get("is_white", True)) else "black"
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
            "mover": mover,
            "played_move_uci": played_uci if isinstance(played_uci, str) else None,
            "best_move_uci": best_uci if isinstance(best_uci, str) else None,
        }
        if phase == "endgame" and fen:
            moment["endgame_material"] = classify_endgame_material(fen)
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
        "player_color": player_color,
        "opening_name": opening_name,
        "eco_code": eco_code,
        "opening_accuracy": opening_accuracy,
        "acpl": compute_game_acpl(analyzed_moves, player_color),
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
            white_name = game.headers.get("White", "")
            black_name = game.headers.get("Black", "")
            result["player_color"] = infer_player_color_from_headers(
                white_name,
                black_name,
                chess_com_username=chess_com_username,
                lichess_username=lichess_username,
            )
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

    player_color = result.get("player_color", "white")
    player_moments = [
        moment for moment in critical_moments if moment.get("mover") == player_color
    ]
    result["critical_moments"] = player_moments
    result["tactical_patterns_missed"] = list(
        {cm.get("tactical_theme", "missed_tactic") for cm in player_moments}
    )
    result["accuracy"] = compute_game_accuracy(analyzed_moves, player_color)
    result["player_moves"] = len(
        [mv for mv in analyzed_moves if bool(mv.get("is_white", True)) == (player_color == "white")]
    )
    for phase_name, start, end in (
        ("opening", 0, opening_end),
        ("middlegame", opening_end, endgame_start),
        ("endgame", endgame_start, len(analyzed_moves)),
    ):
        phase_acc = compute_phase_accuracy(analyzed_moves, start, end, player_color)
        if phase_acc is not None:
            result["phase_breakdown"][phase_name]["accuracy"] = phase_acc

    if saved_game_id is not None:
        result["saved_game_id"] = saved_game_id

    critical_move_numbers = [
        int(m.get("move_number")) for m in player_moments if m.get("move_number") is not None
    ]
    time_management = compute_time_management_from_pgn(
        pgn,
        player_color,
        opening_end,
        endgame_start,
        critical_move_numbers=critical_move_numbers,
    )
    if time_management.get("has_clock_data"):
        result["time_management"] = time_management

    pgn_meta = extract_platform_metadata_from_pgn(pgn)
    for key in ("platform_game_url", "platform", "date_played"):
        if pgn_meta.get(key) and not result.get(key):
            result[key] = pgn_meta[key]
    if not result.get("opponent") and pgn_meta.get("white") and pgn_meta.get("black"):
        player_color = result.get("player_color", "white")
        if player_color == "white":
            result["opponent"] = pgn_meta["black"]
        elif player_color == "black":
            result["opponent"] = pgn_meta["white"]

    return result
