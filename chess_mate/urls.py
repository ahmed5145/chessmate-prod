"""
URL configuration for ChessMate project.

This is a minimal configuration for testing purposes.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin  # type: ignore
from django.shortcuts import render
from django.urls import include, path  # type: ignore

# Import directly from the package-qualified core module with appropriate error handling
try:
    from chess_mate.core.share_preview import share_game_moment_page
    from chess_mate.core.views import health_check as health_check_view
    from chess_mate.core.views import readiness_check as readiness_check_view
except ImportError:
    from core.share_preview import share_game_moment_page
    from core.views import health_check as health_check_view
    from core.views import readiness_check as readiness_check_view


urlpatterns = [
    # Serve a small landing page at root (avoid redirect to admin for public)
    path("", lambda request: render(request, "index.html"), name="index"),
    # Health check endpoints at root level for load balancers and monitoring
    path("health/", health_check_view, name="health-check"),
    path("readiness/", readiness_check_view, name="readiness-check"),
    # Public share pages — server-rendered OG tags for social crawlers
    path(
        "share/game-moment/<uuid:share_token>",
        share_game_moment_page,
        name="share-game-moment-page",
    ),
    path(
        "share/game-moment/<uuid:share_token>/",
        share_game_moment_page,
        name="share-game-moment-page-slash",
    ),
    # Admin and API endpoints
    path("admin/", admin.site.urls),
    path("api/v1/", include("chess_mate.core.urls")),
]

# Add debug-related URLs in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Add debug toolbar if available - will be installed by install_project.py
    try:
        import debug_toolbar  # type: ignore

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
