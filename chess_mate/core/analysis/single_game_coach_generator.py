"""Structured single-game coaching output (gpt-4o-mini + template fallback)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _template_coaching(
    *,
    critical_moments: List[Dict[str, Any]],
    metrics_summary: Dict[str, Any],
    game_context: Optional[Dict[str, Any]] = None,
    batch_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    overall = metrics_summary.get("overall", {}) if isinstance(metrics_summary.get("overall"), dict) else {}
    phases = metrics_summary.get("phases", {}) if isinstance(metrics_summary.get("phases", {}), dict) else {}
    accuracy = overall.get("accuracy")
    mistakes = overall.get("mistakes") or overall.get("blunders") or 0

    worst = critical_moments[0] if critical_moments else None
    opening_name = (game_context or {}).get("opening_name") or "this game"

    priority = (batch_context or {}).get("priority") if isinstance((batch_context or {}).get("priority"), dict) else None
    priority_title = str(priority.get("title") or "").strip() if priority else ""

    if worst:
        takeaway = (
            f"Your largest swing was move {worst.get('move_number')}: "
            f"you played {worst.get('played_move')} instead of {worst.get('best_move')}."
        )
        do_today = (
            f"Replay move {worst.get('move_number')} and calculate {worst.get('best_move')} "
            f"before committing in similar {opening_name} positions."
        )
    else:
        takeaway = f"Focus on reducing mistakes ({mistakes} flagged) while keeping accuracy near {accuracy}%."
        do_today = "Review your two slowest decisions and write one-line plans before each move."

    if priority_title:
        takeaway = f"{takeaway} This ties to your batch priority: {priority_title[:120]}."
        if priority.get("specific_drill"):
            do_today = str(priority.get("specific_drill"))[:240]

    phase_notes: Dict[str, str] = {}
    for phase_name in ("opening", "middlegame", "endgame"):
        phase = phases.get(phase_name, {}) if isinstance(phases.get(phase_name), dict) else {}
        phase_acc = phase.get("accuracy")
        phase_mistakes = phase.get("mistakes", 0)
        if phase_acc is not None:
            phase_notes[phase_name] = f"{phase_name.title()}: {phase_acc}% accuracy, {phase_mistakes} mistakes."

    return {
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
        client = OpenAI(api_key=api_key.strip() if isinstance(api_key, str) else api_key)

        worst_moves = sorted(
            [
                m
                for m in analyzed_moves
                if isinstance(m, dict) and str(m.get("classification", "")).lower() in {"blunder", "mistake", "inaccuracy"}
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
                }
                for m in worst_moves
            ],
            "existing_strengths": (existing_feedback or {}).get("strengths", [])[:3],
            "existing_weaknesses": (existing_feedback or {}).get("weaknesses", [])[:3],
        }

        system_prompt = (
            "You are a chess coach writing a single-game review. Use ONLY supplied JSON facts. "
            "When batch_context.priority is present, reference that batch priority in takeaway. "
            "Return JSON: "
            '{"takeaway":"one sentence","do_today":"one concrete action",'
            '"phase_notes":{"opening":"...","middlegame":"...","endgame":"..."},'
            '"moment_explanations":[{"move_number":int,"explanation":"max 120 chars"}]} '
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

        phase_notes = parsed.get("phase_notes") if isinstance(parsed.get("phase_notes"), dict) else {}
        takeaway = str(parsed.get("takeaway") or template["takeaway"]).strip()
        do_today = str(parsed.get("do_today") or template["do_today"]).strip()

        return {
            "takeaway": takeaway[:320],
            "do_today": do_today[:240],
            "phase_notes": phase_notes or template["phase_notes"],
            "critical_moments": enriched_moments,
            "source": "openai",
        }
    except Exception as exc:
        logger.warning("Single-game coach generation failed, using template: %s", exc)
        return template
