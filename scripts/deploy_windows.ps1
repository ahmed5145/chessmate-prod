# PowerShell deployment script for Windows
param (
    [string]$KeyPath = "C:\Users\PCAdmin\Downloads\chessmate-key-pair.pem",
    [string]$EC2Host = "3.133.97.72",
    [string]$EC2User = "ubuntu"
)

# Configuration
$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/ahmed5145/chessmate-prod.git"
$Branch = "prod"

Write-Host "Starting deployment process..." -ForegroundColor Green

# Verify SSH key exists
if (-not (Test-Path $KeyPath)) {
    Write-Host "SSH key not found at: $KeyPath" -ForegroundColor Red
    exit 1
}

# Set correct permissions on the key file
try {
    # Remove inheritance
    $acl = Get-Acl $KeyPath
    $acl.SetAccessRuleProtection($true, $false)

    # Remove all existing permissions
    $acl.Access | ForEach-Object {
        $acl.RemoveAccessRule($_)
    }

    # Add new permission for current user
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $fileSystemRights = [System.Security.AccessControl.FileSystemRights]::Read
    $type = [System.Security.AccessControl.AccessControlType]::Allow

    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, $fileSystemRights, $type)
    $acl.AddAccessRule($rule)

    # Apply the new ACL
    Set-Acl -Path $KeyPath -AclObject $acl

    Write-Host "Successfully set permissions on key file" -ForegroundColor Green
}
catch {
    Write-Host "Failed to set key file permissions: $_" -ForegroundColor Red
    exit 1
}

# Configure git to handle line endings
Write-Host "Configuring git..." -ForegroundColor Yellow
git config --global core.autocrlf false
git config --global core.eol lf

# Create a temporary script for remote execution
$tempScript = @'
#!/bin/bash
set -e

# Update system and install dependencies
sudo apt-get update
sudo apt-get install -y docker.io docker-compose nginx

# Create deployment directory
sudo mkdir -p /var/www/chessmate
cd /var/www/chessmate

# Clone or update repository
if [ -d "chessmate_prod" ]; then
    cd chessmate_prod
    sudo git pull origin prod
else
    sudo git clone -b prod https://github.com/ahmed5145/chessmate-prod.git chessmate_prod
    cd chessmate_prod
fi

# Set up environment file if it doesn't exist
if [ ! -f ".env" ]; then
    sudo cp .env.example .env
    echo "Please update the .env file with production values"
fi

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Deploy with Docker Compose
sudo docker-compose -f docker-compose.prod.yml down
sudo docker-compose -f docker-compose.prod.yml build --no-cache
sudo docker-compose -f docker-compose.prod.yml up -d

# Configure Nginx
sudo cp nginx/chessmate.conf /etc/nginx/sites-available/chessmate
sudo ln -sf /etc/nginx/sites-available/chessmate /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# Show deployment status
echo "Container status:"
sudo docker-compose -f docker-compose.prod.yml ps
echo "Nginx status:"
sudo systemctl status nginx --no-pager
'@ -replace "`r`n", "`n"

# Save the script to a temporary file with Unix line endings
$tempScriptPath = Join-Path $env:TEMP "deploy_script.sh"
[System.IO.File]::WriteAllText($tempScriptPath, $tempScript)

# Use OpenSSH to copy and execute the script
Write-Host "Deploying to EC2..." -ForegroundColor Yellow
$sshCommand = "C:\Windows\System32\OpenSSH\ssh.exe"

# First, send the script content via SSH (with proper line endings)
$scriptContent = [System.IO.File]::ReadAllText($tempScriptPath)
& $sshCommand -i $KeyPath -o StrictHostKeyChecking=no $EC2User@$EC2Host "echo '$scriptContent' > deploy_script.sh"

# Then execute the script
& $sshCommand -i $KeyPath $EC2User@$EC2Host "chmod +x deploy_script.sh && ./deploy_script.sh"

# Clean up
Remove-Item $tempScriptPath

Write-Host "Deployment completed!" -ForegroundColor Green
