#!/bin/bash
# Restart the bot

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping bot..."
"$SCRIPT_DIR/stop.sh"

sleep 2

echo "Starting bot..."
"$SCRIPT_DIR/supervisor.sh"

echo "Bot restarted. Check status with: ./deploy/check_status.sh"
