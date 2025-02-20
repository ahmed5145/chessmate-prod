"""
Celery configuration for ChessMate project.
"""

import os
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger, worker_init
from celery.schedules import crontab
import logging
from kombu import Exchange, Queue
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_mate.settings')

# Create the Celery app
app = Celery('chess_mate')

# Configure Celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Define exchanges
task_exchange = Exchange('tasks', type='direct')

# Define queues
app.conf.task_queues = (
    Queue('default', task_exchange, routing_key='default'),
    Queue('analysis', task_exchange, routing_key='analysis'),
    Queue('batch_analysis', task_exchange, routing_key='batch_analysis'),
)

# Configure task routing
app.conf.task_routes = {
    'core.tasks.analyze_game_task': {'queue': 'analysis'},
    'core.tasks.analyze_batch_games_task': {'queue': 'batch_analysis'},
    'core.tasks.*': {'queue': 'default'},
}

# Configure celerybeat schedule
app.conf.beat_schedule = {
    'cleanup-expired-cache': {
        'task': 'core.tasks.cleanup_expired_cache_task',
        'schedule': crontab(minute='*/30'),  # Run every 30 minutes
    },
    'health-check': {
        'task': 'core.tasks.health_check',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
}

# Configure specific Celery settings
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,  # Disable prefetching
    task_acks_late=True,  # Only acknowledge after task completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker disconnects
    task_default_queue='default',
    task_default_exchange='tasks',
    task_default_routing_key='default',
    worker_state_db='celery_state',  # Enable worker state persistence
    worker_pool='prefork',  # Use prefork pool
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    task_always_eager=False,  # Ensure tasks are actually sent to workers
    task_eager_propagates=True,  # Propagate exceptions in eager mode
    task_remote_tracebacks=True,  # Include remote tracebacks in errors
    task_ignore_result=False,  # Store task results
)

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@worker_init.connect
def configure_worker(sender=None, conf=None, **kwargs):
    """Configure worker on initialization."""
    logger = logging.getLogger(__name__)
    logger.info("Initializing Celery worker")

@after_setup_task_logger.connect
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """Configure logging for Celery."""
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler
    file_handler = logging.FileHandler('logs/celery.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
    return {'status': 'ok'}