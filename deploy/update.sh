#!/bin/bash
# Update bot from git repository safely

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/update.log"
}

log "=== Starting update process ==="

# Create backup first
log "Creating backup..."
"$SCRIPT_DIR/backup.sh"

# Stop bot
log "Stopping bot..."
"$SCRIPT_DIR/stop.sh"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    log "WARNING: Uncommitted changes detected, stashing..."
    git stash
fi

# Pull latest code
log "Pulling latest code from git..."
if git pull origin main; then
    log "✓ Code updated successfully"
else
    log "ERROR: Git pull failed"
    log "Starting bot with old code..."
    "$SCRIPT_DIR/supervisor.sh"
    exit 1
fi

# Update dependencies
log "Updating dependencies..."
source "$PROJECT_DIR/venv/bin/activate"
if pip install -r requirements.txt --upgrade --quiet; then
    log "✓ Dependencies updated"
else
    log "WARNING: Dependency update had issues"
fi

# Run database initialization (creates tables if needed)
log "Checking database..."
python3 -c "from database.database import init_db; init_db()" 2>&1 | tee -a "$LOG_DIR/update.log"

# Start bot
log "Starting bot..."
"$SCRIPT_DIR/supervisor.sh"

sleep 2

# Check if bot started successfully
if [ -f "$PROJECT_DIR/.bot.pid" ]; then
    BOT_PID=$(cat "$PROJECT_DIR/.bot.pid")
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        log "✓ Bot started successfully (PID: $BOT_PID)"
        log "=== Update complete ==="
    else
        log "ERROR: Bot failed to start"
        exit 1
    fi
else
    log "WARNING: No PID file found, bot may not have started"
fi
