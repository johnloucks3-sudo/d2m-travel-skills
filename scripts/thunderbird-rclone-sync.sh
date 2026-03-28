#!/bin/bash
# thunderbird-rclone-sync.sh — Mirror ~/Thunderbird/ to d2mconcierge Google Drive
# Replaces thunderbird_sync.py — unified rclone auth with d2m-drive-sync
# Remote: d2mconcierge: (authenticate once with: rclone config reconnect d2mconcierge:)

RCLONE="/home/john/.local/bin/rclone"
LOG="/home/john/Thunderbird/.rclone_sync.log"
SRC="/home/john/Thunderbird/"
DST="d2mconcierge:Thunderbird_Mirror/"
FILTER_FILE="/home/john/Thunderbird/scripts/thunderbird_sync_filters.txt"

echo "$(date '+%Y-%m-%d %H:%M:%S') — Thunderbird rclone sync starting  SRC=$SRC  DST=$DST" >> "$LOG"

$RCLONE copy "$SRC" "$DST" \
  --filter-from "$FILTER_FILE" \
  --transfers 4 \
  --checkers 8 \
  --log-file "$LOG" \
  --log-level INFO \
  2>&1

EXIT_CODE=$?
echo "$(date '+%Y-%m-%d %H:%M:%S') — Thunderbird rclone sync finished (exit: $EXIT_CODE)" >> "$LOG"

exit $EXIT_CODE
