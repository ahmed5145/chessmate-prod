import os
import logging
from django.conf import settings
from .windows_worker import WindowsWorkerPool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(settings.LOGS_DIR, 'worker.log'))
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Start the worker pool."""
    try:
        logger.info('Starting worker pool...')
        
        # Create and start the worker pool
        pool = WindowsWorkerPool(
            redis_url=settings.REDIS_URL,
            queues=['default'],
            num_workers=os.cpu_count() or 1
        )
        
        pool.start()
        
        # Keep the main process running
        try:
            while True:
                pass
        except KeyboardInterrupt:
            logger.info('Received keyboard interrupt')
        finally:
            pool.stop()
            
    except Exception as e:
        logger.error(f'Error in main process: {e}', exc_info=True)
        raise

if __name__ == '__main__':
    main() 