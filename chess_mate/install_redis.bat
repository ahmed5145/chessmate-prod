@echo off
setlocal

echo Installing Redis for Windows...

set "REDIS_CLI=redis-cli"
set "REDIS_SERVER=redis-server"

REM If Redis is not available on PATH, try installing it.
%REDIS_CLI% --version >nul 2>&1
if errorlevel 1 (
    echo Redis was not found on PATH. Downloading installer...
    curl -L -o redis.msi https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi
    if errorlevel 1 (
        echo Failed to download Redis installer.
        exit /b 1
    )

    echo Installing Redis...
    start /wait msiexec /i redis.msi /quiet
    if exist redis.msi del redis.msi

    REM Prefer installed executables when available.
    if exist "C:\Program Files\Redis\redis-cli.exe" set "REDIS_CLI=C:\Program Files\Redis\redis-cli.exe"
    if exist "C:\Program Files\Redis\redis-server.exe" set "REDIS_SERVER=C:\Program Files\Redis\redis-server.exe"
) else (
    echo Redis is already installed.
)

REM Try to start Windows service first.
echo Starting Redis service (if installed as service)...
net start Redis >nul 2>&1
if errorlevel 1 (
    echo Redis service not available/running. Starting redis-server process...
    where redis-server >nul 2>&1
    if errorlevel 1 (
        if exist "C:\Program Files\Redis\redis-server.exe" set "REDIS_SERVER=C:\Program Files\Redis\redis-server.exe"
    )

    if not exist "%REDIS_SERVER%" (
        where %REDIS_SERVER% >nul 2>&1
        if errorlevel 1 (
            echo Could not locate redis-server. Install Redis manually and retry.
            exit /b 1
        )
    )

    start "Redis Server" cmd /k "cd /d %~dp0 && %REDIS_SERVER% redis.windows.conf"
)

REM Validate connectivity.
echo Testing Redis connection...
where redis-cli >nul 2>&1
if %errorlevel%==0 (
    redis-cli ping
) else if exist "C:\Program Files\Redis\redis-cli.exe" (
    "C:\Program Files\Redis\redis-cli.exe" ping
) else (
    echo redis-cli not found; skip ping test.
)

echo Redis setup complete.
pause
