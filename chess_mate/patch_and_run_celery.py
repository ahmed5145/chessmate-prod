#!/usr/bin/env python
"""
Script to patch Vine for Python 3.12 and then run Celery worker
"""

import os
import sys
import subprocess

# First add the current directory to the path so we can import vine_patch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the vine patch
try:
    import vine_patch
    print("Applied Vine patch for Python 3.12")
except Exception as e:
    print(f"Failed to apply Vine patch: {e}")
    sys.exit(1)

# Now start the Celery worker
try:
    print("Starting Celery worker...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_mate.settings')
    
    # Import Celery app
    from chess_mate.celery import app
    
    # Start the worker
    argv = ["celery", "worker", "--app=chess_mate", "-l", "info"]
    app.worker_main(argv)
except Exception as e:
    print(f"Failed to start Celery worker: {e}")
    sys.exit(1) 