"""Post-first-batch celebration modal payload (SRG-23)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.contrib.auth.models import User

from .models import BatchAnalysisReport, Profile
from .priority_inbox import get_priority_inbox_payload

FIRST_BATCH_CELEBRATED_KEY = "first_batch_celebrated_at"


def _has_coaching(batch_report: BatchAnalysisReport) -> bool:
    coaching = batch_report.coaching_report
    if not isinstance(coaching, dict) or not coaching:
        return False
    return bool(
        coaching.get("executive_summary")
        or coaching.get("top_3_priorities")
        or coaching.get("one_thing_to_do_today")
    )


def eligible_batches_for_user(user: User):
    return BatchAnalysisReport.objects.filter(
        user=user,
        status__in=["completed", "partial"],
        games_count__gte=5,
    ).order_by("pk")


def is_first_eligible_batch(batch_report: BatchAnalysisReport) -> bool:
    if batch_report.games_count < 5:
        return False
    if not _has_coaching(batch_report):
        return False
    qs = eligible_batches_for_user(batch_report.user)
    first = qs.first()
    return first is not None and first.pk == batch_report.pk and qs.count() == 1


def user_has_celebrated_first_batch(profile: Profile) -> bool:
    return bool(profile.get_preference(FIRST_BATCH_CELEBRATED_KEY))


def mark_first_batch_celebrated(profile: Profile) -> None:
    from django.utils import timezone

    profile.set_preference(FIRST_BATCH_CELEBRATED_KEY, timezone.now().isoformat())


def build_first_batch_celebration_payload(
    batch_report: BatchAnalysisReport,
    profile: Profile,
) -> Dict[str, Any]:
    if user_has_celebrated_first_batch(profile):
        return {"show": False}
    if not is_first_eligible_batch(batch_report):
        return {"show": False}

    coaching = (
        batch_report.coaching_report
        if isinstance(batch_report.coaching_report, dict)
        else {}
    )
    headline = str(
        coaching.get("executive_summary")
        or coaching.get("one_thing_to_do_today")
        or "Your first Batch Coach report is ready."
    )[:220]

    cta_href = f"/batch-report/{batch_report.id}#batch-section-priorities"
    cta_label = "Review your #1 priority"

    inbox = get_priority_inbox_payload(profile)
    for item in inbox.get("pending_items") or []:
        if not isinstance(item, dict):
            continue
        if int(item.get("batch_id") or 0) != int(batch_report.id):
            continue
        if item.get("href"):
            cta_href = str(item["href"])
        if item.get("title"):
            cta_label = "Review your #1 priority"
        break

    return {
        "show": True,
        "headline": headline,
        "cta_label": cta_label,
        "cta_href": cta_href,
        "batch_id": batch_report.id,
    }
