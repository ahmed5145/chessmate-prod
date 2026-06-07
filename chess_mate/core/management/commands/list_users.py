from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Profile


class Command(BaseCommand):
    help = "List users (optionally filter by email substring) with profile credits."

    def add_arguments(self, parser):
        parser.add_argument(
            "email_contains",
            nargs="?",
            default="",
            type=str,
            help="Optional substring to filter email (case-insensitive)",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        qs = User.objects.order_by("id")
        needle = (options.get("email_contains") or "").strip()
        if needle:
            qs = qs.filter(email__icontains=needle)

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No users matched."))
            return

        for user in qs:
            try:
                credits = Profile.objects.get(user=user).credits
            except Profile.DoesNotExist:
                credits = "no profile"
            admin = "admin" if user.is_superuser else ("staff" if user.is_staff else "user")
            self.stdout.write(
                f"id={user.id} username={user.username!r} email={user.email!r} " f"credits={credits} role={admin}"
            )
