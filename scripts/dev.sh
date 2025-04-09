#!/bin/bash

# Exit on error
set -e

echo "Starting local development environment..."

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from example. Please update with your settings."
fi

# Build and start containers for development
echo "Starting development containers..."
docker-compose up --build

# The script will wait here while containers are running
# Press Ctrl+C to stop

echo "Development environment stopped."
