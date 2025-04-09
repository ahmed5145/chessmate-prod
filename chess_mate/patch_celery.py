#!/usr/bin/env python
"""
Script to patch Vine for Python 3.12 and then run the Django server
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

# Now start the Django server
try:
    print("Starting Django server...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_mate.settings')
    
    # Get the command line arguments
    port = "8000"
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    # Start the Django server
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "runserver", port])
except Exception as e:
    print(f"Failed to start Django server: {e}")
    sys.exit(1) 