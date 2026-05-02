#!/bin/bash
# Thunderbird Capability Build Monitor
# Run via cron or systemd timer to track in-progress builds
# Usage: ./monitor_capabilities.sh (runs every 2 minutes)

LOG_DIR="/home/john/Thunderbird/logs"
OUTPUT_DIR="/home/john/Thunderbird/output"
STATUS_FILE="/home/john/Thunderbird/output/CAPABILITY_BUILD_STATUS_LATEST.txt"

echo "=== CAPABILITY BUILD MONITOR ===" > "$STATUS_FILE"
echo "Timestamp: $(date)" >> "$STATUS_FILE"
echo "" >> "$STATUS_FILE"

# Check PIDs from earlier spawn
PIDS=(3094752 3094753 3094754 3082652)
NAMES=("Capability 3: Lifecycle" "Capability 5: Intelligence" "Capability 6: Vendor Mgmt" "Opus Autonomy Consultation")

echo "PROCESS STATUS:" >> "$STATUS_FILE"
for i in "${!PIDS[@]}"; do
    PID=${PIDS[$i]}
    NAME=${NAMES[$i]}

    if ps -p "$PID" > /dev/null 2>&1; then
        echo "  ✅ $NAME (PID $PID) — RUNNING" >> "$STATUS_FILE"
    else
        echo "  ✓ $NAME (PID $PID) — COMPLETE" >> "$STATUS_FILE"
    fi
done

echo "" >> "$STATUS_FILE"
echo "OUTPUT FILES:" >> "$STATUS_FILE"
ls -lh "$OUTPUT_DIR"/CAPABILITY_*.txt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' >> "$STATUS_FILE" || echo "  (None yet)" >> "$STATUS_FILE"
ls -lh "$OUTPUT_DIR"/OPUS_AUTONOMY_*.txt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' >> "$STATUS_FILE" || echo "  (None yet)" >> "$STATUS_FILE"

echo "" >> "$STATUS_FILE"
echo "ERROR CHECK:" >> "$STATUS_FILE"
grep -i "error\|failed\|fatal" "$LOG_DIR"/capability_*.log 2>/dev/null | head -5 >> "$STATUS_FILE" || echo "  No errors detected" >> "$STATUS_FILE"
grep -i "error\|failed\|fatal" "$LOG_DIR"/opus_autonomy_*.log 2>/dev/null | head -5 >> "$STATUS_FILE" || echo "  No errors detected" >> "$STATUS_FILE"

echo "" >> "$STATUS_FILE"
echo "Last update: $(date)" >> "$STATUS_FILE"

# Print to console
cat "$STATUS_FILE"
