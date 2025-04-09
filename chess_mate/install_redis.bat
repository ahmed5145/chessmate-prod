@echo off
echo Installing Redis for Windows...

:: Check if Redis is already installed
redis-cli --version > nul 2>&1
if %errorlevel% equ 0 (
    echo Redis is already installed.
    goto :verify_redis
)

:: Download Redis using curl (built into Windows 10+)
echo Downloading Redis...
curl -L -o redis.msi https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi

:: Install Redis silently
echo Installing Redis...
start /wait msiexec /i redis.msi /quiet

:: Wait a bit
setlocal enabledelayedexpansion
set /a count=0
:wait_loop
set /a count+=1
if !count! lss 5 (
    rem This loop will run for approximately 5 seconds
    goto wait_loop
)


:: Clean up
del redis.msi

:verify_redis
:: Start Redis service
echo Starting Redis service...
net start Redis
if errorlevel 1 (
    echo Starting Redis server directly...
    start "Redis Server" /B "C:\Program Files\Redis\redis-server.exe" redis.windows.conf
    set /a count=0
    :wait_loop2
    set /a count+=1
    if !count! lss 3 (
        rem This loop will run for approximately 3 seconds
        goto wait_loop2
    )
    )

:: Test Redis
echo Testing Redis connection...
"C:\Program Files\Redis\redis-cli.exe" ping
if errorlevel 1 (
    echo Failed to connect to Redis.
    echo Please ensure Redis is installed correctly.
    echo You can download it from: https://github.com/microsoftarchive/redis/releases
    exit /b 1
)

echo Redis is installed and running!
echo Installation complete.
pause
