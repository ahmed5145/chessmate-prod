"""In-app notification center (SRG-14)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.utils import timezone

from .batch_deep_links import build_worst_moment_deep_review_url, worst_moment_summary
from .fix_rate import build_fix_rate_payload
from .models import BatchAnalysisReport, Game, UserNotification
from .priority_inbox import build_priority_inbox_link, get_priority_inbox_payload
from .single_game_notifications import _coaching_payload, _email_subject

_DEDUPE_WINDOW = timedelta(hours=24)


def _recent_duplicate(
    user: User,
    notification_type: str,
    entity_id: str,
) -> bool:
    since = timezone.now() - _DEDUPE_WINDOW
    return UserNotification.objects.filter(
        user=user,
        notification_type=notification_type,
        entity_id=entity_id,
        created_at__gte=since,
    ).exists()


def create_user_notification(
    user: User,
    *,
    notification_type: str,
    entity_id: str,
    title: str,
    body: str = "",
    href: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Optional[UserNotification]:
    if not user or not entity_id or not href:
        return None
    if _recent_duplicate(user, notification_type, entity_id):
        return None
    return UserNotification.objects.create(
        user=user,
        notification_type=notification_type,
        entity_id=entity_id,
        title=str(title)[:200],
        body=str(body or "")[:500],
        href=href[:500],
        meta=meta or {},
    )


def serialize_notification(row: UserNotification) -> Dict[str, Any]:
    return {
        "id": row.id,
        "type": row.notification_type,
        "title": row.title,
        "body": row.body,
        "href": row.href,
        "meta": row.meta if isinstance(row.meta, dict) else {},
        "read_at": row.read_at.isoformat() if row.read_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "is_read": row.read_at is not None,
    }


def get_notifications_payload(user: User, *, limit: int = 50) -> Dict[str, Any]:
    rows = list(
        UserNotification.objects.filter(user=user).order_by("-created_at")[:limit]
    )
    unread_count = UserNotification.objects.filter(
        user=user, read_at__isnull=True
    ).count()
    return {
        "unread_count": unread_count,
        "notifications": [serialize_notification(row) for row in rows],
    }


def mark_notification_read(user: User, notification_id: int) -> bool:
    updated = UserNotification.objects.filter(
        user=user, id=notification_id, read_at__isnull=True
    ).update(read_at=timezone.now())
    return updated > 0


def mark_all_notifications_read(user: User) -> int:
    return UserNotification.objects.filter(user=user, read_at__isnull=True).update(
        read_at=timezone.now()
    )


def seed_inbox_notifications(user: User) -> int:
    """Create notifications for pending coach inbox items."""
    profile = getattr(user, "profile", None)
    if profile is None:
        try:
            from .models import Profile

            profile = Profile.objects.get(user=user)
        except Exception:
            return 0

    inbox = get_priority_inbox_payload(profile)
    created = 0
    for item in inbox.get("pending_items") or []:
        if not isinstance(item, dict):
            continue
        batch_id = item.get("batch_id")
        priority_index = item.get("priority_index")
        if batch_id is None or priority_index is None:
            continue
        entity_id = f"inbox:{batch_id}:{priority_index}"
        href = item.get("href") or build_priority_inbox_link(item)
        if not href:
            continue
        row = create_user_notification(
            user,
            notification_type=UserNotification.TYPE_INBOX_ITEM,
            entity_id=entity_id,
            title=item.get("title") or "New coach priority",
            body=item.get("drill") or item.get("proof_label") or "",
            href=href,
            meta={
                "batch_id": batch_id,
                "priority_index": priority_index,
                "linked_game_id": item.get("linked_game_id"),
            },
        )
        if row:
            created += 1
    return created


def notify_single_game_complete(user: User, game: Game, analysis: Any) -> None:
    feedback = getattr(analysis, "feedback", None)
    analysis_data = getattr(analysis, "analysis_data", None)
    coaching = _coaching_payload(feedback, analysis_data)

    moments: List[Dict[str, Any]] = []
    if isinstance(coaching, dict):
        raw = coaching.get("critical_moments")
        if isinstance(raw, list):
            moments = [row for row in raw if isinstance(row, dict)]
    if not moments and isinstance(analysis_data, dict):
        raw = analysis_data.get("critical_moments")
        if isinstance(raw, list):
            moments = [row for row in raw if isinstance(row, dict)]

    worst_moment = moments[0] if moments else {}
    headline = str(coaching.get("headline") or "").strip()
    title = _email_subject(headline, worst_moment)
    move_number = worst_moment.get("move_number")
    href = f"/game/{game.id}/analysis?mode=review"
    if move_number:
        href = f"{href}&move={move_number}"

    create_user_notification(
        user,
        notification_type=UserNotification.TYPE_SINGLE_COMPLETE,
        entity_id=f"game:{game.id}",
        title=title,
        body=headline or "Your depth-20 review is ready.",
        href=href,
        meta={"game_id": game.id, "move_number": move_number},
    )


def notify_batch_complete(user: User, batch_report: BatchAnalysisReport) -> None:
    if batch_report.status not in ("completed", "partial"):
        return

    batch_id = batch_report.id
    coaching = (
        batch_report.coaching_report
        if isinstance(batch_report.coaching_report, dict)
        else {}
    )
    snippet = str(coaching.get("executive_summary") or "")[:220]
    worst = worst_moment_summary(batch_report)
    deep_href = build_worst_moment_deep_review_url(batch_report)
    href = deep_href or f"/batch-report/{batch_id}"
    if href.startswith("http"):
        from urllib.parse import urlparse

        parsed = urlparse(href)
        href = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    if "/game/" in href and "mode=review" not in href:
        href = f"{href}&mode=review" if "?" in href else f"{href}?mode=review"

    title = f"Batch coach ready — {batch_report.games_count} games"
    body = snippet or "Your batch report and coaching priorities are ready."

    create_user_notification(
        user,
        notification_type=UserNotification.TYPE_BATCH_COMPLETE,
        entity_id=f"batch:{batch_id}",
        title=title,
        body=body,
        href=href,
        meta={
            "batch_id": batch_id,
            "worst_move": worst.get("move_number"),
        },
    )

    seed_inbox_notifications(user)
    notify_fix_rate_for_batch(user, batch_report)


def notify_fix_rate_for_batch(user: User, batch_report: BatchAnalysisReport) -> None:
    previous = (
        BatchAnalysisReport.objects.filter(
            user=user,
            status__in=["completed", "partial"],
            pk__lt=batch_report.pk,
        )
        .order_by("-pk")
        .first()
    )
    if not previous:
        return

    payload = build_fix_rate_payload(batch_report, previous)
    if not payload.get("show") or int(payload.get("fixed_count") or 0) <= 0:
        return

    create_user_notification(
        user,
        notification_type=UserNotification.TYPE_FIX_RATE,
        entity_id=f"fix_rate:{batch_report.id}",
        title=payload.get("headline") or "Patterns improved since your last batch",
        body=payload.get("tooltip") or "",
        href=f"/batch-report/{batch_report.id}",
        meta={
            "batch_id": batch_report.id,
            "fixed_count": payload.get("fixed_count"),
            "total_count": payload.get("total_count"),
        },
    )
