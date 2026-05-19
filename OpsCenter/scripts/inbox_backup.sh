#!/bin/bash
# Inbox Backup Script for Thunderbird Wing Task Coordination
# Hourly cron: 0 * * * * /home/john/Thunderbird/OpsCenter/scripts/inbox_backup.sh

set -e

BACKUP_DIR="/home/john/Thunderbird/OpsCenter/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M)
LOG_FILE="/home/john/Thunderbird/logs/backup_$(date +%Y%m%d).log"

# Create log directory if needed
mkdir -p "$(dirname "$LOG_FILE")"

echo "=== Inbox Backup $(date) ===" >> "$LOG_FILE"

# Backup opencode inbox
if [ -f "/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md" ]; then
    cp "/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md" \
       "$BACKUP_DIR/opencode_inbox_$TIMESTAMP.md.bak"
    COUNT=$(grep -c "^status: UNREAD" "/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md" 2>/dev/null || echo "0")
    echo "  opencode_inbox backed up: $COUNT UNREAD tasks" >> "$LOG_FILE"
else
    echo "  WARNING: opencode_inbox.md not found" >> "$LOG_FILE"
fi

# Backup claude inbox  
if [ -f "/home/john/Thunderbird/claude_inbox.md" ]; then
    cp "/home/john/Thunderbird/claude_inbox.md" \
       "$BACKUP_DIR/claude_inbox_$TIMESTAMP.md.bak"
    COUNT=$(grep -c "^status: UNREAD" "/home/john/Thunderbird/claude_inbox.md" 2>/dev/null || echo "0")
    echo "  claude_inbox backed up: $COUNT UNREAD tasks" >> "$LOG_FILE"
else
    echo "  WARNING: claude_inbox.md not found" >> "$LOG_FILE"
fi

# Cleanup old backups (keep last 48 hours)
find "$BACKUP_DIR" -name "*.md.bak" -mtime +2 -delete 2>/dev/null || true
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.md.bak" | wc -l)
echo "  Cleanup complete: $BACKUP_COUNT backups retained" >> "$LOG_FILE"

# Update nexus state
if [ -f "/home/john/Thunderbird/OpsCenter/nexus_inbox_state.json" ]; then
    echo "{\"last_backup\": \"$TIMESTAMP\", \"backup_count\": $BACKUP_COUNT}" > "/home/john/Thunderbird/OpsCenter/backup_state.json"
fi

echo "=== Backup completed ===" >> "$LOG_FILE"