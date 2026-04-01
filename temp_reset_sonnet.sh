#!/bin/bash
# A simple, self-contained script to wait until 21:01 and then reset the Sonnet limit.

# Calculate seconds to wait until 9:01 PM (21:01)
TARGET_EPOCH=$(date -d "21:01" +%s)
NOW_EPOCH=$(date +%s)
SECONDS_TO_WAIT=$((TARGET_EPOCH - NOW_EPOCH))

# Only proceed if the target time is in the future
if [ "$SECONDS_TO_WAIT" -gt 0 ]; then
    echo "Waiting for ${SECONDS_TO_WAIT} seconds until 21:01 to reset Sonnet limit."
    sleep "$SECONDS_TO_WAIT"
    
    echo "Executing Sonnet reset command."
    python3 /home/john/Thunderbird/OpsCenter/claude_usage_tracker.py reset-sonnet
else
    echo "Target time of 21:01 has already passed. No action taken."
fi
