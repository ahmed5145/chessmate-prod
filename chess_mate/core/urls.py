"""
URL configuration for the ChessMate application.
"""

from django.urls import include, path
from core import views
from core import game_views

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
    path('v1/games/<int:game_id>/analysis/status/', game_views.get_task_status, name='game_analysis_status'),
]
