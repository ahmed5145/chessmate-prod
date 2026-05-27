"""
URL configuration for system-related endpoints.
"""

from django.urls import path

from .health_checks import system_status_view
from .util_views import (
    api_documentation,
    debug_request,
    get_server_time,
    get_system_constants,
    health_check,
    openapi_spec,
    rate_limiter_info,
    trigger_error,
    version_check,
)
from .views import app_info, check_task_status, clear_cache

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("status/", system_status_view, name="system_status"),
    path("cache/clear/", clear_cache, name="clear_cache"),
    path("tasks/status/", check_task_status, name="check_task_status"),
    path("info/", app_info, name="app_info"),
    path("constants/", get_system_constants, name="get_system_constants"),
    path("version/", version_check, name="version"),
    path("version/", version_check, name="version_check"),
    path("time/", get_server_time, name="get_server_time"),
    path("debug/", debug_request, name="debug_request"),
    path("trigger-error/", trigger_error, name="trigger_error"),
    path("rate-limiter-info/", rate_limiter_info, name="rate_limiter_info"),
    path("docs/", api_documentation, name="api_docs"),
    path("docs/openapi.json", openapi_spec, {"format": "json"}, name="openapi_json"),
    path("docs/openapi.yaml", openapi_spec, {"format": "yaml"}, name="openapi_yaml"),
]
