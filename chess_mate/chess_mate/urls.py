"""
URL Configuration for ChessMate project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from typing import Any, Callable

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

urlpatterns = [
    # Redirect the root URL to the admin interface or API
    path("", RedirectView.as_view(url="/admin/", permanent=False), name="index"),
    
    # Health check endpoints at root level for load balancers
    path("health/", health_check, name="health-check"),
    path("readiness/", readiness_check, name="readiness-check"),
    
    # Admin and API endpoints
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),  # Include core.urls for API v1
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
