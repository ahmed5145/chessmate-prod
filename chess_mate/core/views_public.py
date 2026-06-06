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
    return Response(
        {
            "support_email": support,
            "signup_bonus_credits": int(getattr(settings, "SIGNUP_BONUS_CREDITS", 15)),
            "batch_default_games": int(getattr(settings, "BATCH_DEFAULT_GAMES", 10)),
            "site_name": "ChessMate",
            "beta": True,
        }
    )
