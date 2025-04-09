"""
URL configuration for system-related endpoints.
"""

from django.urls import path

from .views import clear_cache, check_task_status, app_info
from .health_checks import system_status_view
from .util_views import (
    get_system_constants,
    version_check,
    get_server_time,
    debug_request,
    api_documentation,
    openapi_spec,
)

urlpatterns = [
    path("status/", system_status_view, name="system_status"),
    path("cache/clear/", clear_cache, name="clear_cache"),
    path("tasks/status/", check_task_status, name="check_task_status"),
    path("info/", app_info, name="app_info"),
    path("constants/", get_system_constants, name="get_system_constants"),
    path("version/", version_check, name="version_check"),
    path("time/", get_server_time, name="get_server_time"),
    path("debug/", debug_request, name="debug_request"),
    path("docs/", api_documentation, name="api_docs"),
    path("docs/openapi.json", openapi_spec, {"format": "json"}, name="openapi_json"),
    path("docs/openapi.yaml", openapi_spec, {"format": "yaml"}, name="openapi_yaml"),
]
