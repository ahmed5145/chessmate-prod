#!/bin/bash

# Configuration
EC2_HOST="3.133.97.72"
EC2_USER="ubuntu"
SSH_KEY="$HOME/.ssh/chessmate-key-pair.pem"
REPO_URL="https://github.com/ahmed5145/chessmate-prod.git"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting deployment to EC2...${NC}"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

# Ensure SSH key has correct permissions
chmod 400 "$SSH_KEY"

# Push changes to GitHub
echo "Pushing changes to GitHub..."
git add .
git commit -m "Deployment commit - $(date)" || true
git push origin prod || {
    echo -e "${RED}Failed to push to GitHub${NC}"
    exit 1
}

# SSH into EC2 and update application
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'EOF'
    # Create directory if it doesn't exist
    sudo mkdir -p /var/www/chessmate
    cd /var/www/chessmate

    # Clone or pull repository
    if [ -d "chessmate_prod" ]; then
        cd chessmate_prod
        sudo git pull origin prod
    else
        sudo git clone -b prod https://github.com/ahmed5145/chessmate-prod.git chessmate_prod
        cd chessmate_prod
    fi

    # Copy environment file if it doesn't exist
    if [ ! -f ".env" ]; then
        sudo cp .env.example .env
        echo "Please update the .env file with your production values"
    fi

    # Install Docker if not installed
    if ! command -v docker &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose
    fi

    # Start Docker service if not running
    if ! systemctl is-active --quiet docker; then
        sudo systemctl start docker
    fi

    # Build and start Docker containers
    sudo docker-compose -f docker-compose.prod.yml down
    sudo docker-compose -f docker-compose.prod.yml build --no-cache
    sudo docker-compose -f docker-compose.prod.yml up -d

    # Install and configure Nginx
    if ! command -v nginx &> /dev/null; then
        sudo apt-get install -y nginx
    fi

    # Configure Nginx
    sudo cp nginx/chessmate.conf /etc/nginx/sites-available/chessmate
    sudo ln -sf /etc/nginx/sites-available/chessmate /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl restart nginx

    # Show status
    echo "Container status:"
    sudo docker-compose -f docker-compose.prod.yml ps
    echo "Nginx status:"
    sudo systemctl status nginx --no-pager
EOF

echo -e "${GREEN}Deployment completed!${NC}"
