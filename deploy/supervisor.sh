#!/bin/bash
# Bot supervisor script for Beget shared hosting
# Checks if bot is running and starts it if needed
# Should be run by cron every 3 minutes: */3 * * * * /path/to/supervisor.sh

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
VENV_DIR="$PROJECT_DIR/venv"
PID_FILE="$PROJECT_DIR/.bot.pid"
LOG_DIR="$PROJECT_DIR/logs"
SUPERVISOR_LOG="$LOG_DIR/supervisor.log"
BOT_LOG="$LOG_DIR/bot.log"
LOCK_FILE="$PROJECT_DIR/.supervisor.lock"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$SUPERVISOR_LOG"
}

# Check for lock file to prevent multiple supervisors
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE")
    if ps -p "$LOCK_PID" > /dev/null 2>&1; then
        # Another supervisor is running
        exit 0
    else
        # Stale lock file, remove it
        rm -f "$LOCK_FILE"
    fi
fi

# Create lock file
echo $$ > "$LOCK_FILE"

# Check if bot is running
if [ -f "$PID_FILE" ]; then
    BOT_PID=$(cat "$PID_FILE")

    # Check if process exists and is our bot
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        # Check if it's actually Python process
        if ps -p "$BOT_PID" -o comm= | grep -q python; then
            # Bot is running normally
            rm -f "$LOCK_FILE"
            exit 0
        fi
    fi

    # PID file exists but process is dead
    log "Stale PID file detected, removing..."
    rm -f "$PID_FILE"
fi

# Bot is not running, start it
log "Bot is not running, starting..."

cd "$PROJECT_DIR"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    log "ERROR: Virtual environment not found at $VENV_DIR"
    rm -f "$LOCK_FILE"
    exit 1
fi

# Activate virtual environment and start bot
source "$VENV_DIR/bin/activate"

# Start bot in background and redirect output
nohup python3 main.py >> "$BOT_LOG" 2>&1 &
BOT_PID=$!

# Save PID
echo "$BOT_PID" > "$PID_FILE"

log "Bot started with PID: $BOT_PID"

# Remove lock file
rm -f "$LOCK_FILE"
