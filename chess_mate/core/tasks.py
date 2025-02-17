"""
Celery tasks for game analysis.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from celery import shared_task
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

@shared_task(bind=True)
def analyze_game_task(self, game_id: int, depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
    """
    Analyze a single game.
    """
    logger.info(f"Starting analysis for game {game_id}")
    analyzer = GameAnalyzer()
    
    try:
        game = Game.objects.get(id=game_id)
        
        # Update game status to analyzing
        with transaction.atomic():
            game.refresh_from_db()
            game.status = 'analyzing'
            game.save(update_fields=['status'])
        
        # Perform analysis
        logger.info(f"Starting analysis for game {game_id}")
        analysis_results = analyzer.analyze_single_game(game, depth)
        
        if not analysis_results:
            logger.error(f"Analysis produced no results for game {game_id}")
            game.status = 'failed'
            game.save(update_fields=['status'])
            return {
                'status': 'failed',
                'game_id': game_id,
                'message': 'Analysis produced no results'
            }
        
        # Structure results for feedback generation
        structured_results = {
            'analysis_results': analysis_results,
            'game_info': {
                'white': game.white,
                'black': game.black,
                'result': game.result,
                'date_played': game.date_played.isoformat() if game.date_played else None
            }
        }
        
        # Generate feedback
        logger.info(f"Generating feedback for game {game_id}")
        feedback = analyzer.generate_feedback(structured_results, game)
        
        # Prepare analysis data
        analysis_data = {
            'analysis_results': analysis_results,
            'feedback': feedback,
            'depth': depth,
            'timestamp': datetime.now().isoformat(),
            'source': 'openai_analysis' if use_ai else 'statistical_analysis',
            'analysis_complete': True
        }
        
        # Save results
        game.status = 'analyzed'
        game.analysis = analysis_data
        game.analysis_completed_at = timezone.now()
        game.save(update_fields=['status', 'analysis', 'analysis_completed_at'])
        
        logger.info(f"Analysis completed for game {game_id}")
        return {
            'status': 'completed',
            'game_id': game_id,
            'message': 'Analysis completed successfully'
        }
        
    except Game.DoesNotExist:
        logger.error(f"Game {game_id} not found")
        return {
            'status': 'failed',
            'game_id': game_id,
            'message': 'Game not found'
        }
    except Exception as e:
        logger.error(f"Error analyzing game {game_id}: {str(e)}")
        return {
            'status': 'failed',
            'game_id': game_id,
            'message': str(e)
        }

@shared_task(bind=True)
def analyze_batch_games_task(self, game_ids: List[int], depth: int = 20, use_ai: bool = True, include_analyzed: bool = False) -> Dict[str, Any]:
    """
    Analyze multiple games in batch.
    """
    logger.info(f"Starting batch analysis of {len(game_ids)} games")
    analyzer = GameAnalyzer()
    successful_games = []
    failed_games = []
    
    try:
        for game_id in game_ids:
            try:
                game = Game.objects.get(id=game_id)
                
                # Skip already analyzed games unless explicitly included
                if game.status == 'analyzed' and not include_analyzed:
                    logger.info(f"Skipping already analyzed game {game_id}")
                    continue
                
                # Update game status to analyzing
                with transaction.atomic():
                    game.refresh_from_db()
                    game.status = 'analyzing'
                    game.save(update_fields=['status'])
                
                # Perform analysis
                logger.info(f"Starting analysis for game {game_id}")
                analysis_results = analyzer.analyze_single_game(game, depth)
                
                if not analysis_results:
                    logger.error(f"Analysis produced no results for game {game_id}")
                    failed_games.append(game_id)
                    with transaction.atomic():
                        game.refresh_from_db()
                        game.status = 'failed'
                        game.save(update_fields=['status'])
                    continue
                
                # Generate feedback
                logger.info(f"Generating feedback for game {game_id}")
                feedback = analyzer.generate_feedback(analysis_results, game)
                
                # Prepare analysis data
                analysis_data = {
                    'analysis_results': analysis_results,
                    'feedback': feedback,
                    'depth': depth,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'openai_analysis' if use_ai else 'statistical_analysis',
                    'analysis_complete': True
                }
                
                # Save results
                with transaction.atomic():
                    game.refresh_from_db()
                    game.status = 'analyzed'
                    game.analysis = analysis_data
                    game.analysis_completed_at = timezone.now()
                    game.save(update_fields=['status', 'analysis', 'analysis_completed_at'])
                
                successful_games.append(game_id)
                logger.info(f"Successfully analyzed game {game_id}")
                
            except Game.DoesNotExist:
                logger.error(f"Game {game_id} not found")
                failed_games.append(game_id)
            except Exception as e:
                logger.error(f"Error analyzing game {game_id}: {str(e)}")
                failed_games.append(game_id)
                with transaction.atomic():
                    try:
                        game = Game.objects.get(id=game_id)
                        game.status = 'failed'
                        game.save(update_fields=['status'])
                    except Game.DoesNotExist:
                        pass
        
        if successful_games:
            return {
                'status': 'completed',
                'successful_games': successful_games,
                'failed_games': failed_games
            }
        else:
            error_message = "No games were successfully analyzed"
            if failed_games:
                error_message = f"All {len(failed_games)} games failed analysis"
            logger.error(error_message)
            return {
                'status': 'failed',
                'message': error_message,
                'failed_games': failed_games
            }
            
    except Exception as e:
        logger.error(f"Batch analysis failed: {str(e)}")
        return {
            'status': 'failed',
            'message': str(e),
            'failed_games': game_ids
        }

@shared_task
def cleanup_analysis_cache() -> None:
    """Clean up old analysis cache entries."""
    try:
        cache.delete_pattern("analysis:*")
        logger.info("Successfully cleaned up analysis cache")
    except Exception as e:
        logger.error(f"Error cleaning up analysis cache: {str(e)}")

@shared_task
def cleanup_expired_cache_task() -> None:
    """Clean up expired cache entries."""
    try:
        TaskManager().cleanup_expired_tasks()
        logger.info("Successfully cleaned up expired tasks")
    except Exception as e:
        logger.error(f"Error cleaning up expired tasks: {str(e)}")

@shared_task
def update_user_stats_task(user_id: int) -> None:
    """Update user statistics."""
    try:
        profile = Profile.objects.get(user_id=user_id)
        profile.update_ratings_for_existing_games()
    except Profile.DoesNotExist:
        logger.error(f"Profile not found for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating user stats: {str(e)}")

@shared_task
def update_ratings_for_linked_account(profile_id: int) -> None:
    """Update ratings for a linked chess platform account."""
    try:
        profile = Profile.objects.get(id=profile_id)
        profile.update_ratings_for_existing_games()
        logger.info(f"Successfully updated ratings for profile {profile_id}")
    except Profile.DoesNotExist:
        logger.error(f"Profile {profile_id} not found")
    except Exception as e:
        logger.error(f"Error updating ratings for profile {profile_id}: {str(e)}") 