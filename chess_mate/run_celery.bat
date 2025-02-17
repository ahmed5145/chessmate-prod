@echo off
:: Change to the script's directory
cd /d %~dp0

:: Start Celery using the main script
call start_celery.bat 