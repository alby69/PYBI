#!/usr/bin/env bash
# Make sure to make this script executable before running:
# chmod +x start.sh stop.sh

set -e

# ANSI Color Codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== PyBI - Starting Docker Container ===${NC}"

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not available in PATH.${NC}"
    echo "Please install Docker and try again."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running.${NC}"
    echo "Please start the Docker service and try again."
    exit 1
fi

# Ensure .env exists if .env.example exists
if [ ! -f .env ] && [ -f .env.example ]; then
    echo -e "${BLUE}No .env file found. Copying .env.example to .env...${NC}"
    cp .env.example .env
fi

echo -e "${BLUE}Building and starting containers in detached mode...${NC}"
docker compose up -d --build

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN} PyBI is starting up successfully!${NC}"
echo -e "${GREEN} Access the application at: http://localhost:8080${NC}"
echo -e "${GREEN}===========================================${NC}"
