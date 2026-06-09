"""Coach tone preference — direct vs encouraging (SRG-26)."""

from __future__ import annotations

from typing import Any

COACH_PERSONA_KEY = "coach_persona"
DEFAULT_PERSONA = "encouraging"
VALID_PERSONAS = frozenset({"encouraging", "direct"})


def resolve_coach_persona(profile: Any) -> str:
    prefs = getattr(profile, "preferences", None) if profile is not None else None
    if not isinstance(prefs, dict):
        return DEFAULT_PERSONA
    raw = str(prefs.get(COACH_PERSONA_KEY) or DEFAULT_PERSONA).strip().lower()
    return raw if raw in VALID_PERSONAS else DEFAULT_PERSONA


def coach_persona_prompt_modifier(persona: str) -> str:
    if persona == "direct":
        return (
            "\nTone: direct and blunt. Short sentences. No cheerleading or filler. "
            "State facts and actions plainly. Do not change metrics or move facts.\n"
        )
    return (
        "\nTone: encouraging and supportive. Acknowledge effort while staying specific. "
        "Do not change metrics or move facts.\n"
    )
