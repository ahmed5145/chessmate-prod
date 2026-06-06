"""
Repair local migration history when core.0014 was applied before core.0013a.

Usage:
    python manage.py reconcile_payment_migrations
    python manage.py migrate
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Fake-apply core.0013a when core.0014 is already recorded (local DB repair)."

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        applied = set(recorder.applied_migrations())

        target = ("core", "0013a_state_inject_payment")
        dependent = ("core", "0014_payment_amount_float")

        if target in applied:
            self.stdout.write(self.style.SUCCESS("core.0013a_state_inject_payment is already applied."))
            return

        if dependent not in applied:
            self.stdout.write(
                self.style.WARNING(
                    "core.0014_payment_amount_float is not applied yet. "
                    "Run `python manage.py migrate` normally instead."
                )
            )
            return

        recorder.record_applied(*target)
        self.stdout.write(
            self.style.SUCCESS(
                "Recorded core.0013a_state_inject_payment as applied. " "You can now run `python manage.py migrate`."
            )
        )
