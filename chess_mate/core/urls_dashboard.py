"""
URL configuration for dashboard-related endpoints.
"""

from django.urls import path

from . import dashboard_views

urlpatterns = [
    path("", dashboard_views.dashboard_view, name="dashboard"),
    path("refresh/", dashboard_views.refresh_dashboard, name="refresh_dashboard"),
    path("performance-trend/", dashboard_views.get_performance_trend, name="get_performance_trend"),
    path("mistake-analysis/", dashboard_views.get_mistake_analysis, name="get_mistake_analysis"),
]
