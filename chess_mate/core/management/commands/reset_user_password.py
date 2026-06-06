from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reset a user's password (and optionally grant Django admin access)."

    def add_arguments(self, parser):
        parser.add_argument(
            "email",
            nargs="?",
            default="",
            type=str,
            help="User email (case-insensitive). Omit when using --user-id.",
        )
        parser.add_argument("password", type=str, help="New password")
        parser.add_argument(
            "--user-id",
            type=int,
            dest="user_id",
            help="Target user by id (overrides email; use when duplicate emails exist)",
        )
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Also set is_staff and is_superuser (Django admin login)",
        )

    def handle(self, *args, **options):
        password = options["password"]
        User = get_user_model()

        if options.get("user_id"):
            try:
                user = User.objects.get(pk=options["user_id"])
            except User.DoesNotExist as exc:
                raise CommandError(f"No user with id={options['user_id']}") from exc
            email = user.email
        else:
            email = (options.get("email") or "").strip()
            if not email:
                raise CommandError("Provide email or --user-id")
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist as exc:
                raise CommandError(f"No user with email {email}") from exc
            except User.MultipleObjectsReturned as exc:
                matches = User.objects.filter(email__iexact=email).order_by("id")
                lines = [
                    f"  id={u.id} username={u.username!r} staff={u.is_staff} super={u.is_superuser}"
                    for u in matches
                ]
                raise CommandError(
                    f"Multiple users have email {email}. Pick one with --user-id:\n"
                    + "\n".join(lines)
                    + f"\n\nExample: python manage.py list_users {email}"
                ) from exc

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
                f"Password updated for id={user.id} {user.username} ({email})"
                + (f" — now {', '.join(flags)}" if flags else "")
            )
        )
