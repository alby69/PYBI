#!/usr/bin/env bash
# Make sure to make this script executable before running:
# chmod +x start.sh stop.sh

set -e

# ANSI Color Codes
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== PyBI - Stopping Docker Containers ===${NC}"

docker compose down

echo -e "${GREEN}PyBI containers stopped successfully.${NC}"
