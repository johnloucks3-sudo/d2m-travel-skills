#!/bin/bash

# Monitor for OpenCode tech search task completion
# Checks every 2 minutes until task appears in opencode_outbox.md

OUTBOX_FILE="/home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md"
TASK_ID="TECHSECARCH-CLAUDECODE-20-OPENC-20260424"
LOGFILE="/home/john/Thunderbird/logs/opencode_techsearch_monitor.log"

echo "=== OpenCode Tech Search Monitor ===" | tee -a "$LOGFILE"
echo "Task ID: $TASK_ID" | tee -a "$LOGFILE"
echo "Start time: $(date '+%Y-%m-%d %H:%M:%S MT')" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

check_count=0
max_checks=15  # 30 minutes total

while [ $check_count -lt $max_checks ]; do
    check_count=$((check_count + 1))
    current_time=$(date '+%Y-%m-%d %H:%M:%S MT')
    
    echo "=== Check #$check_count at $current_time ===" | tee -a "$LOGFILE"
    
    # Check if task is still UNREAD
    if grep -q "## TASK: $TASK_ID" /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md; then
        task_status=$(grep -A1 "## TASK: $TASK_ID" /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md | grep "status:" | cut -d':' -f2 | xargs)
        echo "Task status: $task_status" | tee -a "$LOGFILE"
    else
        echo "Task NOT FOUND in opencode_inbox.md - may have been processed" | tee -a "$LOGFILE"
    fi
    
    # Check watcher logs for OpenCode activity
    echo -e "\nRecent watcher logs (OpenCode related):" | tee -a "$LOGFILE"
    tail -10 /home/john/Thunderbird/logs/inbox_watcher.log 2>/dev/null | grep -i "opencode\|spawn.*deepseek" | tail -3 | tee -a "$LOGFILE"
    
    # Check if task appears in opencode_outbox
    if [ -f "$OUTBOX_FILE" ]; then
        outbox_size=$(wc -l < "$OUTBOX_FILE")
        echo "Outbox file exists: $outbox_size lines" | tee -a "$LOGFILE"
        
        # Check for tech search content
        if grep -q -i "claude.*code\|tech.*search\|20.*results\|tool.*table" "$OUTBOX_FILE"; then
            echo -e "\n✅ FOUND: Tech search content in opencode_outbox.md!" | tee -a "$LOGFILE"
            echo "First matching line:" | tee -a "$LOGFILE"
            grep -i -m1 "claude.*code\|tech.*search\|20.*results" "$OUTBOX_FILE" | tee -a "$LOGFILE"
            echo -e "\n🎯 TASK COMPLETED! Monitor ending." | tee -a "$LOGFILE"
            exit 0
        else
            echo "No tech search content in outbox yet" | tee -a "$LOGFILE"
        fi
    else
        echo "Outbox file does not exist yet" | tee -a "$LOGFILE"
        # Touch it to create if needed
        touch "$OUTBOX_FILE" 2>/dev/null
    fi
    
    echo -e "\n--- Next check in 2 minutes (check $check_count/$max_checks) ---\n" | tee -a "$LOGFILE"
    
    if [ $check_count -lt $max_checks ]; then
        sleep 120
    fi
done

echo -e "\n⏰ MONITOR TIMEOUT: Checked $max_checks times (30 minutes)" | tee -a "$LOGFILE"
echo "Task may be taking longer than expected" | tee -a "$LOGFILE"
echo "Manual check commands:" | tee -a "$LOGFILE"
echo "  tail -f /home/john/Thunderbird/logs/inbox_watcher.log" | tee -a "$LOGFILE"
echo "  ls -la /home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md" | tee -a "$LOGFILE"
exit 1