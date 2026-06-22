#!/bin/bash
# Disk maintenance — daily auto-cleanup to keep /home/john <80%
# Runs via disk-maintenance.timer (daily 0300 MT)

set -e
THRESHOLD_PCT=80
HOME_DISK_USE=$(df /home/john | awk 'NR==2 {print $5}' | sed 's/%//')

# Log
LOG="/home/john/Thunderbird/logs/disk_maintenance.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Disk maintenance start. Usage: ${HOME_DISK_USE}%" >> "$LOG"

# Purge if over threshold
if [ "$HOME_DISK_USE" -gt "$THRESHOLD_PCT" ]; then
  # Aggressive: nuke caches
  rm -rf ~/.cache/* 2>/dev/null || true
  rm -rf ~/.npm 2>/dev/null || true
  rm -rf ~/.bun 2>/dev/null || true

  # Prune old logs (>14 days)
  find /home/john/Thunderbird/logs -type f -mtime +14 -delete 2>/dev/null || true

  # Prune old JSONL (>30 days)
  find /home/john/Thunderbird/OpsCenter -name "*.jsonl" -mtime +30 -delete 2>/dev/null || true

  NEW_USE=$(df /home/john | awk 'NR==2 {print $5}' | sed 's/%//')
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Cleanup executed. New usage: ${NEW_USE}%" >> "$LOG"
else
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Below threshold (${HOME_DISK_USE}%). No action." >> "$LOG"
fi
