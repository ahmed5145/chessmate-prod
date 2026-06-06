"""
Apply credits for a completed Stripe Checkout session (ops recovery).

Use when the user paid but /confirm-purchase/ did not run (expired JWT, old redirect URL, etc.).
"""

from core.models import Profile, Transaction
from core.payment import PaymentProcessor
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F


class Command(BaseCommand):
    help = "Grant credits from a paid Stripe Checkout session_id (manual recovery)."

    def add_arguments(self, parser):
        parser.add_argument("session_id", type=str, help="Stripe Checkout session id (cs_test_... or cs_live_...)")
        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
            dest="user_id",
            help="User id to credit (must match session metadata unless --force)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Credit user even if session metadata user_id differs",
        )
        parser.add_argument("--dry-run", action="store_true", help="Verify session only; do not write DB")

    def handle(self, *args, **options):
        if not getattr(settings, "STRIPE_SECRET_KEY", ""):
            raise CommandError(
                "STRIPE_SECRET_KEY is not set in this environment.\n"
                "Add it to your local .env / .env.production, or run one-off:\n"
                "  set STRIPE_SECRET_KEY=sk_test_...   (cmd)\n"
                "  $env:STRIPE_SECRET_KEY='sk_test_...' (PowerShell)\n"
                "Use the same test secret key configured on Elastic Beanstalk."
            )

        session_id = (options["session_id"] or "").strip()
        if not session_id:
            raise CommandError("session_id is required")

        User = get_user_model()
        try:
            user = User.objects.get(pk=options["user_id"])
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with id={options['user_id']}") from exc

        try:
            payment_data = PaymentProcessor.verify_payment(session_id)
        except Exception as exc:
            raise CommandError(f"Stripe verify failed: {exc}") from exc

        if not payment_data:
            raise CommandError("Session is not paid yet. Check Stripe Dashboard → Payments.")

        meta_uid = payment_data.get("user_id")
        if meta_uid is not None and str(meta_uid) != str(user.id) and not options["force"]:
            raise CommandError(
                f"Session metadata user_id={meta_uid} does not match --user-id={user.id}. " "Use --force to override."
            )

        credits_to_add = int(payment_data.get("credits") or 0)
        if credits_to_add <= 0:
            raise CommandError("Session has no credits in metadata.")

        existing = Transaction.objects.filter(user=user, stripe_payment_id=session_id, status="completed").first()
        if existing:
            profile = Profile.objects.get(user=user)
            self.stdout.write(
                self.style.WARNING(
                    f"Already applied: {credits_to_add} credits for session {session_id}. "
                    f"Current balance={profile.credits}"
                )
            )
            return

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: would add {credits_to_add} credits to id={user.id} {user.username} "
                    f"for session {session_id}"
                )
            )
            return

        with transaction.atomic():
            profile, _ = Profile.objects.select_for_update().get_or_create(user=user)
            profile.credits = F("credits") + credits_to_add
            profile.save(update_fields=["credits"])
            profile.refresh_from_db(fields=["credits"])

            amount_dollars = float(payment_data.get("amount") or 0) / 100.0
            Transaction.objects.create(
                user=user,
                transaction_type="purchase",
                amount=amount_dollars,
                credits=credits_to_add,
                status="completed",
                stripe_payment_id=session_id,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Added {credits_to_add} credits to id={user.id} {user.username}. " f"New balance={profile.credits}"
            )
        )
