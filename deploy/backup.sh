#!/bin/bash
# Backup database, logs, and configuration files

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

# Create backup directory if doesn't exist
mkdir -p "$BACKUP_DIR"

cd "$PROJECT_DIR"

echo "Creating backup..."

# Create tar archive with database, logs, and .env
tar -czf "$BACKUP_FILE" \
    --exclude='venv' \
    --exclude='backups' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    bot_database.db \
    logs/ \
    .env 2>/dev/null || true

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "ERROR: Backup creation failed"
    exit 1
fi

# Keep only last 7 backups
cd "$BACKUP_DIR"
BACKUP_COUNT=$(ls -1 backup_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 7 ]; then
    echo "Cleaning up old backups (keeping last 7)..."
    ls -t backup_*.tar.gz | tail -n +8 | xargs rm -f
    echo "✓ Old backups cleaned up"
fi

echo "Done!"
