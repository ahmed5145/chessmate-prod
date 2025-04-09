#!/bin/bash

# Exit on error
set -e

# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Clone or pull latest code
if [ -d "/var/www/chessmate" ]; then
    cd /var/www/chessmate
    git pull
else
    git clone https://github.com/yourusername/chessmate.git /var/www/chessmate
    cd /var/www/chessmate
fi

# Copy environment file if it doesn't exist
if [ ! -f "chess_mate/.env" ]; then
    cp chess_mate/.env.example chess_mate/.env
fi

# Build and start Docker containers
sudo docker-compose -f docker-compose.prod.yml down
sudo docker-compose -f docker-compose.prod.yml build
sudo docker-compose -f docker-compose.prod.yml up -d

# Configure Nginx
sudo cp nginx/chessmate.conf /etc/nginx/sites-available/chessmate
sudo ln -sf /etc/nginx/sites-available/chessmate /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL certificate
sudo certbot --nginx -d yourdomain.com --non-interactive --agree-tos --email your@email.com

echo "Deployment completed successfully!"
