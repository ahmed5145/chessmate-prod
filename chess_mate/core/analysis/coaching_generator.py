import json
import logging
from typing import Any, Dict, List, Optional

from core.analysis.coaching_schema import BATCH_COACHING_REPORT_SCHEMA

logger = logging.getLogger(__name__)


class CoachingGeneratorError(Exception):
    """Raised when the coaching generator fails to produce a valid report."""


def _map_result_short(result_str: str, player_color: str) -> str:
    if result_str == "1-0":
        return "win" if player_color == "white" else "loss"
    if result_str == "0-1":
        return "win" if player_color == "black" else "loss"
    if result_str == "1/2-1/2":
        return "draw"
    return result_str


def _load_coaching_report_schema() -> Optional[Dict[str, Any]]:
    try:
        json_schema = getattr(
            __import__("core.analysis.coaching_schema", fromlist=["BATCH_COACHING_REPORT_SCHEMA"]),
            "BATCH_COACHING_REPORT_SCHEMA",
        )
    except Exception:
        return None

    if isinstance(json_schema, dict) and "schema" in json_schema:
        return json_schema["schema"]
    return json_schema


def _validate_coaching_report(parsed: Dict[str, Any]) -> None:
    json_schema = _load_coaching_report_schema()
    if json_schema is None:
        return

    try:
        import jsonschema
    except ImportError:
        logger.warning("jsonschema not installed; skipping coaching report validation")
        return

    jsonschema.validate(instance=parsed, schema=json_schema)


def _build_per_game_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    # Support two shapes: either the direct per-game result, or a wrapper
    # {"game_id", "status":"success"|"failed", "result": {...} }
    status = item.get("status")
    if status == "failed":
        return {
            "game_id": item.get("game_id"),
            "status": "failed",
            "error": item.get("error"),
        }

    result = item.get("result") if status is not None else item

    game_id = result.get("game_id")
    player_color = result.get("player_color", "white")
    raw_result = result.get("result", "")

    # phase scores: convert avg_eval_drop to score
    phase_breakdown = {}
    for phase in ("opening", "middlegame", "endgame"):
        phase_data = result.get("phase_breakdown", {}).get(phase, {})
        avg_eval_drop = float(phase_data.get("avg_eval_drop", 0.0) or 0.0)
        score = max(0.0, min(1.0, 1.0 - avg_eval_drop))
        phase_breakdown[phase] = {"score": round(score, 2)}

    move_quality = result.get("move_quality", {})
    blunder_count = int(move_quality.get("blunder", 0) or 0)
    mistake_count = int(move_quality.get("mistake", 0) or 0)

    tactical_themes = []
    critical_moments = []
    for m in result.get("critical_moments", [])[:5]:
        theme = m.get("tactical_theme")
        if theme and theme not in tactical_themes:
            tactical_themes.append(theme)
        critical_moments.append(
            {
                "move_number": m.get("move_number"),
                "phase": m.get("phase"),
                "type": m.get("type"),
                "played_move": m.get("played_move"),
                "best_move": m.get("best_move"),
                "tactical_theme": theme,
                "endgame_material": m.get("endgame_material"),
                "eval_swing": m.get("eval_swing"),
            }
        )

    return {
        "game_id": game_id,
        "result": _map_result_short(raw_result, player_color),
        "opening_name": result.get("opening_name", "Unknown"),
        "phase_breakdown": phase_breakdown,
        "blunder_count": blunder_count,
        "mistake_count": mistake_count,
        "tactical_themes": tactical_themes,
        "critical_moments": critical_moments,
    }


