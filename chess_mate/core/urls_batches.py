"""
URL configuration for batch analysis endpoints (PRD section 11, Step 9).
"""

from django.urls import path

from . import views_batches

urlpatterns = [
    path("", views_batches.batch_collection_view, name="batch-collection"),
    path("<int:batch_id>/status/", views_batches.batch_status_view, name="batch-status"),
    path("<int:batch_id>/report/", views_batches.batch_report_view, name="batch-report"),
    path(
        "<int:batch_id>/regenerate-coaching/",
        views_batches.batch_regenerate_coaching_view,
        name="batch-regenerate-coaching",
    ),
]
