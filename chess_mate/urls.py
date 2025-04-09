"""
URL configuration for ChessMate project.

This is a minimal configuration for testing purposes.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin  # type: ignore
from django.urls import include, path  # type: ignore
from django.views.generic import RedirectView
from django.http import JsonResponse, HttpRequest
from rest_framework.response import Response
from typing import Any, Callable

# Import directly from core.views with appropriate error handling
try:
    # Import the views directly from the core module
    from core.views import health_check as health_check_view
    from core.views import detailed_health_check as readiness_check_view
except ImportError:
    # For testing purposes, define stub views if the real ones aren't available
    # Use explicit typing to avoid incompatible redefinition errors
    def health_check_view(request: HttpRequest) -> JsonResponse:  # type: ignore
        return JsonResponse({"status": "ok"})
    
    def readiness_check_view(request: HttpRequest) -> JsonResponse:  # type: ignore
        return JsonResponse({"status": "ready"})

urlpatterns = [
    # Redirect the root URL to the admin interface or API for now
    path("", RedirectView.as_view(url="/admin/", permanent=False), name="index"),
    
    # Health check endpoints at root level for load balancers and monitoring
    path("health/", health_check_view, name="health-check"),
    path("readiness/", readiness_check_view, name="readiness-check"),
    
    # Admin and API endpoints
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),  # This should import from chess_mate.core.urls
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
