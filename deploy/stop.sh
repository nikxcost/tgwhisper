#!/bin/bash
# Stop the bot gracefully

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PID_FILE="$PROJECT_DIR/.bot.pid"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/supervisor.log"
}

if [ ! -f "$PID_FILE" ]; then
    log "No PID file found. Bot is not running."
    exit 0
fi

BOT_PID=$(cat "$PID_FILE")

if ps -p "$BOT_PID" > /dev/null 2>&1; then
    log "Stopping bot (PID: $BOT_PID)..."
    kill "$BOT_PID"

    # Wait for graceful shutdown
    sleep 3

    # Force kill if still running
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        log "Force killing bot..."
        kill -9 "$BOT_PID"
    fi

    log "Bot stopped"
else
    log "Process $BOT_PID not found. Cleaning up PID file."
fi

rm -f "$PID_FILE"
