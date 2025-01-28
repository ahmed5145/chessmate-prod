from typing import Dict, Any, Optional
import redis
from rq import Queue, get_current_job
from rq.job import Job
from django.conf import settings
import logging
import json
import traceback
from datetime import datetime
from .game_analyzer import GameAnalyzer
from .models import Game, GameAnalysis

logger = logging.getLogger(__name__)

def log_job_event(job_id: str, event: str, details: Dict[str, Any] = None):
    """Log job events with consistent formatting."""
    log_data = {
        'job_id': job_id,
        'event': event,
        'timestamp': datetime.now().isoformat(),
        'details': details or {}
    }
    logger.info(f"Job event: {json.dumps(log_data)}")

def analyze_game_job(game_id: int, depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
    """Background job function for game analysis."""
    job = get_current_job()
    job_id = job.id if job else 'unknown'
    
    log_job_event(job_id, 'started', {
        'game_id': game_id,
        'depth': depth,
        'use_ai': use_ai
    })
    
    try:
        # Get the game
        game = Game.objects.get(id=game_id)
        log_job_event(job_id, 'game_loaded', {'game_id': game_id})
        
        # Initialize analyzer
        analyzer = GameAnalyzer(stockfish_path=settings.STOCKFISH_PATH)
        log_job_event(job_id, 'analyzer_initialized')
        
        try:
            # Analyze the game
            analysis_results = analyzer.analyze_single_game(game, depth)
            log_job_event(job_id, 'analysis_completed', {
                'moves_analyzed': len(analysis_results.get('moves', []))
            })
            
            # Generate feedback
            feedback = analyzer.generate_feedback(analysis_results, game)
            source = 'openai_analysis' if use_ai and feedback.get('source') == 'openai_analysis' else 'statistical_analysis'
            log_job_event(job_id, 'feedback_generated', {'source': source})
            
            # Save analysis results
            analysis_data = {
                'feedback': feedback,
                'source': source,
                'timestamp': str(game.date_played),
                'depth': depth,
                'analysis_results': analysis_results,
                'job_id': job_id
            }
            
            GameAnalysis.objects.update_or_create(
                game=game,
                defaults={'analysis_data': analysis_data}
            )
            log_job_event(job_id, 'results_saved')
            
            return {
                'status': 'completed',
                'game_id': game_id,
                'result': analysis_data
            }
            
        finally:
            analyzer.close_engine()
            log_job_event(job_id, 'analyzer_closed')
            
    except Exception as e:
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        log_job_event(job_id, 'error', error_details)
        logger.error(f"Error in analysis job: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
            'traceback': traceback.format_exc()
        }

class RQTaskManager:
    def __init__(self):
        try:
            redis_conn = redis.from_url(settings.REDIS_URL)
            self.queue = Queue(connection=redis_conn)
            logger.info(f"RQTaskManager initialized with queue: {self.queue.name}")
        except Exception as e:
            logger.error(f"Failed to initialize RQTaskManager: {str(e)}", exc_info=True)
            raise
        
    def create_analysis_job(self, game_id: int, depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
        """Create a background job for game analysis."""
        try:
            # Check if game exists before creating job
            game = Game.objects.get(id=game_id)
            
            # Enqueue the job
            job = self.queue.enqueue(
                analyze_game_job,
                args=(game_id, depth, use_ai),
                job_timeout='10m',  # 10 minutes timeout
                result_ttl=3600,    # Keep result for 1 hour
                failure_ttl=3600,   # Keep failed job info for 1 hour
                meta={
                    'game_id': game_id,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Created analysis job {job.id} for game {game_id}")
            return {
                'status': 'created',
                'task_id': job.id
            }
        except Game.DoesNotExist:
            error_msg = f"Game {game_id} not found"
            logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg
            }
        except Exception as e:
            logger.error(f"Error creating analysis job: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a background job."""
        try:
            job = self.queue.fetch_job(job_id)
            
            if not job:
                logger.warning(f"Job {job_id} not found")
                return {
                    'status': 'error',
                    'message': 'Job not found'
                }
                
            if job.is_finished:
                result = job.result
                if result and result.get('status') == 'completed':
                    logger.info(f"Job {job_id} completed successfully")
                    return {
                        'status': 'completed',
                        'result': result.get('result')
                    }
                else:
                    error_msg = result.get('error') if result else 'Unknown error'
                    logger.error(f"Job {job_id} failed: {error_msg}")
                    return {
                        'status': 'failed',
                        'error': error_msg,
                        'traceback': result.get('traceback') if result else None
                    }
            elif job.is_failed:
                error_msg = str(job.exc_info) if job.exc_info else 'Job failed'
                logger.error(f"Job {job_id} failed: {error_msg}")
                return {
                    'status': 'failed',
                    'message': error_msg
                }
            else:
                logger.info(f"Job {job_id} is still running")
                return {
                    'status': 'in_progress',
                    'message': 'Job is still running',
                    'meta': job.meta
                }
                
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
            
    def cleanup_job(self, job_id: str) -> None:
        """Clean up a completed job."""
        try:
            job = self.queue.fetch_job(job_id)
            if job:
                job.delete()
                logger.info(f"Cleaned up job {job_id}")
        except Exception as e:
            logger.error(f"Error cleaning up job {job_id}: {str(e)}", exc_info=True) 