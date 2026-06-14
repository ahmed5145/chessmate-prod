"""Launch funnel metrics from BatchAnalysisReport and referrals (no analytics product required)."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from core.models import BatchAnalysisReport, Profile, ReferralRedemption
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from django.utils import timezone

User = get_user_model()

COMPLETED_STATUSES = ("completed", "partial")
MIN_GAMES = 5


class Command(BaseCommand):
    help = "Print launch metrics: signups, first batches, second batch within N days, referrals."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Only count users who signed up in the last N days (default 30). Use 0 for all time.",
        )
        parser.add_argument(
            "--second-batch-window",
            type=int,
            default=14,
            help="Days after first batch to count a second batch as retention (default 14).",
        )

    def handle(self, *args, **options):
        days = int(options["days"])
        window_days = int(options["second_batch_window"])
        now = timezone.now()
        since = now - timedelta(days=days) if days > 0 else None

        users = User.objects.all()
        if since:
            users = users.filter(date_joined__gte=since)

        total_users = users.count()
        verified_users = Profile.objects.filter(user__in=users, email_verified=True).count()

        batches = BatchAnalysisReport.objects.filter(
            user__in=users,
            status__in=COMPLETED_STATUSES,
            games_count__gte=MIN_GAMES,
        )

        first_batch_by_user = (
            batches.values("user_id").annotate(first_at=Min("created_at"), batch_count=Count("id")).order_by()
        )

        users_with_first_batch = first_batch_by_user.count()

        # Second batch within window after first
        batch_dates: dict[int, list] = defaultdict(list)
        for row in batches.values("user_id", "created_at").order_by("user_id", "created_at"):
            batch_dates[row["user_id"]].append(row["created_at"])

        second_within_window = 0
        for user_id, dates in batch_dates.items():
            if len(dates) < 2:
                continue
            dates.sort()
            first_at = dates[0]
            cutoff = first_at + timedelta(days=window_days)
            if any(d > first_at and d <= cutoff for d in dates[1:]):
                second_within_window += 1

        referrals = ReferralRedemption.objects.all()
        if since:
            referrals = referrals.filter(created_at__gte=since)

        self.stdout.write(self.style.SUCCESS("ChessMate launch metrics"))
        if since:
            self.stdout.write(f"  Window: last {days} days (since {since.date()})")
        else:
            self.stdout.write("  Window: all time")
        self.stdout.write(f"  Signups: {total_users}")
        self.stdout.write(f"  Email verified: {verified_users}")
        self.stdout.write(f"  First batch completed (≥{MIN_GAMES} games): {users_with_first_batch}")
        self.stdout.write(f"  Second batch within {window_days} days of first: {second_within_window}")
        if users_with_first_batch:
            rate = round(100 * second_within_window / users_with_first_batch, 1)
            self.stdout.write(f"  Second-batch rate: {rate}%")
        self.stdout.write(f"  Referral redemptions: {referrals.count()}")
