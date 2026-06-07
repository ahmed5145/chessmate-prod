"""
Per-game coach blurbs (2–3 sentences) focused on each game's worst critical moment.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PerGameCoachGeneratorError(Exception):
    """Raised when per-game coach notes cannot be produced."""


def _worst_critical_moment(game_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    moments = game_result.get("critical_moments") or []
    if not moments:
        return None
    return max(moments, key=lambda item: float(item.get("eval_swing") or 0))


def _template_coach_note(game_result: Dict[str, Any]) -> Optional[str]:
    moment = _worst_critical_moment(game_result)
    if not moment:
        return None

    theme = str(moment.get("tactical_theme") or "tactical oversight").replace("_", " ")
    explanation = moment.get("explanation") or ""
    played = moment.get("played_move") or "?"
    best = moment.get("best_move") or "?"
    move_no = moment.get("move_number")
    swing = float(moment.get("eval_swing") or 0)

    parts = [
        f"Your biggest swing was move {move_no}: {moment.get('type', 'mistake')} ({theme}).",
        f"You played {played}; the engine preferred {best} (swing {swing:.2f}).",
    ]
    if explanation:
        parts.append(str(explanation).strip())
    text = " ".join(parts)
    return text[:400] if len(text) > 400 else text


def _build_payload(per_game_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    payload = []
    for game in per_game_results:
        moment = _worst_critical_moment(game)
        if not moment:
            continue
        payload.append(
            {
                "game_id": game.get("game_id"),
                "opening_name": game.get("opening_name"),
                "result": game.get("result"),
                "worst_moment": {
                    "move_number": moment.get("move_number"),
                    "type": moment.get("type"),
                    "phase": moment.get("phase"),
                    "played_move": moment.get("played_move"),
                    "best_move": moment.get("best_move"),
                    "tactical_theme": moment.get("tactical_theme"),
                    "eval_swing": moment.get("eval_swing"),
                    "explanation": moment.get("explanation"),
                },
            }
        )
    return payload


def generate_per_game_coach_notes(
    per_game_results: List[Dict[str, Any]],
    player_rating: Optional[int] = None,
) -> Dict[str, str]:
    """
    Return {game_id: coach_note}. Uses one batched OpenAI call when available;
    falls back to template notes per game on failure.
    """
    notes: Dict[str, str] = {}
    for game in per_game_results:
        game_id = game.get("game_id")
        if not game_id:
            continue
        template = _template_coach_note(game)
        if template:
            notes[game_id] = template

    payload = _build_payload(per_game_results)
    if not payload:
        return notes

    try:
        from openai import OpenAI

        client = OpenAI()
        system_prompt = (
            "You are a chess coach. For each game, write exactly one coach_note (2–3 sentences, max 320 chars) "
            "about the listed worst_moment only. Use facts from the JSON; cite move_number. "
            "Do not mention internal game_id strings in coach_note — write as if reviewing this specific game "
            '(e.g. "In this game, at move 19..." or "At move 19..."). '
            'No markdown. Return JSON: {"notes":[{"game_id":"game_0","coach_note":"..."}, ...]} '
            "Include every game_id from the input."
        )
        user_message = json.dumps(
            {
                "player_rating": player_rating,
                "games": payload,
            }
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        for row in parsed.get("notes") or []:
            if not isinstance(row, dict):
                continue
            game_id = row.get("game_id")
            coach_note = (row.get("coach_note") or "").strip()
            if game_id and coach_note:
                notes[game_id] = coach_note[:400]
    except Exception as exc:
        logger.warning("Per-game coach OpenAI call failed, using templates: %s", exc)

    return notes


def attach_coach_notes_to_results(
    per_game_results: List[Dict[str, Any]],
    notes_by_game_id: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Mutate and return per_game_results with coach_note set where available."""
    for game in per_game_results:
        game_id = game.get("game_id")
        if game_id and game_id in notes_by_game_id:
            game["coach_note"] = notes_by_game_id[game_id]
    return per_game_results
