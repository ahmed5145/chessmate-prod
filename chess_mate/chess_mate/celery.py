"""
Celery configuration for ChessMate project.
"""

import logging
import os
import platform

from celery import Celery
from celery.schedules import crontab
from celery.signals import after_setup_logger, after_setup_task_logger, worker_init
from django.conf import settings
from kombu import Exchange, Queue

# Set the default Django settings module for the 'celery' program
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.settings")

# Create the Celery app
app = Celery("chess_mate")

# Configure Celery using Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Define exchanges
task_exchange = Exchange("tasks", type="direct")

# Define queues
app.conf.task_queues = (
    Queue("default", task_exchange, routing_key="default"),
    Queue("analysis", task_exchange, routing_key="analysis"),
    Queue("batch_analysis", task_exchange, routing_key="batch_analysis"),
)

# Configure task routing
app.conf.task_routes = {
    "core.tasks.analyze_game_task": {"queue": "analysis"},
    "core.tasks.analyze_batch_games_task": {"queue": "batch_analysis"},
    "core.tasks.*": {"queue": "default"},
}

# Configure celerybeat schedule
app.conf.beat_schedule = {
    "cleanup-expired-cache": {
        "task": "core.tasks.cleanup_expired_cache_task",
        "schedule": crontab(minute="*/30"),  # Run every 30 minutes
    },
    "health-check": {
        "task": "core.tasks.health_check",
        "schedule": crontab(minute="*/5"),  # Run every 5 minutes
    },
}

# Windows-specific settings
if platform.system() == "Windows":
    # Use solo pool on Windows
    app.conf.worker_pool = "solo"
    # Disable prefork pool settings
    app.conf.worker_prefetch_multiplier = 1
    app.conf.worker_max_tasks_per_child = 1  # Restart worker after each task
    # Disable process forking
    os.environ.setdefault("FORKED_BY_MULTIPROCESSING", "1")
    # Enable task events for monitoring
    app.conf.worker_send_task_events = True
    app.conf.worker_enable_remote_control = True
    app.conf.worker_disable_rate_limits = True
    # Optimize for Windows
    app.conf.broker_pool_limit = 1
    app.conf.broker_heartbeat = None
    app.conf.broker_connection_timeout = 30
    app.conf.broker_connection_retry = True
    app.conf.broker_connection_retry_on_startup = True
    app.conf.broker_connection_max_retries = 3
    app.conf.worker_pool_restarts = True
    app.conf.worker_max_memory_per_child = 200000  # 200MB
    # Task settings
    app.conf.task_acks_late = True
    app.conf.task_reject_on_worker_lost = True
    app.conf.task_time_limit = 3600  # 1 hour
    app.conf.task_soft_time_limit = 3300  # 55 minutes
    app.conf.task_track_started = True
    app.conf.task_ignore_result = False
    app.conf.task_store_errors_even_if_ignored = True
else:
    # Unix-specific settings
    app.conf.worker_pool = "prefork"
    app.conf.worker_prefetch_multiplier = 1
    app.conf.worker_max_tasks_per_child = 50

# Common settings for all platforms
app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    broker_connection_retry=True,
    broker_connection_max_retries=3,
    broker_pool_limit=10,
    broker_heartbeat=0,
    broker_connection_timeout=30,
    result_expires=3600,
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 5.0
        }
    },
    task_acks_late=True,  # Only acknowledge after task completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker disconnects
    task_default_queue="default",
    task_default_exchange="tasks",
    task_default_routing_key="default",
    worker_state_db="celery_state",  # Enable worker state persistence
    task_always_eager=False,  # Use actual Celery workers
    task_eager_propagates=True,  # Propagate exceptions in eager mode
    task_remote_tracebacks=True,  # Include remote tracebacks in errors
    task_ignore_result=False,  # Store task results
)

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()


@worker_init.connect
def configure_worker(sender=None, conf=None, **kwargs):
    """Configure worker on initialization."""
    logger = logging.getLogger(__name__)
    logger.info("Initializing Celery worker")
    if platform.system() == "Windows":
        logger.info("Running on Windows - using solo pool")


@after_setup_task_logger.connect
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """Configure logging for Celery."""
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler
    file_handler = logging.FileHandler("logs/celery.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
