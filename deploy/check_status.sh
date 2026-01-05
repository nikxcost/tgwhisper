#!/bin/bash
# Check bot status

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PID_FILE="$PROJECT_DIR/.bot.pid"
LOG_FILE="$PROJECT_DIR/logs/bot.log"

echo "=== TGWhisper Bot Status ==="
echo ""

if [ -f "$PID_FILE" ]; then
    BOT_PID=$(cat "$PID_FILE")

    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        echo "Status: ✓ RUNNING"
        echo "PID: $BOT_PID"

        # Check if 'ps' supports 'etime' (Linux) or use alternative for macOS
        if ps -p "$BOT_PID" -o etime= > /dev/null 2>&1; then
            UPTIME=$(ps -p "$BOT_PID" -o etime= | tr -d ' ')
            echo "Uptime: $UPTIME"
        fi

        # Memory usage
        if ps -p "$BOT_PID" -o rss= > /dev/null 2>&1; then
            MEMORY=$(ps -p "$BOT_PID" -o rss= | awk '{printf "%.2f MB\n", $1/1024}')
            echo "Memory: $MEMORY"
        fi
    else
        echo "Status: ✗ STOPPED (stale PID file)"
        echo "PID file exists but process is not running"
    fi
else
    echo "Status: ✗ STOPPED"
    echo "No PID file found"
fi

echo ""
echo "=== Last 10 Log Entries ==="
if [ -f "$LOG_FILE" ]; then
    tail -10 "$LOG_FILE"
else
    echo "No log file found at $LOG_FILE"
fi
