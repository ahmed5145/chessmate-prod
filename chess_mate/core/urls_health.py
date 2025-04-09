"""
URL configuration for health-related endpoints.
"""

from django.urls import path

from .views import run_health_check_task
from .health_checks import (
    detailed_health_check_view,
    health_check_view,
    readiness_check_view,
    system_status_view,
)

urlpatterns = [
    path("", health_check_view, name="health_check"),
    path("detailed/", detailed_health_check_view, name="detailed_health_check"),
    path("readiness/", readiness_check_view, name="readiness_check"),
    path("run-check-task/", run_health_check_task, name="run_health_check_task"),
]
