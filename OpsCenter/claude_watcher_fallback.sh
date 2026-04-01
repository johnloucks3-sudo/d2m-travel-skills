#!/bin/bash
# A7 METRIC: Watcher Redundancy (Cron Fallback)
INBOX="/home/john/Thunderbird/claude_inbox.md"
LOG="/home/john/Thunderbird/OpsCenter/overwatch.log"

# Check if file exists and has content (more than just empty brackets)
if [ -s "$INBOX" ] && [ $(wc -c < "$INBOX") -gt 10 ]; then
    MOD_TIME=$(stat -c %Y "$INBOX")
    CUR_TIME=$(date +%s)
    AGE=$((CUR_TIME - MOD_TIME))
    
    if [ "$AGE" -gt 300 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [A7 AUDIT] claude_inbox.md is STALE ($AGE seconds). Watcher failed silently. Force-triggering execution..." >> "$LOG"
        
        # Force a modification event to wake the watchdog, or run directly
        touch "$INBOX"
        
        # If it stays stuck, we restart the service
        sleep 10
        if [ $(stat -c %Y "$INBOX") -eq $MOD_TIME ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [A7 AUDIT] Force-touch failed. Restarting thunderbird-inbox-watcher service..." >> "$LOG"
            systemctl --user restart thunderbird-inbox-watcher
        fi
    fi
fi

