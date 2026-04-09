"""
URL configuration for feedback-related endpoints.
"""

from django.urls import path

from . import feedback_views

urlpatterns = [
    path("<int:game_id>/generate/", feedback_views.generate_ai_feedback, name="generate_ai_feedback"),
    path("<int:game_id>/", feedback_views.get_game_feedback, name="get_game_feedback"),
    path("all/", feedback_views.get_all_feedback, name="get_all_feedback"),
    path("<int:feedback_id>/rate/", feedback_views.rate_feedback, name="rate_feedback"),
    path("comparative/", feedback_views.generate_comparative_feedback, name="generate_comparative_feedback"),
    path("improvement/", feedback_views.get_improvement_suggestions, name="get_improvement_suggestions"),
]
