from core.models import Profile
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Add credits to a user profile by email address."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="User email (case-insensitive)")
        parser.add_argument("amount", type=int, help="Credits to add (can be negative to deduct)")

    def handle(self, *args, **options):
        email = options["email"].strip()
        amount = options["amount"]
        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with email {email}") from exc

        profile, _ = Profile.objects.get_or_create(user=user)
        before = profile.credits
        profile.credits = before + amount
        profile.save(update_fields=["credits"])

        self.stdout.write(
            self.style.SUCCESS(
                f"User {user.username} ({email}): credits {before} -> {profile.credits} ({amount:+d})"
            )
        )
