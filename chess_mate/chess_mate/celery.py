"""
Celery configuration for ChessMate project.
"""

import os
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
import logging
from kombu import Exchange, Queue

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_mate.settings')

# Create the Celery app
app = Celery('chess_mate')

# Configure Celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Define exchanges
default_exchange = Exchange('default', type='direct')
analysis_exchange = Exchange('analysis', type='direct')

# Define queues with priorities
app.conf.task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('analysis', analysis_exchange, routing_key='analysis'),
    Queue('batch_analysis', analysis_exchange, routing_key='batch_analysis'),
)

# Configure task routing
app.conf.task_routes = {
    'core.tasks.analyze_game_task': {
        'queue': 'analysis',
        'routing_key': 'analysis'
    },
    'core.tasks.analyze_batch_games_task': {
        'queue': 'batch_analysis',
        'routing_key': 'batch_analysis'
    }
}

# Windows-specific settings with improved task management
app.conf.update(
    # Task execution settings
    worker_pool_restarts=True,
    worker_max_tasks_per_child=1,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_pool_limit=None,
    broker_heartbeat=0,
    
    # Task management
    worker_cancel_long_running_tasks_on_connection_loss=False,
    task_track_started=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone settings
    timezone='UTC',
    enable_utc=True,
    
    # Event monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Concurrency and prefetch settings
    worker_prefetch_multiplier=1,
    task_always_eager=False,
    task_ignore_result=False,
    
    # Result backend settings
    result_expires=3600,
    
    # Queue settings
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Priority settings
    task_queue_max_priority=10,
    task_default_priority=5,
    
    # Retry settings
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    },
    
    # Transport options
    broker_transport_options={
        'visibility_timeout': 3600,
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    },
    
    # Result backend transport options
    result_backend_transport_options={
        'global_keyprefix': 'chessmate:',
        'retry_policy': {
            'timeout': 5.0
        }
    }
)

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

@after_setup_task_logger.connect
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """Configure Celery logging after logger setup."""
    formatter = logging.Formatter(
        '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
    )
    
    # Configure file handler with absolute path
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'celery.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Configure console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # Set log level
    logger.setLevel(logging.INFO)
    
    # Log startup message
    logger.info("Celery logging configured")

@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')