@echo off
REM Set environment variables for testing
set DJANGO_SETTINGS_MODULE=chess_mate.test_settings
set TESTING=True

REM Navigate to the project directory
cd /d %~dp0

REM Run migrations first
echo Running migrations...
python manage.py migrate --settings=chess_mate.test_settings

REM Run tests with detailed output
echo Running tests...
if "%1"=="" (
    REM No arguments, run all tests
    python -m pytest -v
) else (
    REM Run specific tests
    python -m pytest -v %*
) 