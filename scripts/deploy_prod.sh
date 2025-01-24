#!/bin/bash

# Configuration
EC2_HOST="3.133.97.72"
EC2_USER="ubuntu"
DEPLOY_DIR="/var/www/chessmate"
REPO="https://github.com/ahmed5145/chessmate-prod.git"
BRANCH="prod"

echo "Starting deployment to EC2..."

# SSH into EC2 and run deployment
ssh -i "C:\Users\PCAdmin\Downloads\chessmate-key-pair.pem" $EC2_USER@$EC2_HOST << 'EOF'
    # Update system
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose

    # Create or clean deployment directory
    sudo mkdir -p $DEPLOY_DIR
    cd $DEPLOY_DIR

    # Pull latest changes
    if [ -d ".git" ]; then
        sudo git pull origin prod
    else
        sudo git clone -b prod https://github.com/ahmed5145/chessmate-prod.git .
    fi

    # Ensure .env exists
    if [ ! -f ".env" ]; then
        sudo cp .env.example .env
        echo "Please update .env file with production values"
        exit 1
    fi

    # Build and start containers
    sudo docker-compose -f docker-compose.prod.yml down
    sudo docker-compose -f docker-compose.prod.yml build --no-cache
    sudo docker-compose -f docker-compose.prod.yml up -d

    # Show status
    sudo docker-compose -f docker-compose.prod.yml ps
EOF

echo "Deployment completed!" 