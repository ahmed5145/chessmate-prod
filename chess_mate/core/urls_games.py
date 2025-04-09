"""
URL configuration for game-related endpoints.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import game_views

# Create a router for DRF ViewSets
router = DefaultRouter()
router.register(r"", game_views.GameViewSet, basename="game")

urlpatterns = [
    # Function-based views
    path("user/", game_views.get_user_games, name="user_games"),
    path("import/", game_views.import_game, name="import_game"),
    path("import/external/", game_views.import_external_games, name="import_external_games"),
    path("fetch/", game_views.import_external_games, name="fetch_games"),
    path("search/", game_views.search_external_player, name="search_external_player"),
    path("<int:game_id>/analyze/", game_views.analyze_game, name="analyze_game"),
    path("<int:game_id>/analysis/status/", game_views.get_task_status, name="check_analysis_status"),
    path("<int:game_id>/analysis/", game_views.get_game_analysis, name="get_game_analysis"),
    path("batch-analyze/", game_views.batch_analyze_games, name="batch_analyze"),
    path("batch-status/", game_views.batch_get_analysis_status, name="batch_status"),
]

# Add router URLs to urlpatterns
urlpatterns += router.urls
