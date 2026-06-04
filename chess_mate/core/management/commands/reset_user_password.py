from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reset a user's password (and optionally grant Django admin access)."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="User email (case-insensitive)")
        parser.add_argument("password", type=str, help="New password")
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Also set is_staff and is_superuser (Django admin login)",
        )

    def handle(self, *args, **options):
        email = options["email"].strip()
        password = options["password"]
        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with email {email}") from exc

        user.set_password(password)
        if options["superuser"]:
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save(update_fields=["password", "is_staff", "is_superuser", "is_active"])
        else:
            user.save(update_fields=["password"])

        flags = []
        if user.is_superuser:
            flags.append("superuser")
        if user.is_staff:
            flags.append("staff")
        self.stdout.write(
            self.style.SUCCESS(
                f"Password updated for {user.username} ({email})" + (f" — now {', '.join(flags)}" if flags else "")
            )
        )
