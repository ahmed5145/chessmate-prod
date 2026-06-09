"""Tests for coach persona preference (SRG-26)."""

from django.contrib.auth.models import User
from django.test import TestCase

from core.coach_persona import (
    COACH_PERSONA_KEY,
    coach_persona_prompt_modifier,
    resolve_coach_persona,
)
from core.models import Profile
from core.tests.profile_helpers import ensure_profile


class TestCoachPersona(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="personauser", password="pass")
        self.profile = ensure_profile(self.user, credits=10)

    def test_defaults_to_encouraging(self):
        assert resolve_coach_persona(self.profile) == "encouraging"

    def test_direct_persona_from_preferences(self):
        profile = Profile.objects.get(user=self.user)
        profile.preferences = {COACH_PERSONA_KEY: "direct"}
        profile.save(update_fields=["preferences"])
        assert resolve_coach_persona(profile) == "direct"

    def test_invalid_persona_falls_back(self):
        profile = Profile.objects.get(user=self.user)
        profile.preferences = {COACH_PERSONA_KEY: "sarcastic"}
        profile.save(update_fields=["preferences"])
        assert resolve_coach_persona(profile) == "encouraging"

    def test_prompt_modifier_differs_by_persona(self):
        direct = coach_persona_prompt_modifier("direct")
        encouraging = coach_persona_prompt_modifier("encouraging")
        assert "blunt" in direct.lower()
        assert "supportive" in encouraging.lower()
        assert direct != encouraging
