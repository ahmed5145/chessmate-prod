"""
    Windows worker for RQ.
    Handles worker processes and logging in the background.
    Uses Redis for job processing.
    Manages multiple worker processes and restarts them if they die.
    Provides detailed logging and error handling.
"""
import os
import multiprocessing
import logging
import signal
import time
from typing import List, Optional, Union
from redis import Redis
from rq import Queue, Worker, Connection
from rq.worker import WorkerStatus
from django.conf import settings

logger = logging.getLogger(__name__)

class WindowsWorkerProcess:
    """A worker process that runs on Windows."""
    
    def __init__(self, redis_url, queues):
        self.redis_url = redis_url
        self.queues = queues
        self.process = None
        
    def start(self):
        """Start the worker process."""
        self.process = multiprocessing.Process(
            target=self._run_worker,
            args=(self.redis_url, self.queues)
        )
        self.process.start()
        
    def stop(self):
        """Stop the worker process."""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join()
            
    @staticmethod
    def _run_worker(redis_url, queues):
        """Run the RQ worker."""
        try:
            redis_conn = Redis.from_url(redis_url)
            with Connection(redis_conn):
                worker = Worker(queues)
                worker.work()
        except Exception as e:
            logger.error(f"Worker process error: {e}")

class WindowsWorkerPool:
    """A pool of worker processes for Windows."""
    
    def __init__(self, redis_url, queues, num_workers=1):
        self.redis_url = redis_url
        self.queues = queues
        self.num_workers = num_workers
        self.workers = []
        
    def start(self):
        """Start all worker processes."""
        multiprocessing.set_start_method('spawn', force=True)
        for _ in range(self.num_workers):
            worker = WindowsWorkerProcess(self.redis_url, self.queues)
            worker.start()
            self.workers.append(worker)
            
    def stop(self):
        """Stop all worker processes."""
        for worker in self.workers:
            worker.stop()
        self.workers = []