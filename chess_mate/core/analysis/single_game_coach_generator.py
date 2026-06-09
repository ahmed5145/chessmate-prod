"""Structured single-game coaching output (gpt-4o-mini + template fallback)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _player_pov_eval(white_pov_eval: Any, player_color: str) -> float:
    try:
        value = float(white_pov_eval)
    except (TypeError, ValueError):
        return 0.0
    return value if player_color == "white" else -value


def _format_eval_pawns(value: float) -> str:
    if abs(value) >= 9.5:
        return "+M" if value > 0 else "-M"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}"


def _weakest_phase(phases: Dict[str, Any]) -> Optional[str]:
    scores = []
    for name in ("opening", "middlegame", "endgame"):
        phase = phases.get(name, {}) if isinstance(phases.get(name), dict) else {}
        accuracy = phase.get("accuracy")
        if accuracy is not None:
            try:
                scores.append((name, float(accuracy)))
            except (TypeError, ValueError):
                continue
    if not scores:
        return None
    return min(scores, key=lambda item: item[1])[0]


def _template_coaching(
    *,
    critical_moments: List[Dict[str, Any]],
    metrics_summary: Dict[str, Any],
    game_context: Optional[Dict[str, Any]] = None,
    batch_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    overall = (
        metrics_summary.get("overall", {})
        if isinstance(metrics_summary.get("overall"), dict)
        else {}
    )
    phases = (
        metrics_summary.get("phases", {})
        if isinstance(metrics_summary.get("phases", {}), dict)
        else {}
    )
    accuracy = overall.get("accuracy")
    mistakes = overall.get("mistakes") or overall.get("blunders") or 0

    worst = critical_moments[0] if critical_moments else None
    ctx = game_context or {}
    opening_name = ctx.get("opening_name") or "this game"
    player_color = ctx.get("player_color") or "white"
    result = str(ctx.get("result") or "").lower()
    opponent = ctx.get("opponent") or ctx.get("opponent_name") or "your opponent"
    weakest = _weakest_phase(phases)

    priority = (
        (batch_context or {}).get("priority")
        if isinstance((batch_context or {}).get("priority"), dict)
        else None
    )
    priority_title = str(priority.get("title") or "").strip() if priority else ""

    headline = "Your depth-20 game review"
    takeaway = ""
    do_today = ""

    if worst:
        best_move = worst.get("best_move") or "the engine top move"
        played = worst.get("played_move") or "your move"
        move_no = worst.get("move_number")
        swing = worst.get("eval_swing")
        best_eval = _format_eval_pawns(
            _player_pov_eval(worst.get("eval_after_best"), player_color)
        )
        after_eval = _format_eval_pawns(
            _player_pov_eval(worst.get("eval_after"), player_color)
        )
        headline = f"Move {move_no} swung the game"
        takeaway = (
            f"In {opening_name}, {played} on move {move_no} cost you "
            f"{swing} pawns of eval — {best_move} held {best_eval} instead of {after_eval}."
        )
        do_today = (
            f"Set up move {move_no} on a board, find {best_move} in 3 minutes, "
            f"then replay the next 3 moves from that line."
        )
    else:
        headline = f"{opening_name}: clean review"
        takeaway = (
            f"No single swing dominated vs {opponent}"
            f"{f' ({result})' if result else ''} — keep accuracy near {accuracy}%."
        )
        do_today = "Pick two positions where you spent the most clock and write a one-line plan before moving."

    if weakest:
        phase_acc = (phases.get(weakest) or {}).get("accuracy")
        takeaway = f"{takeaway} Weakest phase: {weakest} ({phase_acc}% accuracy)."

    if priority_title:
        takeaway = f"{takeaway} Batch focus: {priority_title[:100]}."
        if priority.get("specific_drill"):
            do_today = str(priority.get("specific_drill"))[:240]

    phase_notes: Dict[str, str] = {}
    for phase_name in ("opening", "middlegame", "endgame"):
        phase = (
            phases.get(phase_name, {})
            if isinstance(phases.get(phase_name), dict)
            else {}
        )
        phase_acc = phase.get("accuracy")
        phase_mistakes = phase.get("mistakes", 0)
        if phase_acc is not None:
            tone = "solid" if float(phase_acc) >= 70 else "needs work"
            phase_notes[phase_name] = (
                f"{phase_name.title()}: {phase_acc}% accuracy ({tone}), {phase_mistakes} mistakes flagged."
            )

    return {
        "headline": headline[:120],
        "takeaway": takeaway[:320],
        "do_today": do_today[:240],
        "phase_notes": phase_notes,
        "critical_moments": critical_moments,
        "source": "template",
    }


def generate_single_game_coaching(
    *,
    analyzed_moves: List[Dict[str, Any]],
    metrics_summary: Dict[str, Any],
    critical_moments: List[Dict[str, Any]],
    game_context: Optional[Dict[str, Any]] = None,
    existing_feedback: Optional[Dict[str, Any]] = None,
    batch_context: Optional[Dict[str, Any]] = None,
    coach_persona: str = "encouraging",
) -> Dict[str, Any]:
    """
    Produce structured coaching JSON for single-game UI.
    Falls back to template when OpenAI is unavailable.
    """
    template = _template_coaching(
        critical_moments=critical_moments,
        metrics_summary=metrics_summary,
        game_context=game_context,
        batch_context=batch_context,
    )

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return template

    try:
        from openai import OpenAI

        model = getattr(settings, "SINGLE_GAME_COACH_MODEL", "gpt-4o-mini")
        client = OpenAI(
            api_key=api_key.strip() if isinstance(api_key, str) else api_key
        )

        worst_moves = sorted(
            [
                m
                for m in analyzed_moves
                if isinstance(m, dict)
                and str(m.get("classification", "")).lower()
                in {"blunder", "mistake", "inaccuracy"}
            ],
            key=lambda item: abs(float(item.get("eval_change") or 0)),
            reverse=True,
        )[:8]

        payload = {
            "game_context": game_context or {},
            "batch_context": batch_context or {},
            "metrics": {
                "overall": metrics_summary.get("overall", {}),
                "phases": metrics_summary.get("phases", {}),
            },
            "critical_moments": critical_moments,
            "sample_bad_moves": [
                {
                    "move_number": m.get("move_number"),
                    "san": m.get("san"),
                    "classification": m.get("classification"),
                    "best_move_san": m.get("best_move_san"),
                    "eval_change": m.get("eval_change"),
                    "eval_before": m.get("eval_before"),
                    "eval_after": m.get("eval_after"),
                    "eval_after_best": m.get("eval_after_best"),
                }
                for m in worst_moves
            ],
            "existing_strengths": (existing_feedback or {}).get("strengths", [])[:3],
            "existing_weaknesses": (existing_feedback or {}).get("weaknesses", [])[:3],
        }

        from ..coach_persona import coach_persona_prompt_modifier

        system_prompt = (
            "You are a chess coach writing a single-game review for a paying student. "
            f"{coach_persona_prompt_modifier(coach_persona)}"
            "Use ONLY supplied JSON facts — cite specific move numbers, SAN, opening name, and eval swings. "
            "Never write generic advice like 'improve middlegame accuracy' without naming a move or pattern. "
            "When batch_context.priority is present, tie takeaway to that batch priority. "
            "Return JSON: "
            '{"headline":"punchy 8-12 words","takeaway":"one specific sentence",'
            '"do_today":"one concrete 5-minute action",'
            '"phase_notes":{"opening":"...","middlegame":"...","endgame":"..."},'
            '"moment_explanations":[{"move_number":int,"explanation":"max 140 chars, why the swing happened"}]} '
            "moment_explanations must match critical_moments move_numbers only."
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content if response.choices else ""
        parsed = json.loads(content or "{}")
        if not isinstance(parsed, dict):
            return template

        explanations = parsed.get("moment_explanations") or []
        explanation_by_move = {
            int(item["move_number"]): str(item.get("explanation") or "").strip()
            for item in explanations
            if isinstance(item, dict) and item.get("move_number") is not None
        }
        enriched_moments = []
        for moment in critical_moments:
            enriched = dict(moment)
            move_no = enriched.get("move_number")
            if move_no in explanation_by_move and explanation_by_move[move_no]:
                enriched["explanation"] = explanation_by_move[move_no]
            enriched_moments.append(enriched)

        phase_notes = (
            parsed.get("phase_notes")
            if isinstance(parsed.get("phase_notes"), dict)
            else {}
        )
        headline = str(parsed.get("headline") or template.get("headline") or "").strip()
        takeaway = str(parsed.get("takeaway") or template["takeaway"]).strip()
        do_today = str(parsed.get("do_today") or template["do_today"]).strip()

        return {
            "headline": headline[:120],
            "takeaway": takeaway[:320],
            "do_today": do_today[:240],
            "phase_notes": phase_notes or template["phase_notes"],
            "critical_moments": enriched_moments,
            "source": "openai",
        }
    except Exception as exc:
        logger.warning("Single-game coach generation failed, using template: %s", exc)
        return template
