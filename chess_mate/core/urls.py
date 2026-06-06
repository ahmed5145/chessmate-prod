"""
URL configuration for the ChessMate application.
"""

from django.urls import include, path

from . import game_views, views_credits, views_public

# Use this pattern to create a modular URL structure
urlpatterns = [
    # Include URLs from different modules
    path("auth/", include("core.urls_auth")),
    path("profile/", include("core.urls_profile")),
    path("games/", include("core.urls_games")),
    path("dashboard/", include("core.urls_dashboard")),
    path("feedback/", include("core.urls_feedback")),
    path("health/", include("core.urls_health")),
    path("system/", include("core.urls_system")),
    path("batches/", include("core.urls_batches")),
    path("credits/", include("core.urls_credits")),
    path("purchase-credits/", views_credits.purchase_credits_checkout_view, name="purchase-credits"),
    path("confirm-purchase/", views_credits.confirm_purchase_view, name="confirm-purchase"),
    path("webhooks/stripe/", views_credits.stripe_webhook_view, name="stripe-webhook"),
    path("public/site-config/", views_public.public_site_config_view, name="public-site-config"),
    path(
        "v1/games/<int:game_id>/analysis/status/",
        game_views.get_task_status,
        name="game_analysis_status",
    ),
]
