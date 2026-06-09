"""Coach priority inbox — batch priorities as actionable queue items (SRG-9)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth.models import User
from django.utils import timezone

from .models import BatchAnalysisReport, Profile

INBOX_PREF_KEY = "priority_inbox"
_MAX_ITEMS = 3

_GAME_REF_RE = re.compile(r"game[_\s-]?(\d+)", re.IGNORECASE)
_MOVE_REF_RE = re.compile(r"move\s*#?\s*(\d+)", re.IGNORECASE)


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


def _resolve_saved_game_and_move(
    priority: Dict[str, Any],
    per_game_results: List[Dict[str, Any]],
    batch_summary: Dict[str, Any],
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

    if game_idx is not None:
        target_id = f"game_{game_idx}"
        for result in per_game_results:
            if not isinstance(result, dict):
                continue
            if str(result.get("game_id")) == target_id:
                saved_id = result.get("saved_game_id")
                if saved_id is not None:
                    return int(saved_id), move_number

    top_moments = batch_summary.get("top_critical_moments") or []
    if isinstance(top_moments, list) and top_moments:
        first = top_moments[0]
        if isinstance(first, dict):
            saved_id = first.get("saved_game_id")
            if saved_id is not None:
                return int(saved_id), move_number or first.get("move_number")

    return None, move_number


def _build_inbox_item(
    *,
    batch_report: BatchAnalysisReport,
    priority: Dict[str, Any],
    priority_index: int,
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
    linked_game_id, linked_move = _resolve_saved_game_and_move(
        priority, per_game_results, batch_summary
    )
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

    upserted = 0
    for index, priority in enumerate(priorities[:_MAX_ITEMS], start=1):
        if not isinstance(priority, dict):
            continue
        rank = int(priority.get("rank") or index)
        item = _build_inbox_item(
            batch_report=batch_report,
            priority=priority,
            priority_index=rank,
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
    }


def mark_priority_inbox_reviewed(
    user: User,
    *,
    batch_id: int,
    priority_index: int,
) -> Tuple[bool, str]:
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return False, "Profile not found"

    report = BatchAnalysisReport.objects.filter(user=user, id=batch_id).first()
    if report is None:
        return False, "Batch not found"

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
        return False, "Inbox item not found"

    _save_inbox(profile, inbox)
    return True, "Priority marked reviewed"
