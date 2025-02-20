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
    """Analyze a single game."""
    logger.info(f"Starting analysis for game {game_id}")
    analyzer = None
    try:
        # Log the game retrieval attempt
        logger.info(f"Attempting to retrieve game {game_id}")
        game = Game.objects.get(id=game_id)
        logger.info(f"Successfully retrieved game {game_id}")
        
        # Update game status to analyzing
        with transaction.atomic():
            game.status = 'analyzing'
            game.save(update_fields=['status'])
        
        analyzer = GameAnalyzer()
        try:
            logger.info(f"Starting game analysis for game {game_id}")
            analysis_data = analyzer.analyze_single_game(game, depth=depth)
            logger.info(f"Analysis completed for game {game_id}. Data present: {bool(analysis_data)}")
            
            # Check if analysis was successful and complete
            if (analysis_data and 
                analysis_data.get('analysis_complete', False) and 
                isinstance(analysis_data.get('analysis_results', {}).get('moves', []), list)):
                
                logger.info(f"Analysis successful for game {game_id}. Saving results.")
                with transaction.atomic():
                    game.refresh_from_db()
                    game.status = 'analyzed'
                    game.analysis = analysis_data
                    game.analysis_completed_at = timezone.now()
                    game.save(update_fields=['status', 'analysis', 'analysis_completed_at'])
                logger.info(f"Successfully saved analysis results for game {game_id}")
                
                return {
                    'status': 'completed',
                    'game_id': game_id,
                    'message': 'Analysis completed successfully'
                }
            
            # Handle analysis failure
            error_msg = analysis_data.get('error', 'Analysis incomplete or invalid') if analysis_data else 'No analysis data returned'
            logger.error(f"Analysis failed for game {game_id}: {error_msg}")
            with transaction.atomic():
                game.refresh_from_db()
                game.status = 'failed'
                game.save(update_fields=['status'])
            return {
                'status': 'failed',
                'game_id': game_id,
                'message': f'Analysis failed: {error_msg}'
            }
            
        except Exception as e:
            logger.error(f"Error during game analysis: {str(e)}", exc_info=True)
            with transaction.atomic():
                game.refresh_from_db()
                game.status = 'failed'
                game.save(update_fields=['status'])
            return {
                'status': 'failed',
                'game_id': game_id,
                'message': f'Analysis error: {str(e)}'
            }
            
    except Game.DoesNotExist:
        logger.error(f"Game {game_id} not found")
        return {
            'status': 'failed',
            'game_id': game_id,
            'message': 'Game not found'
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'game_id': game_id,
            'message': f'Unexpected error: {str(e)}'
        }
    finally:
        if analyzer:
            try:
                analyzer.close_engine()
            except Exception as e:
                logger.error(f"Error during engine cleanup: {str(e)}")

@shared_task(bind=True, base=BaseAnalysisTask)
def analyze_batch_games_task(self, game_ids: List[int], depth: int = 20, use_ai: bool = True, include_analyzed: bool = False) -> Dict[str, Any]:
    """Analyze multiple games in batch."""
    logger.info(f"Starting batch analysis of {len(game_ids)} games")
    
    successful_games = []
    failed_games = []
    analyzer = None
    
    try:
        analyzer = GameAnalyzer()
        total_games = len(game_ids)
        
        for index, game_id in enumerate(game_ids, 1):
            try:
                game = Game.objects.get(id=game_id)
                
                # Skip already analyzed games if not explicitly included
                if not include_analyzed and game.status == 'analyzed':
                    logger.info(f"Skipping already analyzed game {game_id}")
                    continue
                
                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': index,
                        'total': total_games,
                        'game_id': game_id,
                        'status': 'processing'
                    }
                )
                
                logger.info(f"Processing game {game_id} ({index}/{total_games})")
                
                # Update game status
                with transaction.atomic():
                    game.status = 'analyzing'
                    game.save(update_fields=['status'])
                
                # Analyze game
                analysis_data = analyzer.analyze_single_game(game, depth=depth)
                
                if (analysis_data and 
                    analysis_data.get('analysis_complete', False) and 
                    analysis_data.get('analysis_results', {}).get('moves', [])):
                    
                    # Save results
                    with transaction.atomic():
                        game.refresh_from_db()
                        game.status = 'analyzed'
                        game.analysis = analysis_data
                        game.analysis_completed_at = timezone.now()
                        game.save(update_fields=['status', 'analysis', 'analysis_completed_at'])
                    
                    successful_games.append(game_id)
                    logger.info(f"Successfully analyzed game {game_id}")
                    
                else:
                    error_msg = analysis_data.get('error', 'Analysis incomplete or invalid') if analysis_data else 'No analysis data returned'
                    logger.error(f"Analysis failed for game {game_id}: {error_msg}")
                    with transaction.atomic():
                        game.status = 'failed'
                        game.save(update_fields=['status'])
                    failed_games.append(game_id)
                
            except Game.DoesNotExist:
                logger.error(f"Game {game_id} not found")
                failed_games.append(game_id)
            except Exception as e:
                logger.error(f"Error processing game {game_id}: {str(e)}", exc_info=True)
                failed_games.append(game_id)
                try:
                    with transaction.atomic():
                        game = Game.objects.get(id=game_id)
                        game.status = 'failed'
                        game.save(update_fields=['status'])
                except Exception:
                    pass
    
    except Exception as e:
        logger.error(f"Batch analysis failed: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'successful_games': successful_games,
            'failed_games': failed_games,
            'error': str(e)
        }
    
    finally:
        if analyzer:
            try:
                analyzer.close_engine()
            except Exception as e:
                logger.error(f"Error during engine cleanup: {str(e)}")
    
    return {
        'status': 'completed',
        'successful_games': successful_games,
        'failed_games': failed_games,
        'total_processed': len(successful_games) + len(failed_games)
    }

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