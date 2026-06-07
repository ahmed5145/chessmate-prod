from core.batch_rerun import BatchRerunError, queue_batch_rerun
from core.models import BatchAnalysisReport
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Re-run Stockfish batch analysis for completed/partial/failed reports "
        "(picks up new classification logic; no credit charge)."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--id", type=int, dest="batch_id", help="BatchAnalysisReport primary key")
        group.add_argument(
            "--all-completed",
            action="store_true",
            help="Rerun every completed or partial batch (newest first)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="With --all-completed, cap how many batches to queue (0 = all)",
        )
        parser.add_argument(
            "--eager",
            action="store_true",
            help="Run inline in this process (local dev; no Celery worker needed)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List matching batches without queueing",
        )

    def handle(self, *args, **options):
        if options.get("all_completed"):
            self._rerun_all(options)
            return

        try:
            report = BatchAnalysisReport.objects.get(pk=options["batch_id"])
        except BatchAnalysisReport.DoesNotExist as exc:
            raise CommandError(f"No batch with id={options['batch_id']}") from exc

        self._rerun_one(report, options)

    def _rerun_all(self, options):
        qs = BatchAnalysisReport.objects.filter(status__in=["completed", "partial"]).order_by("-created_at")
        limit = int(options.get("limit") or 0)
        if limit > 0:
            qs = qs[:limit]
        reports = list(qs)

        if not reports:
            self.stdout.write(self.style.WARNING("No completed/partial batches to rerun."))
            return

        self.stdout.write(f"Found {len(reports)} batch(es) to rerun.")
        if options.get("dry_run"):
            for report in reports:
                self.stdout.write(
                    f"  id={report.pk} user_id={report.user_id} games={report.games_count} "
                    f"status={report.status} created={report.created_at.isoformat()}"
                )
            self.stdout.write(self.style.WARNING("Dry run only — no changes made."))
            return

        ok = 0
        for report in reports:
            try:
                message = queue_batch_rerun(report, eager=bool(options.get("eager")))
                self.stdout.write(self.style.SUCCESS(message))
                ok += 1
            except BatchRerunError as exc:
                self.stdout.write(self.style.ERROR(f"Batch {report.pk}: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"Queued or ran {ok}/{len(reports)} batch(es)."))

    def _rerun_one(self, report: BatchAnalysisReport, options):
        if options.get("dry_run"):
            self.stdout.write(
                f"Would rerun batch id={report.pk} status={report.status} "
                f"games={report.games_count} task_id={report.task_id}"
            )
            return

        try:
            message = queue_batch_rerun(report, eager=bool(options.get("eager")))
        except BatchRerunError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(message))
