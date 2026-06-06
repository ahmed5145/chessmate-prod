import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models import Profile


@pytest.mark.django_db
def test_register_grants_signup_bonus_credits(settings):
    settings.SIGNUP_BONUS_CREDITS = 15
    client = APIClient()
    response = client.post(
        "/api/v1/auth/register/",
        {
            "username": "newbeta1",
            "email": "newbeta1@example.com",
            "password": "SecurePass123!",
        },
        format="json",
    )
    assert response.status_code in (200, 201)
    user = get_user_model().objects.get(username="newbeta1")
    profile = Profile.objects.get(user=user)
    assert profile.credits == 15
