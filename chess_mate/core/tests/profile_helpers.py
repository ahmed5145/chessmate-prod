"""Test helpers for Profile rows created automatically on User signup."""

from core.models import Profile


def ensure_profile(user, **overrides):
    """Return the signal-created profile for user and apply optional field overrides."""
    profile = Profile.objects.get(user=user)
    if not overrides:
        return profile

    for field, value in overrides.items():
        setattr(profile, field, value)

    update_fields = list(overrides.keys())
    if hasattr(profile, "legacy_rating") and "legacy_rating" not in update_fields:
        update_fields.append("legacy_rating")
    profile.save(update_fields=update_fields)
    return profile
