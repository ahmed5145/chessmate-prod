"""Public, unauthenticated site metadata for marketing pages."""

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def public_site_config_view(request):
    """GET /api/v1/public/site-config/ — support contact and beta framing."""
    support = (
        getattr(settings, "SUPPORT_EMAIL", "")
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        or "support@chess-mate.online"
    ).strip()
    legal_entity = getattr(settings, "LEGAL_ENTITY_NAME", "").strip()
    demo_share_token = (getattr(settings, "DEMO_BATCH_SHARE_TOKEN", "") or "").strip()
    return Response(
        {
            "support_email": support,
            "signup_bonus_credits": int(getattr(settings, "SIGNUP_BONUS_CREDITS", 15)),
            "demo_batch_share_token": demo_share_token or None,
            "batch_default_games": int(getattr(settings, "BATCH_DEFAULT_GAMES", 10)),
            "batch_sends_completion_email": bool(getattr(settings, "BATCH_SEND_COMPLETE_EMAIL", True)),
            "single_game_sends_completion_email": bool(
                getattr(settings, "SINGLE_GAME_SEND_COMPLETE_EMAIL", True)
            ),
            "batch_eta_minutes_per_game_low": int(getattr(settings, "BATCH_ETA_MINUTES_PER_GAME_LOW", 3)),
            "batch_eta_minutes_per_game_high": int(getattr(settings, "BATCH_ETA_MINUTES_PER_GAME_HIGH", 5)),
            "batch_eta_coaching_buffer_minutes": int(getattr(settings, "BATCH_ETA_COACHING_BUFFER_MINUTES", 2)),
            "max_batches_per_user_per_day": int(getattr(settings, "MAX_BATCHES_PER_USER_PER_DAY", 3)),
            "site_name": "ChessMate",
            "beta": True,
            "legal_entity_name": legal_entity,
            "legal_entity_incorporated": bool(legal_entity),
            "legal_governing_law": getattr(
                settings,
                "LEGAL_ENTITY_JURISDICTION",
                "the State of Delaware, United States",
            ).strip(),
            "legal_entity_address": getattr(settings, "LEGAL_ENTITY_ADDRESS", "").strip(),
        }
    )
