"""
Celery configuration for ChessMate project.
"""

from __future__ import absolute_import, unicode_literals
import os
import platform
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_mate.settings')

# Create the Celery app
app = Celery('chess_mate')

# Configure Celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Windows-specific settings
if platform.system().lower() == 'windows':
    app.conf.update(
        broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=10,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_concurrency=1,  # Single worker for Windows
        worker_prefetch_multiplier=1,
        broker_transport_options={'visibility_timeout': 3600},
        result_backend_transport_options={'visibility_timeout': 3600},
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        enable_utc=True,
        task_always_eager=False,
        task_store_errors_even_if_ignored=True,
        task_ignore_result=False,
        task_time_limit=3600,
        broker_pool_limit=None,  # Disable connection pooling
        task_track_started=True,
        worker_max_tasks_per_child=50,  # Prevent memory leaks
        worker_max_memory_per_child=150000  # 150MB memory limit per worker
    )

# Load task modules from all registered Django app configs
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}') 