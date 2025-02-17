#!/bin/bash

# Create required directories
sudo mkdir -p /var/www/chessmate/data/certbot/conf
sudo mkdir -p /var/www/chessmate/data/certbot/www

# Ensure proper permissions
sudo chown -R 1000:1000 /var/www/chessmate/data/certbot
sudo chmod -R 755 /var/www/chessmate/data/certbot

# Copy certificates if they don't exist
if [ ! -d "/var/www/chessmate/data/certbot/conf/live" ]; then
    sudo cp -L -r /etc/letsencrypt/live /var/www/chessmate/data/certbot/conf/
    sudo cp -L -r /etc/letsencrypt/archive /var/www/chessmate/data/certbot/conf/
    sudo cp -r /etc/letsencrypt/renewal /var/www/chessmate/data/certbot/conf/
    sudo chown -R 1000:1000 /var/www/chessmate/data/certbot/conf
fi