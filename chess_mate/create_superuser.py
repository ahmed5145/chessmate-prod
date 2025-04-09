import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.settings_dev")
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


def create_superuser():
    try:
        with transaction.atomic():
            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser(username="admin", email="admin@example.com", password="admin")
                print("Superuser created successfully!")
            else:
                print("Superuser already exists!")
    except Exception as e:
        print(f"Error creating superuser: {str(e)}")


if __name__ == "__main__":
    create_superuser()
