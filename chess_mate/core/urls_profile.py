"""
URL configuration for profile-related endpoints.
"""

from django.urls import path

from . import profile_views

urlpatterns = [
    path("", profile_views.profile_view, name="get_user_profile"),
    path("basic/", profile_views.fallback_profile_view, name="get_basic_profile"),
    path("minimal/", profile_views.minimal_profile_view, name="get_minimal_profile"),
    path("update/", profile_views.update_profile, name="update_user_profile"),
    path("statistics/", profile_views.get_user_statistics, name="get_user_statistics"),
    path("subscription/tiers/", profile_views.get_subscription_tiers, name="get_subscription_tiers"),
    path("subscription/create/", profile_views.create_subscription, name="create_subscription"),
    path("subscription/cancel/", profile_views.cancel_subscription, name="cancel_subscription"),
    path("credits/add/", profile_views.add_credits, name="add_credits"),
    path("webhook/stripe/", profile_views.webhook_handler, name="stripe_webhook"),
]
