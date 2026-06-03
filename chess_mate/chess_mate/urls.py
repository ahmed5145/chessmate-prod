"""
URL Configuration for ChessMate project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from typing import Any, Callable

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import include, path, re_path

# Define type for views to prevent linter errors
ViewType = Callable[[HttpRequest], Any]

# Import health check views directly with error handling
try:
    # Import the views directly from the core module
    from core.views import detailed_health_check, health_check, readiness_check
except ImportError:
    # Fallback for testing: define stub health check views
    def health_check(request: HttpRequest) -> JsonResponse:
        return JsonResponse({"status": "ok"})

    def detailed_health_check(request: HttpRequest) -> JsonResponse:
        return JsonResponse({"status": "ok", "details": {}})

    def readiness_check(request: HttpRequest) -> JsonResponse:
        return JsonResponse({"status": "ready"})


def spa_index(request: HttpRequest) -> HttpResponse:
    """Serve the React SPA (client-side routes like /login, /dashboard)."""
    return render(request, "index.html")


urlpatterns = [
    # Health check endpoints at root level for load balancers
    path("health/", health_check, name="health-check"),
    path("readiness/", readiness_check, name="readiness-check"),
    # Admin and API endpoints
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),  # Include core.urls for API v1
    # Legacy frontend builds used baseURL /api + paths /api/v1/... 
    # -- remove after all clients updated
    path("api/api/v1/", include("core.urls")),
    path("api/system/", include("core.urls_system")),  # Legacy API prefix
    # React SPA (must be last; excludes api/admin/health/static/media)
    re_path(
        r"^(?!api/|admin/|health/|readiness/|static/|media/).*$",
        spa_index,
        name="spa-index",
    ),
    path("", spa_index, name="index"),
]

# Add static and media URLs in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Add debug toolbar if available
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
