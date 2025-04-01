"""
URL configuration for the ChessMate application.
"""

from django.urls import path
from . import (
    auth_views,
    game_views,
    profile_views,
    dashboard_views,
    feedback_views,
    util_views
)

urlpatterns = [
    # Auth endpoints
    path('api/register/', auth_views.register_view, name='register'),
    path('api/login/', auth_views.login_view, name='login'),
    path('api/logout/', auth_views.logout_view, name='logout'),
    path('api/token/refresh/', auth_views.token_refresh_view, name='token_refresh'),
    path('api/reset-password/', auth_views.request_password_reset, name='request_password_reset'),
    path('api/reset-password/confirm/', auth_views.reset_password, name='reset_password'),
    path('api/verify-email/<str:token>/', auth_views.verify_email, name='verify_email'),
    
    # Profile endpoints
    path('api/profile/', profile_views.get_user_profile, name='get_user_profile'),
    path('api/profile/update/', profile_views.update_user_profile, name='update_user_profile'),
    path('api/statistics/', profile_views.get_user_statistics, name='get_user_statistics'),
    path('api/subscription/tiers/', profile_views.get_subscription_tiers, name='get_subscription_tiers'),
    path('api/subscription/create/', profile_views.create_subscription, name='create_subscription'),
    path('api/subscription/cancel/', profile_views.cancel_subscription, name='cancel_subscription'),
    path('api/credits/add/', profile_views.add_credits, name='add_credits'),
    path('api/webhook/stripe/', profile_views.webhook_handler, name='stripe_webhook'),
    
    # Game endpoints
    path('api/games/', game_views.user_games_view, name='user_games'),
    path('api/games/fetch/', game_views.fetch_games, name='fetch_games'),
    path('api/games/<int:game_id>/analyze/', game_views.analyze_game, name='analyze_game'),
    path('api/games/<int:game_id>/analysis/', game_views.get_game_analysis, name='get_game_analysis'),
    path('api/games/<int:game_id>/analysis/status/', game_views.check_analysis_status, name='check_analysis_status'),
    path('api/batch-analyze/', game_views.batch_analyze, name='batch_analyze'),
    path('api/batch-analyze/status/<str:task_id>/', game_views.check_batch_analysis_status, name='check_batch_analysis_status'),
    
    # Feedback endpoints
    path('api/games/<int:game_id>/feedback/', game_views.generate_ai_feedback, name='generate_ai_feedback'),
    path('api/feedback/comparative/', feedback_views.generate_comparative_feedback, name='generate_comparative_feedback'),
    path('api/feedback/improvement/', feedback_views.get_improvement_suggestions, name='get_improvement_suggestions'),
    
    # Dashboard endpoints
    path('api/dashboard/', dashboard_views.dashboard_view, name='dashboard'),
    path('api/dashboard/refresh/', dashboard_views.refresh_dashboard, name='refresh_dashboard'),
    path('api/dashboard/performance-trend/', dashboard_views.get_performance_trend, name='get_performance_trend'),
    path('api/dashboard/mistake-analysis/', dashboard_views.get_mistake_analysis, name='get_mistake_analysis'),
    
    # Utility endpoints
    path('api/csrf/', util_views.csrf, name='csrf'),
    path('api/health/', util_views.health_check, name='health_check'),
    path('api/info/', util_views.api_info, name='api_info'),
    path('api/constants/', util_views.get_system_constants, name='get_system_constants'),
    path('api/version/', util_views.check_version, name='check_version'),
    path('api/time/', util_views.get_server_time, name='get_server_time'),
    path('api/debug/', util_views.debug_request, name='debug_request'),
]
