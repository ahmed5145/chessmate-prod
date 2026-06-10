import json
import logging
import re
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
            __import__(
                "core.analysis.coaching_schema",
                fromlist=["BATCH_COACHING_REPORT_SCHEMA"],
            ),
            "BATCH_COACHING_REPORT_SCHEMA",
        )
    except Exception:
        return None

    if isinstance(json_schema, dict) and "schema" in json_schema:
        return json_schema["schema"]
    return json_schema


_GAME_ID_RE = re.compile(r"game_\d+", re.IGNORECASE)
_MOVE_RE = re.compile(r"move\s*#?\s*\d+", re.IGNORECASE)


def _text_blob(*parts: Any) -> str:
    return " ".join(str(p) for p in parts if p is not None).lower()


def validate_coaching_citations(
    parsed: Dict[str, Any],
    batch_summary: Dict[str, Any],
    per_game_summaries: List[Dict[str, Any]],
) -> List[str]:
    """
    Post-check that coaching prose references grounded batch facts.
    Returns human-readable validation errors (empty if OK).
    """
    errors: List[str] = []
    game_ids = {s.get("game_id") for s in per_game_summaries if s.get("game_id")}

    priorities = parsed.get("top_3_priorities") or []
    if game_ids and priorities:
        cited_game = False
        cited_move = False
        for priority in priorities:
            blob = _text_blob(
                priority.get("title"),
                priority.get("why_it_matters"),
                priority.get("specific_drill"),
            )
            if any(gid and gid.lower() in blob for gid in game_ids):
                cited_game = True
            if _GAME_ID_RE.search(blob):
                cited_game = True
            if _MOVE_RE.search(blob):
                cited_move = True
        if not cited_game:
            errors.append(
                "top_3_priorities must cite at least one game_id from per_game_summaries "
                "(e.g. game_0) in title or specific_drill."
            )
        if not cited_move:
            errors.append(
                "top_3_priorities must cite at least one move number "
                "(e.g. 'move 22') from critical_moments in specific_drill or title."
            )

    opening_insights = batch_summary.get("opening_insights") or []
    if opening_insights:
        opening_names = [
            str(item.get("opening_name", "")).lower()
            for item in opening_insights
            if isinstance(item, dict) and item.get("opening_name")
        ]
        narrative = _text_blob(
            parsed.get("executive_summary"),
            (parsed.get("coaching_narrative") or {}).get("opening"),
        )
        if opening_names and not any(name in narrative for name in opening_names):
            errors.append(
                "executive_summary or coaching_narrative.opening must name an opening "
                "from batch_summary.opening_insights."
            )

    endgame_insights = batch_summary.get("endgame_insights") or []
    if endgame_insights:
        endgame_tokens = []
        for item in endgame_insights:
            if not isinstance(item, dict):
                continue
            for key in ("label", "endgame_type", "study_focus"):
                val = item.get(key)
                if val:
                    endgame_tokens.append(str(val).lower().replace("_", " "))
        endgame_text = _text_blob(
            (parsed.get("coaching_narrative") or {}).get("endgame")
        )
        if endgame_tokens and not any(
            token in endgame_text for token in endgame_tokens if len(token) > 3
        ):
            errors.append(
                "coaching_narrative.endgame must reference an endgame type or study_focus "
                "from batch_summary.endgame_insights."
            )

    return errors


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

    # phase scores: eval stability (1 - avg_eval_drop) plus move match % when available
    phase_breakdown = {}
    for phase in ("opening", "middlegame", "endgame"):
        phase_data = result.get("phase_breakdown", {}).get(phase, {})
        avg_eval_drop = float(phase_data.get("avg_eval_drop", 0.0) or 0.0)
        score = max(0.0, min(1.0, 1.0 - avg_eval_drop))
        phase_entry: Dict[str, Any] = {"score": round(score, 2)}
        if phase_data.get("accuracy") is not None:
            try:
                phase_entry["move_match_pct"] = round(float(phase_data["accuracy"]), 1)
            except (TypeError, ValueError):
                pass
        phase_breakdown[phase] = phase_entry

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

    game_move_match = result.get("accuracy")
    try:
        game_move_match = (
            round(float(game_move_match), 1) if game_move_match is not None else None
        )
    except (TypeError, ValueError):
        game_move_match = None

    return {
        "game_id": game_id,
        "result": _map_result_short(raw_result, player_color),
        "opening_name": result.get("opening_name", "Unknown"),
        "move_match_pct": game_move_match,
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
    coach_persona: str = "encouraging",
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
            failed_games.append(
                {"game_id": item.get("game_id"), "error": item.get("error")}
            )
            continue

        summary = _build_per_game_summary(item)
        # If the summary indicates a failure, move to failed_games
        if summary.get("status") == "failed":
            failed_games.append(
                {"game_id": summary.get("game_id"), "error": item.get("error")}
            )
        else:
            per_game_summaries.append(summary)

    from ..coach_persona import coach_persona_prompt_modifier

    # System prompt from PRD with an added instruction about skipping no_data phases
    system_prompt = (
        "You are a chess coach generating a batch improvement report from structured analysis data.\n"
        f"{coach_persona_prompt_modifier(coach_persona)}"
        "Use only the provided aggregated metrics and per-game summaries. Do not invent openings, move numbers, tactical themes, or chess facts that are not present in the input. Be direct, specific, and practical. No generic advice. No motivational filler. No hedging. No markdown. No prose outside the JSON object.\n"
        "Return only valid JSON that exactly matches the supplied schema. Every field is required. Use concise coaching language. If some games failed or data is missing, reflect that succinctly inside the JSON fields rather than outside the schema.\n"
        "If a player rating is provided, calibrate all advice, drills, and priorities to that skill level. A 1200-rated player needs fundamentals. A 1600-rated player needs pattern recognition and basic strategy. A 2000-rated player needs deep calculation, complex positional play, and advanced endgame technique — do not recommend beginner drills.\n"
        'CRITICAL: If a phase has trend: "no_data", do not reference it as a weakness or strength — skip it entirely in the coaching narrative for that phase and note data was insufficient.\n'
        "MANDATORY SPECIFICITY:\n"
        "- If batch_summary contains opening_insights, you MUST name at least one opening by name in executive_summary or opening narrative and reference its record/recommendation.\n"
        "- If batch_summary contains endgame_insights, you MUST name the endgame type (e.g. rook and pawn) in endgame narrative and cite study_focus wording.\n"
        "- top_3_priorities specific_drill must include TWO parts: (1) a general practice drill (puzzles, themed training, or study — not only one game), and (2) a review step citing game_id and move_number from critical_moments (e.g. 'Practice: 15 hanging-piece puzzles on Lichess. Review: game_0 move 22 — replay the tactic from your game.').\n"
        "- training_plan weeks must differ from each other and reference concrete weaknesses from opening_insights/endgame_insights/recurring_weaknesses — not generic 'do puzzles daily' every week.\n"
        "- Do not only say fork or missed_tactic; tie tactics to the listed moments and openings.\n"
        "METRIC RULES (mandatory):\n"
        "- batch_summary.overall_accuracy_pct and phase_performance.*.accuracy_pct are move match % (Chess.com-style).\n"
        "- batch_summary.overall_eval_stability and phase_performance.*.score are eval stability (0–1), not move match.\n"
        "- opening_insights.avg_opening_move_match_pct is move match for that opening; avg_opening_score is eval stability.\n"
        "- Never call score or eval stability 'accuracy' or 'move match'. Quote the exact field you mean."
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

        def _parse_response(response_obj: Any) -> Dict[str, Any]:
            """
            Support both the OpenAI SDK response shape and our test double shape.

            - Tests / some SDK paths: response.output_parsed (dict)
            - Production chat completions: response.choices[0].message.content (JSON string)
            """
            if (
                hasattr(response_obj, "output_parsed")
                and response_obj.output_parsed is not None
            ):
                parsed_obj = response_obj.output_parsed
                if isinstance(parsed_obj, dict):
                    return parsed_obj
                raise CoachingGeneratorError(
                    f"OpenAI returned unexpected type: {type(parsed_obj)}"
                )

            content = response_obj.choices[0].message.content
            logger.info(f"OpenAI response (first 200 chars): {content[:200]}")
            try:
                loaded = json.loads(content)
            except json.JSONDecodeError as exc:
                raise CoachingGeneratorError(
                    f"OpenAI returned non-JSON response: {content[:200]}"
                ) from exc

            if not isinstance(loaded, dict):
                raise CoachingGeneratorError(
                    f"OpenAI returned unexpected type: {type(loaded)}, content: {content[:200]}"
                )
            return loaded

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format=response_format,
        )
        parsed = _parse_response(response)
        _validate_coaching_report(parsed)

        citation_errors = validate_coaching_citations(
            parsed, batch_summary, per_game_summaries
        )
        if citation_errors:
            logger.warning(
                "Coaching citation validation failed, retrying once: %s",
                citation_errors,
            )
            retry_message = (
                user_message
                + "\n\nYour previous JSON failed grounding checks. Fix and return new JSON only:\n"
                + "\n".join(f"- {err}" for err in citation_errors)
            )
            retry_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": retry_message},
                ],
                response_format=response_format,
            )
            parsed = _parse_response(retry_response)
            _validate_coaching_report(parsed)
            citation_errors = validate_coaching_citations(
                parsed, batch_summary, per_game_summaries
            )
            if citation_errors:
                logger.warning(
                    "Coaching citations still weak after retry (serving report anyway): %s",
                    citation_errors,
                )

        return parsed

    except Exception as exc:
        # Wrap any exception to allow caller to handle specifically
        raise CoachingGeneratorError("Coaching generation failed") from exc
