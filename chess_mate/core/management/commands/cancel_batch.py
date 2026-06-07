from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.batch_credits import refund_batch_credits_on_hard_fail
from core.models import BatchAnalysisReport


class Command(BaseCommand):
    help = "Mark a stuck batch as failed (by database id, Celery task_id, or bulk in_progress)."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--id", type=int, dest="batch_id", help="BatchAnalysisReport primary key")
        group.add_argument("--task-id", type=str, dest="task_id", help="Batch task_id (UUID string)")
        group.add_argument(
            "--all-in-progress",
            action="store_true",
            help="Cancel every batch with status in_progress (optionally filtered by age)",
        )
        parser.add_argument(
            "--include-pending",
            action="store_true",
            help="With --all-in-progress, also cancel pending batches",
        )
        parser.add_argument(
            "--older-than-hours",
            type=float,
            default=0,
            help="With --all-in-progress, only batches created at least N hours ago (0 = all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List matching batches without updating them",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default="Cancelled manually",
            help="Reason stored in failed_games metadata",
        )

    def handle(self, *args, **options):
        if options.get("all_in_progress"):
            self._cancel_all_in_progress(options)
            return

        if options.get("batch_id"):
            try:
                report = BatchAnalysisReport.objects.get(pk=options["batch_id"])
            except BatchAnalysisReport.DoesNotExist as exc:
                raise CommandError(f"No batch with id={options['batch_id']}") from exc
        else:
            task_id = options["task_id"].strip()
            qs = BatchAnalysisReport.objects.filter(task_id=task_id)
            if qs.count() != 1:
                raise CommandError(f"Expected exactly one batch for task_id={task_id}, found {qs.count()}")
            report = qs.get()

        self._cancel_report(report, options["reason"])

    def _cancel_all_in_progress(self, options):
        statuses = ["in_progress"]
        if options.get("include_pending"):
            statuses.append("pending")

        qs = BatchAnalysisReport.objects.filter(status__in=statuses).order_by("created_at")
        older_than_hours = float(options.get("older_than_hours") or 0)
        if older_than_hours > 0:
            cutoff = timezone.now() - timedelta(hours=older_than_hours)
            qs = qs.filter(created_at__lte=cutoff)

        reports = list(qs)
        if not reports:
            self.stdout.write(self.style.WARNING("No matching batches to cancel."))
            return

        self.stdout.write(f"Found {len(reports)} batch(es) with status in {statuses}.")
        if options.get("dry_run"):
            for report in reports:
                self.stdout.write(
                    f"  id={report.pk} user_id={report.user_id} status={report.status} "
                    f"created={report.created_at.isoformat()} task_id={report.task_id}"
                )
            self.stdout.write(self.style.WARNING("Dry run only — no changes made."))
            return

        cancelled = 0
        refunded_total = 0
        for report in reports:
            refunded = self._cancel_report(report, options["reason"])
            cancelled += 1
            refunded_total += refunded or 0

        self.stdout.write(
            self.style.SUCCESS(
                f"Cancelled {cancelled} batch(es)."
                + (f" Refunded {refunded_total} credits total." if refunded_total else "")
            )
        )

    def _cancel_report(self, report: BatchAnalysisReport, reason: str) -> int:
        if report.status in ("completed", "partial"):
            raise CommandError(f"Batch id={report.pk} is already {report.status}; not cancelling.")

        previous = report.status
        report.status = "failed"
        failed = list(report.failed_games or [])
        failed.append({"game_id": "_batch", "error": reason})
        report.failed_games = failed
        report.save(update_fields=["status", "failed_games", "updated_at"])
        refunded = refund_batch_credits_on_hard_fail(report)

        self.stdout.write(
            self.style.SUCCESS(
                f"Batch id={report.pk} task_id={report.task_id}: {previous} -> failed ({reason})"
                + (f"; refunded {refunded} credits" if refunded else "")
            )
        )
        return refunded or 0