def generate_coaching_report(
    batch_summary: Dict[str, Any],
    per_game_results: List[Dict[str, Any]],
    player_rating: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a batch coaching report by calling the OpenAI API once with a
    structured JSON schema response_format.

    Raises CoachingGeneratorError on failures from the API or invalid responses.
    """
    # Build per-game summaries (trimmed objects) and failed games list
    per_game_summaries = []
    failed_games = []
    for item in per_game_results:
        # item may be already a wrapped response with status
        status = item.get("status")
        if status == "failed":
            failed_games.append({"game_id": item.get("game_id"), "error": item.get("error")})
            continue

        summary = _build_per_game_summary(item)
        # If the summary indicates a failure, move to failed_games
        if summary.get("status") == "failed":
            failed_games.append({"game_id": summary.get("game_id"), "error": item.get("error")})
        else:
            per_game_summaries.append(summary)

    # System prompt from PRD with an added instruction about skipping no_data phases
    system_prompt = (
        "You are a chess coach generating a batch improvement report from structured analysis data.\n"
        "Use only the provided aggregated metrics and per-game summaries. Do not invent openings, move numbers, tactical themes, or chess facts that are not present in the input. Be direct, specific, and practical. No generic advice. No motivational filler. No hedging. No markdown. No prose outside the JSON object.\n"
        "Return only valid JSON that exactly matches the supplied schema. Every field is required. Use concise coaching language. If some games failed or data is missing, reflect that succinctly inside the JSON fields rather than outside the schema.\n"
        "If a player rating is provided, calibrate all advice, drills, and priorities to that skill level. A 1200-rated player needs fundamentals. A 1600-rated player needs pattern recognition and basic strategy. A 2000-rated player needs deep calculation, complex positional play, and advanced endgame technique — do not recommend beginner drills.\n"
        'CRITICAL: If a phase has trend: "no_data", do not reference it as a weakness or strength — skip it entirely in the coaching narrative for that phase and note data was insufficient.\n'
        "MANDATORY SPECIFICITY:\n"
        "- If batch_summary contains opening_insights, you MUST name at least one opening by name in executive_summary or opening narrative and reference its record/recommendation.\n"
        "- If batch_summary contains endgame_insights, you MUST name the endgame type (e.g. rook and pawn) in endgame narrative and cite study_focus wording.\n"
        "- top_3_priorities titles and specific_drill must cite real game_id and move_number from per_game_summaries.critical_moments when available (e.g. 'In game_0 move 22...').\n"
        "- training_plan weeks must differ from each other and reference concrete weaknesses from opening_insights/endgame_insights/recurring_weaknesses — not generic 'do puzzles daily' every week.\n"
        "- Do not only say fork or missed_tactic; tie tactics to the listed moments and openings."
    )

    user_template = (
        "Generate the batch coaching report from this data.\n\n"
        "PLAYER_RATING:\n"
        "{player_rating}\n\n"
        "BATCH_SUMMARY_JSON:\n"
        "{batch_summary_json}\n\n"
        "PER_GAME_SUMMARIES_JSON:\n"
        "{per_game_summaries_json}\n\n"
        "FAILED_GAMES_JSON:\n"
        "{failed_games_json}\n\n"
        "Return a JSON object that matches the coaching schema exactly."
    )

    batch_summary_json = json.dumps(batch_summary)
    per_game_summaries_json = json.dumps(per_game_summaries)
    failed_games_json = json.dumps(failed_games)
    player_rating_text = str(player_rating) if player_rating is not None else "Unknown"

    user_message = user_template.format(
        player_rating=player_rating_text,
        batch_summary_json=batch_summary_json,
        per_game_summaries_json=per_game_summaries_json,
        failed_games_json=failed_games_json,
    )

    # Call OpenAI client (attempt to use the official OpenAI client if available)
    try:
        try:
            from openai import OpenAI

            client = OpenAI()
        except Exception:
            # Fallback: try importing openai module object
            import openai as _openai

            client = getattr(_openai, "OpenAI", _openai)()

        # Prepare response_format using the canonical schema
        response_format = {
            "type": "json_schema",
            "json_schema": BATCH_COACHING_REPORT_SCHEMA,
        }

        logger.info(f"Coaching generation prompt length: {len(user_message)} chars")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format=response_format,
        )

        # Support both the OpenAI SDK response shape and our test double shape.
        if hasattr(response, "output_parsed") and response.output_parsed is not None:
            parsed = response.output_parsed
            if isinstance(parsed, dict):
                _validate_coaching_report(parsed)
                return parsed
            raise CoachingGeneratorError(f"OpenAI returned unexpected type: {type(parsed)}")

        # Extract JSON string from response.choices[0].message.content
        content = response.choices[0].message.content
        logger.info(f"OpenAI response (first 200 chars): {content[:200]}")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise CoachingGeneratorError(f"OpenAI returned non-JSON response: {content[:200]}") from e

        if not isinstance(parsed, dict):
            raise CoachingGeneratorError(f"OpenAI returned unexpected type: {type(parsed)}, content: {content[:200]}")

        _validate_coaching_report(parsed)

        return parsed

    except Exception as exc:
        # Wrap any exception to allow caller to handle specifically
        raise CoachingGeneratorError("Coaching generation failed") from exc
