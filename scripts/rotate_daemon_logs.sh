#!/bin/bash
# Thunderbird daemon log rotation — SO-DISK-PRESSURE-20260620
# Runs daily via systemd timer to prevent unbounded log growth

LOGS=(
  "/home/john/Thunderbird/.rclone_sync.log"
  "/home/john/Thunderbird/OpsCenter/logs/email_scanner.log"
  "/home/john/Thunderbird/OpsCenter/logs/commander_updates.log"
  "/home/john/Thunderbird/logs/phase3a_health_check.log"
  "/home/john/Thunderbird/logs/telegram_gw_stderr.log"
  "/home/john/Thunderbird/logs/openrouter_monitor.log"
  "/home/john/Thunderbird/logs/trip_architect.log"
  "/home/john/Thunderbird/OpsCenter/logs/email_task_ingest.log"
  "/home/john/Thunderbird/logs/qdrant_reindex.log"
  "/home/john/Thunderbird/logs/inbox_checkpoint_daemon.log"
)

ARCHIVE_DIR="/home/john/Thunderbird/logs/archive"
mkdir -p "$ARCHIVE_DIR"

for logfile in "${LOGS[@]}"; do
  if [ -f "$logfile" ]; then
    size=$(stat -f%z "$logfile" 2>/dev/null || stat -c%s "$logfile" 2>/dev/null)

    # Rotate if >100MB
    if [ "$size" -gt 104857600 ]; then
      timestamp=$(date +%Y%m%d_%H%M%S)
      archive_name="$(basename "$logfile").$timestamp"

      gzip -c "$logfile" > "$ARCHIVE_DIR/$archive_name.gz"
      > "$logfile"  # Truncate in place

      echo "[$(date)] Rotated $(basename $logfile) — archived to $archive_name.gz"
    fi
  fi
done

# Clean up archives older than 14 days
find "$ARCHIVE_DIR" -name "*.gz" -mtime +14 -delete

exit 0
