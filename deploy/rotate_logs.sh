#!/bin/bash
# Rotate log files when they exceed size limit

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

LOG_DIR="$PROJECT_DIR/logs"
MAX_SIZE=10485760  # 10MB in bytes

# Ensure log directory exists
mkdir -p "$LOG_DIR"

cd "$LOG_DIR"

# Process each log file
for log in *.log; do
    if [ -f "$log" ]; then
        # Get file size (compatible with both Linux and macOS)
        if [ "$(uname)" = "Darwin" ]; then
            # macOS
            size=$(stat -f%z "$log" 2>/dev/null || echo 0)
        else
            # Linux
            size=$(stat -c%s "$log" 2>/dev/null || echo 0)
        fi

        if [ "$size" -gt "$MAX_SIZE" ]; then
            timestamp=$(date +%Y%m%d_%H%M%S)
            echo "Rotating $log (size: $(($size / 1048576))MB)"

            # Move and compress
            mv "$log" "${log}.${timestamp}"
            gzip "${log}.${timestamp}"

            # Create new empty log file
            touch "$log"
        fi
    fi
done

# Clean old rotated logs (older than 30 days)
find "$LOG_DIR" -name "*.log.*.gz" -mtime +30 -delete 2>/dev/null

echo "Log rotation complete"
