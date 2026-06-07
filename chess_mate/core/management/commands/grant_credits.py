from core.models import Profile
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Add credits to a user profile by email address."

    def add_arguments(self, parser):
        parser.add_argument("email", nargs="?", default="", type=str, help="User email (case-insensitive)")
        parser.add_argument("amount", type=int, help="Credits to add (can be negative to deduct)")
        parser.add_argument("--user-id", type=int, dest="user_id", help="Target user by id (overrides email)")

    def handle(self, *args, **options):
        amount = options["amount"]
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
                raise CommandError(
                    f"Multiple users have email {email}. Use --user-id (see: python manage.py list_users {email})"
                ) from exc

        profile, _ = Profile.objects.get_or_create(user=user)
        before = profile.credits
        profile.credits = before + amount
        profile.save(update_fields=["credits"])

        self.stdout.write(
            self.style.SUCCESS(f"User {user.username} ({email}): credits {before} -> {profile.credits} ({amount:+d})")
        )
