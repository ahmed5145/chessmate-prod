"""
Celery tasks for game analysis.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from celery import shared_task
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import Game, Profile, GameAnalysis
from .game_analyzer import GameAnalyzer
from .cache_manager import CacheManager
from .ai_feedback import AIFeedbackGenerator
from django.db import transaction
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)
cache_manager = CacheManager()

@shared_task(bind=True)
def analyze_game_task(self, game_id: int, depth: int = 20, use_ai: bool = True) -> Dict:
    """
    Analyze a chess game asynchronously.
    """
    try:
        # Get the game
        game = Game.objects.get(id=game_id)
        
        # Initialize the analyzer with Stockfish path
        analyzer = GameAnalyzer(stockfish_path=settings.STOCKFISH_PATH)
        
        try:
            # Analyze the game first
            analysis_results = analyzer.analyze_single_game(game, depth)
            
            # Generate feedback based on analysis
            feedback = analyzer.generate_feedback(analysis_results, game)
            source = 'openai_analysis' if use_ai and feedback.get('source') == 'openai_analysis' else 'statistical_analysis'
            
            # Create or update GameAnalysis
            analysis_data = {
                'feedback': feedback,
                'source': source,
                'timestamp': timezone.now().isoformat(),
                'depth': depth,
                'analysis_results': analysis_results
            }
            
            GameAnalysis.objects.update_or_create(
                game=game,
                defaults={'analysis_data': analysis_data}
            )
            
            return {
                'status': 'completed',
                'game_id': game_id
            }
            
        except OpenAIError as e:
            logger.warning(f"OpenAI API error: {str(e)}. Falling back to statistical analysis.")
            
            # Analyze the game
            analysis_results = analyzer.analyze_single_game(game, depth)
            
            # Generate feedback without AI
            feedback = analyzer.generate_feedback(analysis_results, game)
            
            # Create or update GameAnalysis with fallback data
            analysis_data = {
                'feedback': feedback,
                'source': 'statistical_analysis',
                'timestamp': timezone.now().isoformat(),
                'depth': depth,
                'analysis_results': analysis_results,
                'fallback_reason': str(e)
            }
            
            GameAnalysis.objects.update_or_create(
                game=game,
                defaults={'analysis_data': analysis_data}
            )
            
            return {
                'status': 'completed',
                'game_id': game_id
            }
            
        finally:
            # Always close the engine
            analyzer.close_engine()
            
    except Game.DoesNotExist:
        error_msg = f"Game {game_id} not found"
        logger.error(error_msg)
        return {
            'status': 'failed',
            'error': error_msg
        }
        
    except Exception as e:
        error_msg = f"Error analyzing game {game_id}: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'failed',
            'error': error_msg
        }

@shared_task(bind=True, max_retries=3)
def analyze_batch_games_task(self, game_ids: List[int], depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
    """
    Analyze multiple games asynchronously.
    
    Args:
        game_ids: List of game IDs to analyze
        depth: Analysis depth for Stockfish
        use_ai: Whether to use OpenAI for feedback generation
    
    Returns:
        Dict containing analysis results and status for each game
    """
    result = {
        "status": "failed",
        "task_id": self.request.id,
        "results": {},
        "completed": 0,
        "total": len(game_ids),
        "error": None
    }
    
    try:
        # Initialize analyzer
        analyzer = GameAnalyzer(stockfish_path=settings.STOCKFISH_PATH)
        
        try:
            for game_id in game_ids:
                try:
                    game = Game.objects.get(id=game_id)
                    
                    # Analyze the game
                    analysis_results = analyzer.analyze_single_game(game, depth)
                    
                    # Generate feedback if requested
                    if use_ai and analysis_results:
                        try:
                            # Initialize AI feedback generator with API key
                            feedback_generator = AIFeedbackGenerator(settings.OPENAI_API_KEY)
                            
                            # Get player profile for personalized feedback
                            player = game.user
                            player_profile = {
                                "username": player.username,
                                "rating": getattr(player.profile, "rating", None),
                                "total_games": getattr(player.profile, "total_games", 0),
                                "preferences": {
                                    "preferred_openings": getattr(player.profile, "preferred_openings", [])
                                }
                            }
                            
                            # Generate AI feedback
                            feedback = feedback_generator.generate_personalized_feedback(
                                game_analysis=analysis_results,
                                player_profile=player_profile
                            )
                            
                            if feedback:
                                analysis_results["feedback"] = feedback
                                
                        except Exception as e:
                            logger.error(f"Error generating AI feedback for game {game_id}: {str(e)}")
                            # Fallback to basic feedback
                            feedback = analyzer.generate_feedback(analysis_results, game)
                            if feedback:
                                analysis_results["feedback"] = feedback
                    
                    # Save results to database
                    analyzer.save_analysis_to_db(game, analysis_results)
                    
                    result["results"][game_id] = {
                        "status": "completed",
                        "results": analysis_results
                    }
                    
                    result["completed"] += 1
                    
                    # Update progress in cache
                    progress = (result["completed"] / result["total"]) * 100
                    cache.set(
                        f"batch_analysis_progress_{self.request.id}",
                        {
                            "status": "in_progress",
                            "progress": progress,
                            "completed": result["completed"],
                            "total": result["total"],
                            "current_results": result["results"]
                        },
                        timeout=3600
                    )
                    
                except Game.DoesNotExist:
                    logger.error(f"Game {game_id} not found")
                    result["results"][game_id] = {
                        "status": "failed",
                        "error": "Game not found"
                    }
                    
                except Exception as e:
                    logger.error(f"Error analyzing game {game_id}: {str(e)}")
                    result["results"][game_id] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    
        finally:
            # Ensure engine is closed
            analyzer.close_engine()
        
        # Update final status
        result["status"] = "completed"
        
        # Set final results in cache
        cache.set(
            f"batch_analysis_results_{self.request.id}",
            result,
            timeout=3600
        )
        
    except Exception as e:
        error_msg = f"Error in batch analysis: {str(e)}"
        logger.error(error_msg)
        result["error"] = error_msg
        self.retry(exc=e, countdown=2 ** self.request.retries)
    
    return result

@shared_task
def cleanup_analysis_cache() -> None:
    """Periodic task to clean up expired analysis cache entries."""
    try:
        pattern = "analysis_status_*"
        keys = [key for key in cache.iter_keys(pattern)]
        for key in keys:
            if not cache.get(key):
                cache.delete(key)
    except Exception as e:
        logger.error(f"Error cleaning up analysis cache: {str(e)}")

@shared_task
def cleanup_expired_cache_task() -> None:
    """Periodic task to clean up expired cache entries."""
    try:
        cache_manager.clear_all_caches()
    except Exception as e:
        logger.error(f"Error in cleanup_expired_cache_task: {str(e)}")

@shared_task
def update_user_stats_task(user_id: int) -> None:
    """Update user statistics based on analyzed games."""
    try:
        with transaction.atomic():
            profile = Profile.objects.get(user_id=user_id)
            games = Game.objects.filter(player_id=user_id)
            
            total_games = games.count()
            if total_games == 0:
                return
            
            # Calculate statistics
            wins = games.filter(result='win').count()
            losses = games.filter(result='loss').count()
            draws = games.filter(result='draw').count()
            
            # Update profile
            profile.total_games = total_games
            profile.win_rate = (wins / total_games) * 100
            profile.recent_performance = 'improving' if profile.win_rate > 50 else 'stable'
            profile.save()
            
    except Exception as e:
        logger.error(f"Error in update_user_stats_task: {str(e)}") 