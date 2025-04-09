import logging
import os
import platform
import signal
import sys

import django
from redis import Redis
from rq import Connection, Queue, Worker

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.settings")
django.setup()

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(processName)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(LOGS_DIR, "worker.log"))],
)

logger = logging.getLogger(__name__)


def setup_redis_connection():
    """Set up and test Redis connection."""
    try:
        from django.conf import settings

        redis_conn = Redis.from_url(settings.REDIS_URL)
        redis_conn.ping()  # Test connection
        logger.info(f"Successfully connected to Redis at {settings.REDIS_URL}")
        return redis_conn
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise


def handle_signal(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main worker function with enhanced error handling and logging."""
    try:
        logger.info("Starting worker initialization...")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python version: {sys.version}")

        # Set up signal handlers
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Set up Redis connection
        redis_conn = setup_redis_connection()

        # Configure worker for Windows
        with Connection(redis_conn):
            w = Worker(["default"])
            # Disable job monitoring to avoid fork issues on Windows
            w.job_monitoring_interval = 0
            # Set a smaller job timeout
            w.default_worker_ttl = 420
            # Enable logging
            w.log_job_description = True

            logger.info("Starting worker...")
            w.work()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Critical error in main process: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
