"""Cross-batch moment timeline — pattern recurrence over time (SRG-10)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from django.utils import timezone

from .models import BatchAnalysisReport, Game, Profile

TIMELINE_PREF_KEY = "moment_timeline"
_MIN_EVENTS_TO_SHOW = 2


def _normalize_token(value: Any) -> str:
    return str(value or "").replace("_", " ").strip().lower()


def build_moment_signature(
    pattern_or_type: Any,
    phase: Any,
    opening_eco: Optional[str] = None,
) -> str:
    pattern = _normalize_token(pattern_or_type) or "positional_slip"
    pattern = pattern.replace(" ", "_")
    phase_name = phase if phase in ("opening", "middlegame", "endgame") else "middlegame"
    eco = str(opening_eco or "").strip().upper()[:10]
    return f"{pattern}|{phase_name}|{eco}"


def signature_from_moment(
    moment: Dict[str, Any],
    *,
    opening_eco: Optional[str] = None,
) -> str:
    pattern = moment.get("tactical_theme") or moment.get("pattern") or moment.get("type") or "positional_slip"
    return build_moment_signature(pattern, moment.get("phase"), opening_eco)


def _infer_phase_from_pattern(pattern: Any) -> str:
    blob = _normalize_token(pattern)
    if any(token in blob for token in ("opening", "prep", "repertoire")):
        return "opening"
    if "endgame" in blob:
        return "endgame"
    return "middlegame"


def _load_events(profile: Profile) -> List[Dict[str, Any]]:
    if profile.pk:
        profile.refresh_from_db(fields=["preferences"])
    raw = profile.get_preference(TIMELINE_PREF_KEY, None)
    if isinstance(raw, dict):
        events = raw.get("events")
        if isinstance(events, list):
            return [event for event in events if isinstance(event, dict)]
    if isinstance(raw, list):
        return [event for event in raw if isinstance(event, dict)]
    return []


def _save_events(profile: Profile, events: List[Dict[str, Any]]) -> None:
    profile.set_preference(TIMELINE_PREF_KEY, {"events": events[-500:]})


def _parse_occurred_at(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed)
        return parsed
    except (TypeError, ValueError):
        return None


def _append_event(profile: Profile, event: Dict[str, Any]) -> None:
    dedupe_key = event.get("dedupe_key")
    events = _load_events(profile)
    if dedupe_key and any(row.get("dedupe_key") == dedupe_key for row in events):
        return
    events.append(event)
    _save_events(profile, events)


def extract_critical_moments_from_analysis(analysis: Any) -> List[Dict[str, Any]]:
    moments: List[Dict[str, Any]] = []
    feedback = getattr(analysis, "feedback", None)
    analysis_data = getattr(analysis, "analysis_data", None)
    if isinstance(feedback, dict):
        for container in (feedback.get("coaching"), feedback):
            if isinstance(container, dict):
                raw = container.get("critical_moments")
                if isinstance(raw, list):
                    moments.extend(item for item in raw if isinstance(item, dict))
    if isinstance(analysis_data, dict):
        raw = analysis_data.get("critical_moments")
        if isinstance(raw, list):
            moments.extend(item for item in raw if isinstance(item, dict))
    return moments


def record_batch_timeline_events(batch_report: BatchAnalysisReport) -> int:
    """Append timeline events from a completed batch report."""
    if batch_report.status not in ("completed", "partial"):
        return 0

    try:
        profile = Profile.objects.get(user=batch_report.user)
    except Profile.DoesNotExist:
        return 0

    batch_summary = batch_report.batch_summary if isinstance(batch_report.batch_summary, dict) else {}
    per_game_results = batch_report.per_game_results if isinstance(batch_report.per_game_results, list) else []
    occurred_at = (batch_report.updated_at or batch_report.created_at or timezone.now()).isoformat()
    added = 0

    weaknesses = batch_summary.get("recurring_weaknesses") or []
    if isinstance(weaknesses, list):
        for weakness in weaknesses:
            if not isinstance(weakness, dict):
                continue
            pattern = weakness.get("pattern")
            if not pattern:
                continue
            phase = _infer_phase_from_pattern(pattern)
            signature = build_moment_signature(pattern, phase)
            dedupe_key = f"batch:{batch_report.id}:weakness:{signature}"
            _append_event(
                profile,
                {
                    "dedupe_key": dedupe_key,
                    "signature": signature,
                    "pattern": str(pattern),
                    "phase": phase,
                    "batch_id": batch_report.id,
                    "game_id": None,
                    "move_number": None,
                    "eval_swing": weakness.get("avg_eval_swing"),
                    "occurred_at": occurred_at,
                    "source": "batch_weakness",
                },
            )
            added += 1

    top_moments = batch_summary.get("top_critical_moments") or []
    if isinstance(top_moments, list):
        for moment in top_moments:
            if not isinstance(moment, dict):
                continue
            eco = None
            saved_id = moment.get("saved_game_id")
            if saved_id:
                game = Game.objects.filter(id=saved_id, user=batch_report.user).first()
                if game and game.opening_name:
                    eco = getattr(game, "eco_code", None)
            signature = signature_from_moment(moment, opening_eco=eco)
            dedupe_key = f"batch:{batch_report.id}:moment:{signature}:{moment.get('move_number')}"
            _append_event(
                profile,
                {
                    "dedupe_key": dedupe_key,
                    "signature": signature,
                    "pattern": moment.get("tactical_theme") or moment.get("type"),
                    "phase": moment.get("phase") or "middlegame",
                    "opening_eco": eco,
                    "batch_id": batch_report.id,
                    "game_id": saved_id,
                    "move_number": moment.get("move_number"),
                    "eval_swing": moment.get("eval_swing"),
                    "occurred_at": occurred_at,
                    "source": "batch_moment",
                },
            )
            added += 1

    if added == 0 and per_game_results:
        for game_result in per_game_results[:3]:
            if not isinstance(game_result, dict):
                continue
            for moment in (game_result.get("critical_moments") or [])[:1]:
                if not isinstance(moment, dict):
                    continue
                signature = signature_from_moment(moment)
                dedupe_key = f"batch:{batch_report.id}:fallback:{signature}:{moment.get('move_number')}"
                _append_event(
                    profile,
                    {
                        "dedupe_key": dedupe_key,
                        "signature": signature,
                        "pattern": moment.get("tactical_theme") or moment.get("type"),
                        "phase": moment.get("phase") or "middlegame",
                        "batch_id": batch_report.id,
                        "game_id": game_result.get("saved_game_id"),
                        "move_number": moment.get("move_number"),
                        "eval_swing": moment.get("eval_swing"),
                        "occurred_at": occurred_at,
                        "source": "batch_moment",
                    },
                )
                added += 1
                break

    return added


def record_single_game_timeline_events(
    profile: Profile,
    game: Game,
    moments: List[Dict[str, Any]],
) -> int:
    if not moments:
        return 0

    eco = getattr(game, "eco_code", None)
    occurred_at = timezone.now().isoformat()
    added = 0
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        swing = float(moment.get("eval_swing") or 0)
        if swing < 0.25 and moment.get("type") not in ("blunder", "mistake"):
            continue
        signature = signature_from_moment(moment, opening_eco=eco)
        dedupe_key = f"game:{game.id}:{moment.get('move_number')}:{signature}"
        _append_event(
            profile,
            {
                "dedupe_key": dedupe_key,
                "signature": signature,
                "pattern": moment.get("tactical_theme") or moment.get("type"),
                "phase": moment.get("phase") or "middlegame",
                "opening_eco": eco,
                "batch_id": None,
                "game_id": game.id,
                "move_number": moment.get("move_number"),
                "eval_swing": moment.get("eval_swing"),
                "occurred_at": occurred_at,
                "source": "single_game",
            },
        )
        added += 1
    return added


def summarize_timeline_for_signature(
    profile: Profile,
    signature: str,
) -> Dict[str, Any]:
    events = [event for event in _load_events(profile) if event.get("signature") == signature]
    events.sort(key=lambda row: row.get("occurred_at") or "")

    if len(events) < _MIN_EVENTS_TO_SHOW:
        return {"show": False, "signature": signature, "event_count": len(events)}

    batch_ids = sorted({int(event["batch_id"]) for event in events if event.get("batch_id") is not None})
    batch_count = len(batch_ids)

    months: List[str] = []
    for event in events:
        occurred = _parse_occurred_at(event.get("occurred_at"))
        if occurred:
            label = occurred.strftime("%b")
            if label not in months:
                months.append(label)

    swings = [float(event["eval_swing"]) for event in events if event.get("eval_swing") is not None]
    trend_copy = None
    if len(swings) >= 2:
        delta = swings[0] - swings[-1]
        if abs(delta) >= 0.1:
            direction = "down" if delta > 0 else "up"
            trend_copy = f"Avg swing {direction} {abs(delta):.1f} pawns since first sighting"

    if batch_count >= 2:
        headline = f"This pattern appeared in {batch_count} batches"
    else:
        headline = f"This pattern appeared {len(events)} times across your reviews"

    return {
        "show": True,
        "signature": signature,
        "event_count": len(events),
        "batch_count": batch_count,
        "headline": headline,
        "months_label": ", ".join(months[:6]),
        "trend_copy": trend_copy,
        "sparkline": [round(value, 2) for value in swings[-8:]],
        "events": [
            {
                "batch_id": event.get("batch_id"),
                "game_id": event.get("game_id"),
                "move_number": event.get("move_number"),
                "eval_swing": event.get("eval_swing"),
                "occurred_at": event.get("occurred_at"),
            }
            for event in events[-8:]
        ],
    }


def attach_timelines_to_moments(
    profile: Profile,
    moments: List[Dict[str, Any]],
    *,
    opening_eco: Optional[str] = None,
) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        row = dict(moment)
        signature = signature_from_moment(row, opening_eco=opening_eco)
        row["timeline"] = summarize_timeline_for_signature(profile, signature)
        enriched.append(row)
    return enriched


def enrich_batch_report_payload(
    payload: Dict[str, Any],
    profile: Profile,
) -> Dict[str, Any]:
    """Attach timeline summaries to batch report weaknesses and top moments."""
    data = dict(payload)
    batch_summary = data.get("batch_summary")
    if not isinstance(batch_summary, dict):
        return data

    summary = dict(batch_summary)
    weaknesses = summary.get("recurring_weaknesses")
    if isinstance(weaknesses, list):
        enriched_weaknesses = []
        for weakness in weaknesses:
            if not isinstance(weakness, dict):
                continue
            row = dict(weakness)
            pattern = row.get("pattern")
            phase = _infer_phase_from_pattern(pattern)
            signature = build_moment_signature(pattern, phase)
            row["timeline"] = summarize_timeline_for_signature(profile, signature)
            enriched_weaknesses.append(row)
        summary["recurring_weaknesses"] = enriched_weaknesses

    top_moments = summary.get("top_critical_moments")
    if isinstance(top_moments, list):
        summary["top_critical_moments"] = attach_timelines_to_moments(
            profile,
            top_moments,
        )

    data["batch_summary"] = summary
    return data
