"""
Celery tasks for game analysis.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from celery import shared_task, Task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import Game, Profile, GameAnalysis
from .game_analyzer import GameAnalyzer
from .cache_manager import CacheManager
from .ai_feedback import AIFeedbackGenerator
from django.db import transaction
from openai import OpenAI, OpenAIError
from datetime import datetime
import os
import redis
import json
import time
from .task_manager import TaskManager
from core.analysis.stockfish_analyzer import StockfishAnalyzer
from core.analysis.feedback_generator import FeedbackGenerator
from core.utils import analyze_game

logger = get_task_logger(__name__)
cache_manager = CacheManager()

class BaseAnalysisTask(Task):
    """Base class for analysis tasks."""
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f'Task {task_id} failed: {str(exc)}', exc_info=einfo)
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f'Task {task_id} completed successfully')
        super().on_success(retval, task_id, args, kwargs)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Cleanup after task completion."""
        logger.info(f'Task {task_id} finished with status: {status}')
        super().after_return(status, retval, task_id, args, kwargs, einfo)

@shared_task(bind=True, base=BaseAnalysisTask)
def analyze_game_task(self, game_id: int, depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
    """
    Analyze a single game.
    """
    try:
        game = Game.objects.get(id=game_id)
        game.analysis_status = 'analyzing'
        game.save()

        analyzer = GameAnalyzer()
        analysis_results = analyzer.analyze_single_game(game, depth)
        
        if not analysis_results or not analysis_results.get('analysis_results'):
            raise ValueError("Invalid analysis results")

        if use_ai and analysis_results.get('analysis_results', {}).get('moves'):
            try:
                feedback_generator = FeedbackGenerator()
                feedback = feedback_generator.generate_feedback(analysis_results)
                if feedback:
                    analysis_results['feedback'] = {
                        'source': 'openai',
                        'feedback': feedback
                    }
            except Exception as e:
                logger.error(f"Error generating AI feedback: {str(e)}")
                # Keep existing feedback if AI generation fails

        # Ensure consistent response structure
        if 'game_id' not in analysis_results:
            analysis_results['game_id'] = game_id
            
        if 'analysis_complete' not in analysis_results:
            analysis_results['analysis_complete'] = True

        # Update game with analysis results
        game.analysis = analysis_results
        game.analysis_status = 'analyzed'
        game.analysis_completed_at = timezone.now()
        game.save()

        return analysis_results

    except Game.DoesNotExist:
        logger.error(f"Game with id {game_id} not found")
        return {
            'analysis_complete': True,
            'game_id': game_id,
            'analysis_results': {
                'summary': GameAnalyzer()._get_default_metrics(),
                'moves': []
            },
            'feedback': {
                'source': 'system',
                'feedback': {
                    'strengths': [],
                    'weaknesses': [f'Game with id {game_id} not found'],
                    'critical_moments': [],
                    'improvement_areas': ['Ensure the game exists before analysis'],
                    'opening': {'analysis': 'Game not found', 'suggestion': 'Verify game ID'},
                    'middlegame': {'analysis': 'Game not found', 'suggestion': 'Verify game ID'},
                    'endgame': {'analysis': 'Game not found', 'suggestion': 'Verify game ID'}
                }
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing game {game_id}: {str(e)}", exc_info=True)
        game.analysis_status = 'failed'
        game.save()
        
        return {
            'analysis_complete': True,
            'game_id': game_id,
            'analysis_results': {
                'summary': GameAnalyzer()._get_default_metrics(),
                'moves': []
            },
            'feedback': {
                'source': 'system',
                'feedback': {
                    'strengths': [],
                    'weaknesses': [f'Analysis failed: {str(e)}'],
                    'critical_moments': [],
                    'improvement_areas': ['Try analyzing the game again'],
                    'opening': {'analysis': 'Analysis failed', 'suggestion': 'Try again'},
                    'middlegame': {'analysis': 'Analysis failed', 'suggestion': 'Try again'},
                    'endgame': {'analysis': 'Analysis failed', 'suggestion': 'Try again'}
                }
            }
        }

@shared_task(bind=True, base=BaseAnalysisTask)
def analyze_batch_games_task(self, game_ids: List[int], depth: int = 20, use_ai: bool = True, include_analyzed: bool = False) -> Dict[str, Any]:
    """
    Analyze a batch of games.
    """
    results = {}
    for game_id in game_ids:
        try:
            result = analyze_game_task(game_id, depth, use_ai)
            results[game_id] = result
        except Exception as e:
            logger.error(f"Error analyzing game {game_id} in batch: {str(e)}")
            results[game_id] = {"error": str(e)}
    return results

@shared_task(base=BaseAnalysisTask)
def cleanup_analysis_cache() -> None:
    """Clean up analysis cache."""
    try:
        CacheManager().clear_all_caches()
        logger.info("Successfully cleaned up analysis cache")
    except Exception as e:
        logger.error(f"Error cleaning up analysis cache: {str(e)}")

@shared_task(base=BaseAnalysisTask)
def cleanup_expired_cache_task() -> None:
    """Clean up expired cache entries."""
    try:
        TaskManager().cleanup_expired_tasks()
        logger.info("Successfully cleaned up expired tasks")
    except Exception as e:
        logger.error(f"Error cleaning up expired tasks: {str(e)}")

@shared_task(base=BaseAnalysisTask)
def update_user_stats_task(user_id: int) -> None:
    """Update user statistics."""
    try:
        profile = Profile.objects.get(user_id=user_id)
        profile.update_ratings_for_existing_games()
    except Profile.DoesNotExist:
        logger.error(f"Profile not found for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating user stats: {str(e)}")

@shared_task(base=BaseAnalysisTask)
def update_ratings_for_linked_account(profile_id: int) -> None:
    """Update ratings for linked chess platform account."""
    try:
        profile = Profile.objects.get(id=profile_id)
        profile.update_ratings_for_existing_games()
        logger.info(f"Successfully updated ratings for profile {profile_id}")
    except Profile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found")
    except Exception as e:
        logger.error(f"Error updating ratings: {str(e)}")

@shared_task(base=BaseAnalysisTask)
def health_check() -> Dict[str, Any]:
    """Health check task to verify Celery is working."""
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Celery is operational'
    } 