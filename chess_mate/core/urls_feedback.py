"""
URL configuration for feedback-related endpoints.
"""

from django.urls import path

from . import feedback_views

urlpatterns = [
    path("comparative/", feedback_views.generate_comparative_feedback, name="generate_comparative_feedback"),
    path("improvement/", feedback_views.get_improvement_suggestions, name="get_improvement_suggestions"),
]
