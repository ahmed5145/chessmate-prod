"""
URL Configuration for ChessMate project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

import re
from typing import Any, Callable

from core.share_preview import share_game_moment_page
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.urls import include, path, re_path
from django.views.generic import RedirectView

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

    def readiness_check(request: HttpRequest) -> HttpResponse:
        return JsonResponse({"status": "ready"})


def spa_index(request: HttpRequest) -> HttpResponse:
    """Serve the React SPA (client-side routes like /login, /dashboard)."""
    return render(request, "index.html")


def admin_legacy_decoy(_request: HttpRequest) -> HttpResponse:
    """Return 404 for the default /admin path when hidden in production."""
    return HttpResponseNotFound()


def batch_legacy_report_redirect(request: HttpRequest, report_id: int) -> HttpResponse:
    """Server-side redirect for old /batch-analysis/results/report/:id URLs."""
    return redirect(f"/batch-report/{report_id}", permanent=False)


def batch_legacy_task_redirect(request: HttpRequest, task_id: str) -> HttpResponse:
    """Legacy task UUID links — send users to batch coach to pick from history."""
    if str(task_id).isdigit():
        return redirect(f"/batch-report/{task_id}", permanent=False)
    return redirect("/batch-analysis", permanent=False)


ADMIN_PATH = getattr(settings, "DJANGO_ADMIN_PATH", "admin").strip("/")
ADMIN_PREFIX = f"{ADMIN_PATH}/"

admin_urlpatterns = [
    path(ADMIN_PREFIX, admin.site.urls),
    path(ADMIN_PATH, RedirectView.as_view(url=f"/{ADMIN_PREFIX}", permanent=True)),
]

if getattr(settings, "ADMIN_HIDE_LEGACY_PATH", False):
    admin_urlpatterns = [
        path("admin/", admin_legacy_decoy),
        path("admin", admin_legacy_decoy),
    ] + admin_urlpatterns
else:
    admin_urlpatterns = [
        path("admin/", admin.site.urls),
        path("admin", RedirectView.as_view(url="/admin/", permanent=True)),
    ]

spa_excluded_prefixes = [
    "api/",
    f"{ADMIN_PREFIX}",
    "health/",
    "readiness/",
    "static/",
    "media/",
]
if not getattr(settings, "ADMIN_HIDE_LEGACY_PATH", False):
    spa_excluded_prefixes.append("admin/")

spa_exclude_pattern = "|".join(re.escape(prefix) for prefix in spa_excluded_prefixes)

urlpatterns = [
    # Health check endpoints at root level for load balancers
    path("health/", health_check, name="health-check"),
    path("readiness/", readiness_check, name="readiness-check"),
    # Admin (custom path in production; legacy /admin hidden when configured)
    *admin_urlpatterns,
    path("api/v1/", include("core.urls")),  # Include core.urls for API v1
    # Legacy frontend builds used baseURL /api + paths /api/v1/...
    # -- remove after all clients updated
    path("api/api/v1/", include("core.urls")),
    path("api/system/", include("core.urls_system")),  # Legacy API prefix
    # Legacy batch report URLs (before SPA catch-all — works even on stale frontend bundles)
    path(
        "batch-analysis/results/report/<int:report_id>/",
        batch_legacy_report_redirect,
        name="batch-legacy-report-redirect",
    ),
    path(
        "batch-analysis/results/report/<int:report_id>",
        batch_legacy_report_redirect,
    ),
    path(
        "batch-analysis/results/<str:task_id>/",
        batch_legacy_task_redirect,
        name="batch-legacy-task-redirect",
    ),
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
    # React SPA (must be last; excludes api/admin/health/static/media)
    re_path(
        rf"^(?!{spa_exclude_pattern}).*$",
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
