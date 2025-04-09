#!/usr/bin/env python
"""
Environment Variable Loader for ChessMate

This script loads environment variables from .env files.
It prioritizes environment-specific files (.env.development, .env.production)
over the default .env file.

Usage:
    python load_env.py [environment]
    
    If environment is not specified, it defaults to 'development'.
"""

import os
import sys
from pathlib import Path

def load_env_file(file_path):
    """Load environment variables from a file"""
    if not os.path.exists(file_path):
        print(f"Warning: Environment file {file_path} not found.")
        return False
    
    print(f"Loading environment from: {file_path}")
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
                
            # Set the environment variable
            os.environ[key] = value
            
    return True

def main():
    """Main function to load environment variables"""
    # Get environment from command line or default to development
    environment = sys.argv[1] if len(sys.argv) > 1 else 'development'
    
    # Get project root directory
    project_root = Path(__file__).resolve().parent
    
    # Try environment-specific file first
    env_specific_file = os.path.join(project_root, f".env.{environment}")
    env_default_file = os.path.join(project_root, ".env")
    
    # Load environment-specific file if it exists
    if load_env_file(env_specific_file):
        print(f"Loaded {environment} environment settings.")
    # Fall back to default .env file
    elif load_env_file(env_default_file):
        print("Loaded default environment settings.")
    else:
        print("No environment files found. Using system environment variables.")
        
    # Print loaded environment variables (excluding sensitive ones)
    print("\nLoaded Environment Variables:")
    sensitive_keys = ['SECRET_KEY', 'PASSWORD', 'API_KEY']
    for key, value in sorted(os.environ.items()):
        # Skip non-project related environment variables
        if key.startswith('PYTHONPATH') or key.startswith('PATH') or key.startswith('APPDATA'):
            continue
            
        # Mask sensitive values
        is_sensitive = any(sensitive_key in key for sensitive_key in sensitive_keys)
        displayed_value = '********' if is_sensitive else value
        print(f"{key}={displayed_value}")

if __name__ == "__main__":
    main() 