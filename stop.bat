@echo off
rem PyBI Windows Stop Script
echo === PyBI - Stopping Docker Containers ===

docker compose down

if %errorlevel% equ 0 (
    echo.
    echo PyBI containers stopped successfully.
) else (
    echo [ERROR] Failed to stop Docker containers.
)
