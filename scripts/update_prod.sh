#!/bin/bash

# Exit on error
set -e

echo "Starting production update process..."

# Stop system nginx if running
sudo systemctl stop nginx || true

# Navigate to project directory
cd /var/www/chessmate

# Backup current .env file
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "Backed up .env file"
fi

# Pull latest changes
echo "Pulling latest changes from git..."
sudo git pull

# Restore .env file
if [ -f ".env.backup" ]; then
    cp .env.backup .env
    echo "Restored .env file"
fi

# Rebuild and restart containers
echo "Rebuilding and restarting containers..."
sudo docker-compose -f docker-compose.prod.yml down
sudo docker-compose -f docker-compose.prod.yml build --no-cache
sudo docker-compose -f docker-compose.prod.yml up -d

# Check container status
echo "Checking container status..."
sudo docker-compose -f docker-compose.prod.yml ps

echo "Update completed!" 