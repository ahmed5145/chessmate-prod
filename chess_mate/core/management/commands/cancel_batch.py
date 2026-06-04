from core.batch_credits import refund_batch_credits_on_hard_fail
from core.models import BatchAnalysisReport
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Mark a stuck batch as failed (by database id or Celery task_id)."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--id", type=int, dest="batch_id", help="BatchAnalysisReport primary key")
        group.add_argument("--task-id", type=str, dest="task_id", help="Batch task_id (UUID string)")
        parser.add_argument(
            "--reason",
            type=str,
            default="Cancelled manually",
            help="Reason stored in failed_games metadata",
        )

    def handle(self, *args, **options):
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

        if report.status in ("completed", "partial"):
            raise CommandError(f"Batch id={report.pk} is already {report.status}; not cancelling.")

        previous = report.status
        report.status = "failed"
        failed = list(report.failed_games or [])
        failed.append({"game_id": "_batch", "error": options["reason"]})
        report.failed_games = failed
        report.save(update_fields=["status", "failed_games", "updated_at"])
        refunded = refund_batch_credits_on_hard_fail(report)

        self.stdout.write(
            self.style.SUCCESS(
                f"Batch id={report.pk} task_id={report.task_id}: {previous} -> failed ({options['reason']})"
                + (f"; refunded {refunded} credits" if refunded else "")
            )
        )
