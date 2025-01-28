@echo off
echo Starting ChessMate services...

echo Starting Redis server...
net start Redis
if errorlevel 1 (
    echo Redis service not found, starting Redis server directly...
    start "Redis Server" /B "C:\Program Files\Redis\redis-server.exe" "%~dp0redis.windows.conf"
)

echo Waiting for Redis to start...
timeout /t 5 /nobreak > nul
redis-cli ping > nul 2>&1
if errorlevel 1 (
    echo Failed to connect to Redis.
    exit /b 1
)
echo Redis is running!

echo Starting RQ worker...
python run_worker.py

echo All services stopped.