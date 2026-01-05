#!/bin/bash
# Monitor bot resources and log status

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MONITOR_LOG="$PROJECT_DIR/logs/monitor.log"
PID_FILE="$PROJECT_DIR/.bot.pid"

mkdir -p "$PROJECT_DIR/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$MONITOR_LOG"
}

# Check disk space
if [ "$(uname)" = "Darwin" ]; then
    # macOS
    DISK_USAGE=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
else
    # Linux
    DISK_USAGE=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
fi

if [ "$DISK_USAGE" -gt 80 ]; then
    log "WARNING: Disk usage high: ${DISK_USAGE}%"
fi

# Check database size
if [ -f "$PROJECT_DIR/bot_database.db" ]; then
    DB_SIZE=$(du -h "$PROJECT_DIR/bot_database.db" | cut -f1)
    log "Database size: $DB_SIZE"
fi

# Check log directory size
if [ -d "$PROJECT_DIR/logs" ]; then
    LOG_SIZE=$(du -sh "$PROJECT_DIR/logs" | cut -f1)
    log "Logs directory size: $LOG_SIZE"
fi

# Check if bot is running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        # Get memory usage
        if ps -p "$PID" -o rss= > /dev/null 2>&1; then
            MEM=$(ps -p "$PID" -o rss= | awk '{printf "%.2f MB", $1/1024}')
            log "Bot running (PID: $PID, Memory: $MEM, Disk: ${DISK_USAGE}%)"
        else
            log "Bot running (PID: $PID, Disk: ${DISK_USAGE}%)"
        fi
    else
        log "WARNING: Bot not running (stale PID file)"
    fi
else
    log "WARNING: Bot not running (no PID file)"
fi
