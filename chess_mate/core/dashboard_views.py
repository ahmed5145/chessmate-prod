"""
Dashboard-related views for the ChessMate application.
Including data aggregation for user statistics, recent games, and performance metrics.
"""

# Standard library imports
import logging
from datetime import timedelta
from typing import Dict, Any, List

# Django imports
from django.utils import timezone
from django.db.models import Count, Avg, Q

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Local application imports
from .models import Game, Profile, GameAnalysis
from .cache_manager import CacheManager

# Configure logging
logger = logging.getLogger(__name__)

# Initialize cache manager
cache_manager = CacheManager()

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    """
    Get dashboard data for the user, including recent games, statistics, and insights.
    """
    try:
        user = request.user
        
        # Check cache first
        cache_key = f"dashboard_data_{user.id}"
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
            
        # Get user's profile
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return Response(
                {"error": "User profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get recent games
        recent_games = Game.objects.filter(user=user).order_by('-date_played')[:5].values(
            'id',
            'white',
            'black',
            'result',
            'date_played',
            'platform',
            'opening_name',
            'analysis_status'
        )
        
        # Get analysis statistics
        analyzed_games = Game.objects.filter(user=user, analysis_status='analyzed')
        analysis_count = analyzed_games.count()
        
        # Calculate user's performance statistics
        performance_stats = {}
        
        # Overall win/loss/draw ratio
        all_games = Game.objects.filter(user=user)
        win_count = all_games.filter(result='win').count()
        loss_count = all_games.filter(result='loss').count()
        draw_count = all_games.filter(result='draw').count()
        total_games = all_games.count()
        
        if total_games > 0:
            win_rate = (win_count / total_games) * 100
            loss_rate = (loss_count / total_games) * 100
            draw_rate = (draw_count / total_games) * 100
        else:
            win_rate = loss_rate = draw_rate = 0
            
        performance_stats["overall"] = {
            "win_count": win_count,
            "loss_count": loss_count,
            "draw_count": draw_count,
            "total_games": total_games,
            "win_rate": round(win_rate, 2),
            "loss_rate": round(loss_rate, 2),
            "draw_rate": round(draw_rate, 2)
        }
        
        # Win/loss ratio as white
        white_games = all_games.filter(Q(white__icontains=profile.chess_com_username) | 
                                       Q(white__icontains=profile.lichess_username))
        white_win_count = white_games.filter(result='win').count()
        white_loss_count = white_games.filter(result='loss').count()
        white_draw_count = white_games.filter(result='draw').count()
        white_total = white_games.count()
        
        if white_total > 0:
            white_win_rate = (white_win_count / white_total) * 100
            white_loss_rate = (white_loss_count / white_total) * 100
            white_draw_rate = (white_draw_count / white_total) * 100
        else:
            white_win_rate = white_loss_rate = white_draw_rate = 0
            
        performance_stats["as_white"] = {
            "win_count": white_win_count,
            "loss_count": white_loss_count,
            "draw_count": white_draw_count,
            "total_games": white_total,
            "win_rate": round(white_win_rate, 2),
            "loss_rate": round(white_loss_rate, 2),
            "draw_rate": round(white_draw_rate, 2)
        }
        
        # Win/loss ratio as black
        black_games = all_games.filter(Q(black__icontains=profile.chess_com_username) | 
                                       Q(black__icontains=profile.lichess_username))
        black_win_count = black_games.filter(result='win').count()
        black_loss_count = black_games.filter(result='loss').count()
        black_draw_count = black_games.filter(result='draw').count()
        black_total = black_games.count()
        
        if black_total > 0:
            black_win_rate = (black_win_count / black_total) * 100
            black_loss_rate = (black_loss_count / black_total) * 100
            black_draw_rate = (black_draw_count / black_total) * 100
        else:
            black_win_rate = black_loss_rate = black_draw_rate = 0
            
        performance_stats["as_black"] = {
            "win_count": black_win_count,
            "loss_count": black_loss_count,
            "draw_count": black_draw_count,
            "total_games": black_total,
            "win_rate": round(black_win_rate, 2),
            "loss_rate": round(black_loss_rate, 2),
            "draw_rate": round(black_draw_rate, 2)
        }
        
        # Get most common openings
        opening_stats = all_games.values('opening_name').annotate(
            count=Count('opening_name')
        ).order_by('-count')[:5]
        
        # Calculate performance by opening
        opening_performance = []
        for opening in opening_stats:
            opening_name = opening['opening_name']
            opening_games = all_games.filter(opening_name=opening_name)
            opening_win_count = opening_games.filter(result='win').count()
            opening_total = opening_games.count()
            
            if opening_total > 0:
                win_percentage = (opening_win_count / opening_total) * 100
            else:
                win_percentage = 0
                
            opening_performance.append({
                "opening_name": opening_name,
                "games_count": opening_total,
                "win_count": opening_win_count,
                "win_percentage": round(win_percentage, 2)
            })
            
        # Get analysis insights
        analysis_insights = []
        
        if analysis_count > 0:
            # Get average accuracy
            try:
                avg_accuracy = analyzed_games.aggregate(Avg('analysis__analysis_results__summary__user_accuracy'))
                avg_accuracy_value = avg_accuracy.get('analysis__analysis_results__summary__user_accuracy__avg', 0)
                
                if avg_accuracy_value:
                    analysis_insights.append({
                        "type": "accuracy",
                        "title": "Average Game Accuracy",
                        "value": round(avg_accuracy_value, 2),
                        "unit": "%"
                    })
            except Exception as e:
                logger.warning(f"Could not calculate average accuracy: {str(e)}")
                
            # Get most common mistakes
            common_mistakes = {}
            try:
                for game in analyzed_games:
                    if not game.analysis or not game.analysis.get('analysis_results'):
                        continue
                        
                    mistakes = game.analysis.get('analysis_results', {}).get('mistakes', [])
                    for mistake in mistakes:
                        mistake_type = mistake.get('type', 'Unknown')
                        common_mistakes[mistake_type] = common_mistakes.get(mistake_type, 0) + 1
                        
                # Sort by frequency
                sorted_mistakes = sorted(common_mistakes.items(), key=lambda x: x[1], reverse=True)
                top_mistakes = sorted_mistakes[:3]
                
                if top_mistakes:
                    analysis_insights.append({
                        "type": "mistakes",
                        "title": "Most Common Mistakes",
                        "value": [{"type": m[0], "count": m[1]} for m in top_mistakes]
                    })
            except Exception as e:
                logger.warning(f"Could not calculate common mistakes: {str(e)}")
                
            # Get improvement over time
            try:
                recent_month = timezone.now() - timedelta(days=30)
                older_games = analyzed_games.filter(date_played__lt=recent_month)
                recent_games_analysis = analyzed_games.filter(date_played__gte=recent_month)
                
                if older_games.count() > 0 and recent_games_analysis.count() > 0:
                    older_avg = older_games.aggregate(Avg('analysis__analysis_results__summary__user_accuracy'))
                    recent_avg = recent_games_analysis.aggregate(Avg('analysis__analysis_results__summary__user_accuracy'))
                    
                    older_avg_value = older_avg.get('analysis__analysis_results__summary__user_accuracy__avg', 0)
                    recent_avg_value = recent_avg.get('analysis__analysis_results__summary__user_accuracy__avg', 0)
                    
                    if older_avg_value and recent_avg_value:
                        improvement = recent_avg_value - older_avg_value
                        
                        analysis_insights.append({
                            "type": "improvement",
                            "title": "Accuracy Improvement",
                            "value": round(improvement, 2),
                            "unit": "%"
                        })
            except Exception as e:
                logger.warning(f"Could not calculate improvement: {str(e)}")
                
        # Build final response data
        dashboard_data = {
            "user": {
                "username": user.username,
                "chess_com_username": profile.chess_com_username,
                "lichess_username": profile.lichess_username,
                "elo_rating": profile.elo_rating,
                "credits": profile.credits,
                "analysis_count": profile.analysis_count
            },
            "recent_games": list(recent_games),
            "game_stats": {
                "total_games": total_games,
                "analyzed_games": analysis_count,
                "analysis_pending": all_games.filter(analysis_status='analyzing').count()
            },
            "performance": performance_stats,
            "openings": opening_performance,
            "insights": analysis_insights
        }
        
        # Cache the results
        cache_manager.set(cache_key, dashboard_data, 900)  # Cache for 15 minutes
        
        return Response(dashboard_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating dashboard data: {str(e)}")
        return Response(
            {"error": "Failed to generate dashboard data"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_dashboard(request):
    """
    Force refresh the dashboard data by clearing the cache.
    """
    try:
        user = request.user
        cache_key = f"dashboard_data_{user.id}"
        
        # Clear cache
        cache_manager.delete(cache_key)
        
        return Response(
            {"message": "Dashboard cache cleared successfully"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error refreshing dashboard: {str(e)}")
        return Response(
            {"error": "Failed to refresh dashboard"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_performance_trend(request):
    """
    Get the user's performance trend over time.
    """
    try:
        user = request.user
        
        # Check cache first
        cache_key = f"performance_trend_{user.id}"
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
            
        # Get analyzed games with results
        analyzed_games = Game.objects.filter(
            user=user, 
            analysis_status='analyzed'
        ).order_by('date_played')
        
        # Skip if no analyzed games
        if not analyzed_games:
            return Response(
                {"message": "No analyzed games found"},
                status=status.HTTP_200_OK
            )
            
        # Collect trend data
        trend_data = []
        
        for game in analyzed_games:
            if not game.analysis or not game.analysis.get('analysis_results'):
                continue
                
            try:
                analysis_results = game.analysis.get('analysis_results', {})
                accuracy = analysis_results.get('summary', {}).get('user_accuracy', 0)
                mistakes = len(analysis_results.get('mistakes', []))
                blunders = len(analysis_results.get('blunders', []))
                
                trend_point = {
                    "game_id": game.id,
                    "date": game.date_played.isoformat(),
                    "accuracy": round(accuracy, 2) if accuracy else 0,
                    "result": game.result,
                    "mistakes": mistakes,
                    "blunders": blunders,
                    "opening": game.opening_name,
                    "opponent": game.opponent
                }
                
                trend_data.append(trend_point)
            except Exception as e:
                logger.warning(f"Error processing game {game.id} for trend: {str(e)}")
                continue
                
        # Calculate moving averages
        if trend_data:
            window_size = min(5, len(trend_data))
            for i in range(len(trend_data)):
                # Calculate moving average for accuracy
                if i >= window_size - 1:
                    window = trend_data[i - window_size + 1:i + 1]
                    accuracies = [point['accuracy'] for point in window]
                    avg_accuracy = sum(accuracies) / len(accuracies)
                    trend_data[i]['avg_accuracy'] = round(avg_accuracy, 2)
                else:
                    window = trend_data[:i + 1]
                    accuracies = [point['accuracy'] for point in window]
                    avg_accuracy = sum(accuracies) / len(accuracies)
                    trend_data[i]['avg_accuracy'] = round(avg_accuracy, 2)
                    
        # Cache the results
        cache_manager.set(cache_key, trend_data, 1800)  # Cache for 30 minutes
        
        return Response(trend_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating performance trend: {str(e)}")
        return Response(
            {"error": "Failed to generate performance trend"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_mistake_analysis(request):
    """
    Get analysis of common mistakes made by the user.
    """
    try:
        user = request.user
        
        # Check cache first
        cache_key = f"mistake_analysis_{user.id}"
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
            
        # Get analyzed games
        analyzed_games = Game.objects.filter(
            user=user, 
            analysis_status='analyzed'
        )
        
        # Skip if no analyzed games
        if not analyzed_games:
            return Response(
                {"message": "No analyzed games found"},
                status=status.HTTP_200_OK
            )
            
        # Collect mistake data
        mistake_types = {}
        game_phase_mistakes = {"opening": 0, "middlegame": 0, "endgame": 0}
        mistake_by_piece = {"pawn": 0, "knight": 0, "bishop": 0, "rook": 0, "queen": 0, "king": 0}
        total_mistakes = 0
        
        for game in analyzed_games:
            if not game.analysis or not game.analysis.get('analysis_results'):
                continue
                
            try:
                analysis_results = game.analysis.get('analysis_results', {})
                mistakes = analysis_results.get('mistakes', [])
                
                for mistake in mistakes:
                    total_mistakes += 1
                    
                    # Count by type
                    mistake_type = mistake.get('type', 'unknown')
                    mistake_types[mistake_type] = mistake_types.get(mistake_type, 0) + 1
                    
                    # Count by game phase
                    move_number = mistake.get('move_number', 0)
                    if move_number <= 10:
                        game_phase_mistakes["opening"] += 1
                    elif move_number <= 30:
                        game_phase_mistakes["middlegame"] += 1
                    else:
                        game_phase_mistakes["endgame"] += 1
                        
                    # Count by piece
                    piece = mistake.get('piece', 'unknown')
                    if piece.lower() in mistake_by_piece:
                        mistake_by_piece[piece.lower()] += 1
            except Exception as e:
                logger.warning(f"Error processing game {game.id} for mistakes: {str(e)}")
                continue
                
        # Prepare response
        if total_mistakes > 0:
            # Convert to percentages
            for phase in game_phase_mistakes:
                game_phase_mistakes[phase] = round((game_phase_mistakes[phase] / total_mistakes) * 100, 2)
                
            for piece in mistake_by_piece:
                mistake_by_piece[piece] = round((mistake_by_piece[piece] / total_mistakes) * 100, 2)
                
            # Sort mistake types by frequency
            sorted_types = sorted(mistake_types.items(), key=lambda x: x[1], reverse=True)
            top_mistake_types = [{"type": m[0], "count": m[1], "percentage": round((m[1] / total_mistakes) * 100, 2)} 
                               for m in sorted_types[:10]]
                               
            response_data = {
                "total_mistakes": total_mistakes,
                "by_type": top_mistake_types,
                "by_game_phase": game_phase_mistakes,
                "by_piece": mistake_by_piece,
                "games_analyzed": analyzed_games.count()
            }
        else:
            response_data = {
                "message": "No mistakes found in analyzed games",
                "games_analyzed": analyzed_games.count()
            }
            
        # Cache the results
        cache_manager.set(cache_key, response_data, 1800)  # Cache for 30 minutes
        
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating mistake analysis: {str(e)}")
        return Response(
            {"error": "Failed to generate mistake analysis"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 