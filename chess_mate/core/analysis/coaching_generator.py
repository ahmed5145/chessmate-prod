import json
from typing import Any, Dict, List

from core.analysis.coaching_schema import BATCH_COACHING_REPORT_SCHEMA


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


def _build_per_game_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    # Support two shapes: either the direct per-game result, or a wrapper
    # {"game_id", "status":"success"|"failed", "result": {...} }
    status = item.get("status")
    if status == "failed":
        return {"game_id": item.get("game_id"), "status": "failed", "error": item.get("error")}

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
    for m in result.get("critical_moments", [])[:10]:
        theme = m.get("tactical_theme")
        if theme and theme not in tactical_themes:
            tactical_themes.append(theme)

    return {
        "game_id": game_id,
        "result": _map_result_short(raw_result, player_color),
        "opening_name": result.get("opening_name", "Unknown"),
        "phase_breakdown": phase_breakdown,
        "blunder_count": blunder_count,
        "mistake_count": mistake_count,
        "tactical_themes": tactical_themes,
    }


def generate_coaching_report(batch_summary: Dict[str, Any], per_game_results: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        "CRITICAL: If a phase has trend: \"no_data\", do not reference it as a weakness or strength — skip it entirely in the coaching narrative for that phase and note data was insufficient."
    )

    user_template = (
        "Generate the batch coaching report from this data.\n\n"
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

    user_message = user_template.format(
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

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format=response_format,
        )

        # Accept either SDK-parsed output or raw content
        parsed = None
        if hasattr(response, "output_parsed"):
            parsed = response.output_parsed
        elif isinstance(response, dict) and response.get("output_parsed") is not None:
            parsed = response.get("output_parsed")
        else:
            # Try to extract text and parse JSON
            # different SDKs expose different structures; be permissive
            try:
                # New SDKs may provide output[0].content[0].text
                output = getattr(response, "output", None) or response.get("output")
                if output and len(output) > 0:
                    content = output[0].get("content") if isinstance(output[0], dict) else None
                    if content and len(content) > 0:
                        text = content[0].get("text") if isinstance(content[0], dict) else None
                        if text:
                            parsed = json.loads(text)
            except Exception:
                parsed = None

        if not parsed or not isinstance(parsed, dict):
            raise CoachingGeneratorError("OpenAI returned no valid parsed JSON")

        return parsed

    except Exception as exc:
        # Wrap any exception to allow caller to handle specifically
        raise CoachingGeneratorError("Coaching generation failed") from exc
