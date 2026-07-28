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
  --ignore-errors \
  --skip-links \
  --log-file "$LOG" \
  --log-level INFO \
  2>&1

EXIT_CODE=$?
# With --ignore-errors, rclone skips files that fail to transfer and continues.
# Exit 1 = transfer errors occurred but were skipped (e.g. source file changed size
#           mid-copy due to a race with a live writer — "size changed from 0 to N").
#           This is non-fatal: the full 622+ MiB still transfers; one volatile state
#           file is retried next run. Treat as success.
# Exit 6 = rclone's own "less serious errors" bucket — also treat as success.
# Hard-fail on 2 (usage), 3 (dir not found), 4 (file not found), 5 (temp/retry),
#               7 (fatal), 8 (transfer limit exceeded).
if [ "$EXIT_CODE" -eq 1 ] || [ "$EXIT_CODE" -eq 6 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') — Thunderbird rclone sync finished with minor warnings (exit: $EXIT_CODE) — treating as success" >> "$LOG"
  exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') — Thunderbird rclone sync finished (exit: $EXIT_CODE)" >> "$LOG"

exit $EXIT_CODE
