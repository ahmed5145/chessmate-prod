"""URL configuration for in-app notifications."""

from django.urls import path

from . import views_notifications

urlpatterns = [
    path("", views_notifications.notifications_view, name="notifications"),
]
