"""Coach priority inbox — batch priorities as actionable queue items (SRG-9 / SRG-19)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from django.contrib.auth.models import User
from django.utils import timezone

from .inbox_streak import (get_inbox_streak_payload,
                           update_inbox_streak_on_review)
from .models import BatchAnalysisReport, Profile

INBOX_PREF_KEY = "priority_inbox"
_MAX_ITEMS = 3

_GAME_REF_RE = re.compile(r"game[_\s-]?(\d+)", re.IGNORECASE)
_MOVE_REF_RE = re.compile(r"move\s*#?\s*(\d+)", re.IGNORECASE)

_PHASE_KEYWORDS = {
    "opening": ("opening", "prep", "repertoire", "development", "opening prep"),
    "middlegame": (
        "middlegame",
        "tactic",
        "tactical",
        "calculation",
        "vision",
        "middlegame",
    ),
    "endgame": ("endgame", "conversion", "technique", "pawn endgame"),
}


def _empty_inbox() -> Dict[str, Any]:
    return {"items": [], "archived_batch_ids": []}


def _load_inbox(profile: Profile) -> Dict[str, Any]:
    raw = profile.get_preference(INBOX_PREF_KEY, None)
    if not isinstance(raw, dict):
        return _empty_inbox()
    items = raw.get("items")
    archived = raw.get("archived_batch_ids")
    return {
        "items": list(items) if isinstance(items, list) else [],
        "archived_batch_ids": list(archived) if isinstance(archived, list) else [],
    }


def _save_inbox(profile: Profile, inbox: Dict[str, Any]) -> None:
    profile.set_preference(INBOX_PREF_KEY, inbox)


def _item_key(batch_id: int, priority_index: int) -> str:
    return f"{batch_id}:{priority_index}"


def _normalize_match_text(value: Any) -> str:
    return str(value or "").replace("_", " ").strip().lower()


def _priority_text_blob(priority: Dict[str, Any]) -> str:
    return _normalize_match_text(
        " ".join(
            str(priority.get(key) or "")
            for key in ("title", "specific_drill", "how_to_fix", "why_it_matters")
        )
    )


def _parse_priority_refs(
    priority: Dict[str, Any]
) -> Tuple[Optional[int], Optional[int]]:
    blob = " ".join(
        str(priority.get(key) or "")
        for key in ("title", "specific_drill", "how_to_fix")
    )
    game_idx = None
    move_number = None

    game_match = _GAME_REF_RE.search(blob)
    if game_match:
        game_idx = int(game_match.group(1))

    move_match = _MOVE_REF_RE.search(blob)
    if move_match:
        move_number = int(move_match.group(1))

    return game_idx, move_number


def _per_game_by_batch_index(
    per_game_results: List[Dict[str, Any]],
    game_idx: int,
) -> Optional[Dict[str, Any]]:
    target_id = f"game_{game_idx}"
    for result in per_game_results:
        if not isinstance(result, dict):
            continue
        if str(result.get("game_id")) == target_id:
            return result
    return None


def _infer_priority_phase(
    priority: Dict[str, Any],
    batch_summary: Dict[str, Any],
) -> Optional[str]:
    blob = _priority_text_blob(priority)
    for phase, keywords in _PHASE_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords):
            return phase

    weaknesses = batch_summary.get("recurring_weaknesses") or []
    if isinstance(weaknesses, list) and blob:
        for weakness in weaknesses:
            if not isinstance(weakness, dict):
                continue
            pattern = _normalize_match_text(weakness.get("pattern"))
            if pattern and (pattern in blob or blob in pattern):
                phase = weakness.get("phase")
                if phase in ("opening", "middlegame", "endgame"):
                    return phase

    worst_phase = batch_summary.get("worst_phase")
    if worst_phase in ("opening", "middlegame", "endgame"):
        return worst_phase
    return None


def _match_weakness_pattern(
    priority: Dict[str, Any],
    batch_summary: Dict[str, Any],
) -> Optional[str]:
    weaknesses = batch_summary.get("recurring_weaknesses") or []
    if not isinstance(weaknesses, list) or not weaknesses:
        return None

    blob = _priority_text_blob(priority)
    for weakness in weaknesses:
        if not isinstance(weakness, dict):
            continue
        pattern = _normalize_match_text(weakness.get("pattern"))
        if pattern and blob and (pattern in blob or blob in pattern):
            return pattern

    first = weaknesses[0]
    if isinstance(first, dict):
        return _normalize_match_text(first.get("pattern")) or None
    return None


def _iter_ranked_moments(
    per_game_results: List[Dict[str, Any]],
    batch_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    top_moments = batch_summary.get("top_critical_moments") or []
    if isinstance(top_moments, list):
        for moment in top_moments:
            if isinstance(moment, dict) and moment.get("saved_game_id") is not None:
                ranked.append(dict(moment))

    for game_result in per_game_results:
        if not isinstance(game_result, dict):
            continue
        saved_game_id = game_result.get("saved_game_id")
        if saved_game_id is None:
            continue
        player_color = game_result.get("player_color")
        for moment in game_result.get("critical_moments") or []:
            if not isinstance(moment, dict):
                continue
            if (
                player_color
                and moment.get("mover")
                and moment.get("mover") != player_color
            ):
                continue
            ranked.append(
                {
                    **moment,
                    "saved_game_id": saved_game_id,
                    "game_result": game_result,
                }
            )

    ranked.sort(
        key=lambda row: float(row.get("eval_swing") or 0),
        reverse=True,
    )
    return ranked


def _score_moment_for_priority(
    moment: Dict[str, Any],
    *,
    phase: Optional[str],
    pattern: Optional[str],
) -> float:
    score = float(moment.get("eval_swing") or 0)
    if phase and moment.get("phase") == phase:
        score += 10.0
    if pattern:
        theme = _normalize_match_text(moment.get("tactical_theme"))
        if theme and (pattern in theme or theme in pattern):
            score += 5.0
    return score


def _build_proof_label(
    game_result: Optional[Dict[str, Any]],
    moment: Dict[str, Any],
) -> Optional[str]:
    if not game_result:
        return None

    opening = str(game_result.get("opening_name") or "").strip()
    if not opening or opening.lower() == "unknown":
        opening = "Proof game"

    opponent = str(game_result.get("opponent") or "").strip() or "opponent"
    move_number = moment.get("move_number")
    if move_number:
        return f"{opening} example: vs {opponent}, move {move_number}"
    return f"{opening} example: vs {opponent}"


def _pick_proof_game_for_priority(
    priority: Dict[str, Any],
    per_game_results: List[Dict[str, Any]],
    batch_summary: Dict[str, Any],
    used_game_ids: Set[int],
) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[Dict[str, Any]]]:
    """
    SRG-19: pick highest-swing moment in the priority's matching phase.
    Returns (saved_game_id, move_number, proof_label, game_result).
    """
    game_idx, move_number = _parse_priority_refs(priority)
    if game_idx is not None:
        game_result = _per_game_by_batch_index(per_game_results, game_idx)
        if game_result and game_result.get("saved_game_id") is not None:
            saved_id = int(game_result["saved_game_id"])
            if move_number is None:
                for moment in game_result.get("critical_moments") or []:
                    if isinstance(moment, dict) and moment.get("move_number"):
                        move_number = int(moment["move_number"])
                        return (
                            saved_id,
                            move_number,
                            _build_proof_label(game_result, moment),
                            game_result,
                        )
            moment = {"move_number": move_number}
            return (
                saved_id,
                move_number,
                _build_proof_label(game_result, moment),
                game_result,
            )

    ranked_moments = _iter_ranked_moments(per_game_results, batch_summary)
    if not ranked_moments:
        return None, move_number, None, None

    phase = _infer_priority_phase(priority, batch_summary)
    pattern = _match_weakness_pattern(priority, batch_summary)

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for moment in ranked_moments:
        scored.append(
            (
                _score_moment_for_priority(moment, phase=phase, pattern=pattern),
                moment,
            )
        )
    scored.sort(key=lambda row: row[0], reverse=True)

    def _pick_from_scored(
        allow_used_games: bool,
    ) -> Optional[Tuple[int, int, str, Dict[str, Any]]]:
        for _, moment in scored:
            saved_id = moment.get("saved_game_id")
            if saved_id is None:
                continue
            saved_id = int(saved_id)
            if not allow_used_games and saved_id in used_game_ids:
                continue
            game_result = moment.get("game_result")
            if game_result is None:
                for result in per_game_results:
                    if (
                        isinstance(result, dict)
                        and int(result.get("saved_game_id") or 0) == saved_id
                    ):
                        game_result = result
                        break
            move = moment.get("move_number")
            if move is None:
                continue
            proof_label = _build_proof_label(game_result, moment)
            return saved_id, int(move), proof_label, game_result
        return None

    picked = _pick_from_scored(allow_used_games=False) or _pick_from_scored(
        allow_used_games=True
    )
    if picked:
        return picked

    fallback = ranked_moments[0]
    saved_id = int(fallback["saved_game_id"])
    game_result = fallback.get("game_result")
    move = fallback.get("move_number")
    return (
        saved_id,
        int(move) if move is not None else None,
        _build_proof_label(game_result, fallback),
        game_result,
    )


def _build_inbox_item(
    *,
    batch_report: BatchAnalysisReport,
    priority: Dict[str, Any],
    priority_index: int,
    used_game_ids: Set[int],
) -> Dict[str, Any]:
    per_game_results = (
        batch_report.per_game_results
        if isinstance(batch_report.per_game_results, list)
        else []
    )
    batch_summary = (
        batch_report.batch_summary
        if isinstance(batch_report.batch_summary, dict)
        else {}
    )
    linked_game_id, linked_move, proof_label, game_result = (
        _pick_proof_game_for_priority(
            priority, per_game_results, batch_summary, used_game_ids
        )
    )
    if linked_game_id is not None:
        used_game_ids.add(int(linked_game_id))

    completed_at = batch_report.updated_at or batch_report.created_at
    return {
        "id": _item_key(batch_report.id, priority_index),
        "batch_id": batch_report.id,
        "priority_index": priority_index,
        "title": str(priority.get("title") or f"Priority {priority_index}").strip(),
        "drill": str(
            priority.get("specific_drill") or priority.get("how_to_fix") or ""
        ).strip(),
        "linked_game_id": linked_game_id,
        "linked_move": linked_move,
        "proof_label": proof_label,
        "opening_name": (game_result or {}).get("opening_name"),
        "opponent": (game_result or {}).get("opponent"),
        "status": "pending",
        "reviewed_at": None,
        "archived": False,
        "source_batch_completed_at": completed_at.isoformat() if completed_at else None,
        "batch_games_count": batch_report.games_count,
    }


def seed_priority_inbox_from_batch(batch_report: BatchAnalysisReport) -> int:
    """
    Upsert up to 3 inbox items when a batch completes with coaching.
    Archives pending items from older batches (kept for SRG-10 timeline).
    """
    if batch_report.status not in ("completed", "partial"):
        return 0

    coaching_report = (
        batch_report.coaching_report
        if isinstance(batch_report.coaching_report, dict)
        else {}
    )
    priorities = coaching_report.get("top_3_priorities") or []
    if not isinstance(priorities, list) or not priorities:
        return 0

    try:
        profile = Profile.objects.get(user=batch_report.user)
    except Profile.DoesNotExist:
        return 0

    inbox = _load_inbox(profile)
    existing_by_key = {
        item.get("id"): item
        for item in inbox["items"]
        if isinstance(item, dict) and item.get("id")
    }

    archived_ids = set(inbox.get("archived_batch_ids") or [])
    for item in inbox["items"]:
        if not isinstance(item, dict):
            continue
        other_batch_id = item.get("batch_id")
        if (
            other_batch_id
            and int(other_batch_id) != int(batch_report.id)
            and item.get("status") == "pending"
            and not item.get("archived")
        ):
            item["archived"] = True
            item["archived_at"] = timezone.now().isoformat()
            archived_ids.add(int(other_batch_id))

    used_game_ids: Set[int] = set()
    upserted = 0
    for index, priority in enumerate(priorities[:_MAX_ITEMS], start=1):
        if not isinstance(priority, dict):
            continue
        rank = int(priority.get("rank") or index)
        item = _build_inbox_item(
            batch_report=batch_report,
            priority=priority,
            priority_index=rank,
            used_game_ids=used_game_ids,
        )
        prior = existing_by_key.get(item["id"])
        if prior and prior.get("status") == "reviewed":
            item["status"] = "reviewed"
            item["reviewed_at"] = prior.get("reviewed_at")
        existing_by_key[item["id"]] = item
        upserted += 1

    inbox["items"] = list(existing_by_key.values())
    inbox["archived_batch_ids"] = sorted(archived_ids)
    _save_inbox(profile, inbox)
    return upserted


def build_priority_inbox_link(item: Dict[str, Any]) -> Optional[str]:
    batch_id = item.get("batch_id")
    if not batch_id:
        return None
    priority_index = item.get("priority_index")
    linked_game_id = item.get("linked_game_id")
    if linked_game_id:
        params = [f"mode=review", f"batch={batch_id}"]
        if priority_index:
            params.append(f"priority={priority_index}")
        linked_move = item.get("linked_move")
        if linked_move:
            params.append(f"move={linked_move}")
        return f"/game/{linked_game_id}/analysis?{'&'.join(params)}"
    if priority_index:
        return f"/batch-report/{batch_id}?priority={priority_index}"
    return f"/batch-report/{batch_id}"


def get_priority_inbox_payload(profile: Profile) -> Dict[str, Any]:
    inbox = _load_inbox(profile)
    items = [item for item in inbox["items"] if isinstance(item, dict)]
    pending = [
        item
        for item in items
        if item.get("status") == "pending" and not item.get("archived")
    ]
    pending.sort(
        key=lambda row: (
            row.get("source_batch_completed_at") or "",
            row.get("priority_index") or 0,
        )
    )

    serialized_pending = []
    for item in pending:
        row = dict(item)
        row["href"] = build_priority_inbox_link(item)
        serialized_pending.append(row)

    streak = get_inbox_streak_payload(profile.preferences)
    return {
        "pending_count": len(serialized_pending),
        "pending_items": serialized_pending,
        "reviewed_count": sum(
            1
            for item in items
            if item.get("status") == "reviewed" and not item.get("archived")
        ),
        "empty_state_cta": "/batch-analysis",
        "empty_state_label": "Start Batch Coach",
        "streak": streak,
    }


def mark_priority_inbox_reviewed(
    user: User,
    *,
    batch_id: int,
    priority_index: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return False, "Profile not found", None

    report = BatchAnalysisReport.objects.filter(user=user, id=batch_id).first()
    if report is None:
        return False, "Batch not found", None

    inbox = _load_inbox(profile)
    key = _item_key(batch_id, priority_index)
    updated = False
    for item in inbox["items"]:
        if not isinstance(item, dict):
            continue
        if item.get("id") == key or (
            int(item.get("batch_id") or 0) == int(batch_id)
            and int(item.get("priority_index") or 0) == int(priority_index)
        ):
            item["status"] = "reviewed"
            item["reviewed_at"] = timezone.now().isoformat()
            updated = True
            break

    if not updated:
        return False, "Inbox item not found", None

    _save_inbox(profile, inbox)
    streak = update_inbox_streak_on_review(profile)
    return True, "Priority marked reviewed", streak
