#!/bin/bash
# Daily wrapper for Hale Touchpoint Proposer
# Runs --propose for all known clients without profiles (new bookings)
# OAuth tokens auto-injected by systemd (see hale-touchpoint-proposer.service)

set -euo pipefail

SCRIPT_DIR="/home/john/Thunderbird/D2M"
CLIENTS_DIR="/home/john/Thunderbird/D2M/clients"
LOG_FILE="/home/john/Thunderbird/logs/hale_touchpoint_proposer.log"
OAUTH_CACHE="${HOME}/.claude/oauth/google_token.json"

# Set OAuth env vars for any subprocess Claude calls
if [ -f "$OAUTH_CACHE" ]; then
    export GOOGLE_OAUTH_TOKEN=$(jq -r '.access_token // empty' "$OAUTH_CACHE" 2>/dev/null || echo "")
    export DRIVE_TOKEN_PATH="$OAUTH_CACHE"
fi

echo "[$(date)] ─── Hale Touchpoint Proposer Daily Scan ───" >> "$LOG_FILE"

# Check for new client profiles without corresponding touchpoint JSON
for profile_json in "$CLIENTS_DIR"/*_profile.json; do
    [ -f "$profile_json" ] || continue

    client_id=$(basename "$profile_json" _profile.json)
    touchpoint_json="$CLIENTS_DIR/${client_id}_touchpoints.json"

    # Skip if touchpoint JSON already exists
    if [ -f "$touchpoint_json" ]; then
        echo "[$(date)] ℹ️  $client_id: touchpoints already exist" >> "$LOG_FILE"
        continue
    fi

    echo "[$(date)] 📋 Proposing schedule for: $client_id" >> "$LOG_FILE"
    python3 "$SCRIPT_DIR/hale_touchpoint_proposer.py" \
        --client "$client_id" \
        --propose \
        >> "$LOG_FILE" 2>&1

    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ Proposal posted to claude_inbox.md" >> "$LOG_FILE"
    else
        echo "[$(date)] ❌ Proposal failed for $client_id" >> "$LOG_FILE"
    fi
done

echo "[$(date)] ─── Scan complete ───" >> "$LOG_FILE"
