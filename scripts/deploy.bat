@echo off
echo Starting deployment process...

:: Run PowerShell script with elevated privileges
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& {Start-Process PowerShell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0deploy_windows.ps1\"' -Verb RunAs}"

echo Deployment process initiated.
pause
