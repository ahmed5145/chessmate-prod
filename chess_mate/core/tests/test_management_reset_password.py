import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_reset_user_password_duplicate_email_lists_ids():
    User = get_user_model()
    User.objects.create_user(username="u1", email="dup@example.com", password="old")
    User.objects.create_user(username="u2", email="dup@example.com", password="old")

    with pytest.raises(CommandError) as exc:
        call_command("reset_user_password", "dup@example.com", "newpass123")

    assert "Multiple users" in str(exc.value)
    assert "id=" in str(exc.value)


@pytest.mark.django_db
def test_reset_user_password_by_user_id():
    User = get_user_model()
    user = User.objects.create_user(username="admin1", email="a@b.com", password="old")

    call_command("reset_user_password", "", "newpass123", user_id=user.id, superuser=True)

    user.refresh_from_db()
    assert user.is_superuser is True
    assert user.check_password("newpass123")
