#!/bin/bash
# Optimize database and clean old records

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Starting database optimization..."

# Activate virtual environment
source venv/bin/activate

# Run optimization
python3 << 'EOF'
from database.database import Session, engine
from sqlalchemy import text
from datetime import datetime

session = Session()

try:
    print("Running VACUUM...")
    session.execute(text("VACUUM;"))

    print("Running ANALYZE...")
    session.execute(text("ANALYZE;"))

    # Clean old usage logs (older than 90 days)
    print("Cleaning old usage logs (>90 days)...")
    result = session.execute(text("""
        DELETE FROM usage_logs
        WHERE created_at < datetime('now', '-90 days')
    """))

    deleted = result.rowcount
    if deleted > 0:
        print(f"Deleted {deleted} old log entries")
    else:
        print("No old entries to delete")

    session.commit()
    print("✓ Database optimized successfully")

except Exception as e:
    print(f"ERROR: {e}")
    session.rollback()
finally:
    session.close()
EOF

# Show database size
if [ -f "bot_database.db" ]; then
    DB_SIZE=$(du -h bot_database.db | cut -f1)
    echo "Current database size: $DB_SIZE"
fi

echo "Done!"
