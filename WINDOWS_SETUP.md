# Windows Setup Guide for ChessMate

This guide will help you set up and run the ChessMate application on Windows.

## Prerequisites

- Python 3.8 or higher
- Git
- Redis (optional, but recommended for full functionality)

## Installation Steps

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd chessmate_prod
   ```

2. **Run the setup script**:
   Simply double-click the `run_development.bat` file or run it from the command prompt:
   ```
   run_development.bat
   ```

   This script will:
   - Install all required dependencies
   - Set up the development environment
   - Create necessary directories
   - Run database migrations
   - Start the development server

3. **Access the application**:
   Open your browser and go to http://127.0.0.1:8000/

## Redis on Windows

For full functionality, Redis is recommended. You can set it up on Windows in two ways:

### Option 1: Windows Subsystem for Linux (WSL)

1. Install WSL by running `wsl --install` in an administrator PowerShell
2. Install Redis in WSL: `sudo apt update && sudo apt install redis-server`
3. Start Redis in WSL: `sudo service redis-server start`

### Option 2: Redis Windows port

1. Download the Redis Windows port from https://github.com/microsoftarchive/redis/releases
2. Extract the files to a folder like `C:\Redis`
3. Start Redis by running `redis-server.exe` from that folder

Then, update your `.env` file to point to your Redis instance:
```
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Running Tests

To run tests on Windows:

```
cd chess_mate
python manage.py test
```

## Common Issues on Windows

1. **Path Length Limitations**: 
   Windows has a path length limit of 260 characters. If you encounter related errors, enable long paths:
   - Edit registry: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem` 
   - Set `LongPathsEnabled` to `1`

2. **Port Already in Use**:
   If port 8000 is already in use, specify a different port:
   ```
   python manage.py runserver 8080
   ```

3. **Redis Connection Issues**:
   If you encounter Redis connection errors, check that Redis is running and update your `.env` file with the correct host and port.

## Development Workflow

1. Make your changes
2. Run tests: `python manage.py test`
3. Run pre-commit checks: `pre-commit run --all-files`
4. Commit and push your changes

## Production Deployment on Windows

For production deployment on Windows, we recommend using:
- IIS with wfastcgi
- Windows Server
- SQL Server (adjust settings accordingly)

Alternatively, consider Docker deployment even on Windows, as it provides a consistent environment. 