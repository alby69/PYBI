@echo off
rem PyBI Windows Start Script
echo === PyBI - Starting Docker Container ===

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo Please install Docker Desktop for Windows and try again.
    pause
    exit /b 1
)

docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker daemon is not running.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

if not exist .env (
    if exist .env.example (
        echo Copying .env.example to .env...
        copy .env.example .env >nul
    )
)

echo Building and starting containers in detached mode...
docker compose up -d --build

if %errorlevel% equ 0 (
    echo.
    echo ===========================================
    echo  PyBI is starting up successfully!
    echo  Access the application at: http://localhost:8080
    echo ===========================================
) else (
    echo [ERROR] Failed to start Docker containers.
)
