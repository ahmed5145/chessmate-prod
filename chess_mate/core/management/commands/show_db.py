from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Show which database Django is using (verify before grant_credits / reset_user_password)."

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        self.stdout.write(f"ENVIRONMENT={getattr(settings, 'ENVIRONMENT', '?')}")
        self.stdout.write(f"ENGINE={db.get('ENGINE')}")
        self.stdout.write(f"HOST={db.get('HOST')}")
        self.stdout.write(f"NAME={db.get('NAME')}")
        self.stdout.write(f"USER={db.get('USER')}")

        try:
            User = get_user_model()
            self.stdout.write(f"auth_user count={User.objects.count()}")
        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(
                    f"Could not connect to database: {exc}. "
                    "If running from your PC, add RDS inbound PostgreSQL 5432 from My IP."
                )
            )
