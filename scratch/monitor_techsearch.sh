#!/bin/bash

# Monitor watcher and claude_outbox for tech search task completion
# Checks every 2 minutes until task appears in claude_outbox.md

TASK_ID="TECHSECARCH-CLAUDECODE-20-20260424"
OUTBOX_FILE="/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md"
LOGFILE="/home/john/Thunderbird/logs/techsearch_monitor.log"

echo "=== Tech Search Task Monitor ===" | tee -a "$LOGFILE"
echo "Task ID: $TASK_ID" | tee -a "$LOGFILE"
echo "Start time: $(date '+%Y-%m-%d %H:%M:%S MT')" | tee -a "$LOGFILE"
echo "Checking every 2 minutes..." | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

check_count=0
max_checks=30  # 60 minutes total

while [ $check_count -lt $max_checks ]; do
    check_count=$((check_count + 1))
    current_time=$(date '+%Y-%m-%d %H:%M:%S MT')
    
    echo "=== Check #$check_count at $current_time ===" | tee -a "$LOGFILE"
    
    # 1. Check if task is still UNREAD in claude_inbox
    if grep -q "## TASK: $TASK_ID" /home/john/Thunderbird/claude_inbox.md; then
        task_status=$(grep -A1 "## TASK: $TASK_ID" /home/john/Thunderbird/claude_inbox.md | grep "status:" | cut -d':' -f2 | xargs)
        echo "Task found in claude_inbox.md - Status: $task_status" | tee -a "$LOGFILE"
        
        if [ "$task_status" = "UNREAD" ]; then
            echo "Task still UNREAD - watcher may not have picked it up yet" | tee -a "$LOGFILE"
        else
            echo "Task status changed to: $task_status" | tee -a "$LOGFILE"
        fi
    else
        echo "Task NOT found in claude_inbox.md - may have been removed after processing" | tee -a "$LOGFILE"
    fi
    
    # 2. Check watcher service status
    echo "Watcher service status:" | tee -a "$LOGFILE"
    systemctl --user status d2m-tasking-watcher.service --no-pager | head -10 | tee -a "$LOGFILE"
    
    # 3. Check watcher logs for recent activity
    echo -e "\nRecent watcher logs (last 5 lines):" | tee -a "$LOGFILE"
    tail -5 /home/john/Thunderbird/logs/inbox_watcher.log 2>/dev/null | tee -a "$LOGFILE" || echo "No watcher logs found" | tee -a "$LOGFILE"
    
    # 4. Check claude_headless logs
    echo -e "\nRecent claude_headless logs (last 3 lines):" | tee -a "$LOGFILE"
    tail -3 /home/john/Thunderbird/logs/claude_headless.log 2>/dev/null | tee -a "$LOGFILE" || echo "No claude_headless logs found" | tee -a "$LOGFILE"
    
    # 5. Check if task appears in claude_outbox
    if [ -f "$OUTBOX_FILE" ]; then
        if grep -q -i "claude.code\|tech.*search\|20.*results" "$OUTBOX_FILE"; then
            echo -e "\n✅ FOUND: Tech search content in claude_outbox.md!" | tee -a "$LOGFILE"
            echo "First matching line:" | tee -a "$LOGFILE"
            grep -i -m1 "claude.code\|tech.*search\|20.*results" "$OUTBOX_FILE" | tee -a "$LOGFILE"
            echo -e "\n🎯 TASK COMPLETED! Monitor ending." | tee -a "$LOGFILE"
            exit 0
        else
            echo -e "\n❌ NOT FOUND: No tech search content in claude_outbox.md yet" | tee -a "$LOGFILE"
            echo "Outbox file size: $(wc -l < "$OUTBOX_FILE") lines" | tee -a "$LOGFILE"
        fi
    else
        echo -e "\n❌ Outbox file does not exist: $OUTBOX_FILE" | tee -a "$LOGFILE"
    fi
    
    # 6. Check for any errors or timeouts in watcher logs
    if tail -20 /home/john/Thunderbird/logs/inbox_watcher.log 2>/dev/null | grep -q -i "error\|timeout\|failed\|401\|oauth"; then
        echo -e "\n⚠️ WARNING: Potential errors detected in watcher logs:" | tee -a "$LOGFILE"
        tail -20 /home/john/Thunderbird/logs/inbox_watcher.log 2>/dev/null | grep -i "error\|timeout\|failed\|401\|oauth" | head -3 | tee -a "$LOGFILE"
    fi
    
    echo -e "\n--- Next check in 2 minutes ---\n" | tee -a "$LOGFILE"
    
    # Wait 2 minutes before next check
    if [ $check_count -lt $max_checks ]; then
        sleep 120
    fi
done

echo -e "\n⏰ MONITOR TIMEOUT: Checked $max_checks times (60 minutes total)" | tee -a "$LOGFILE"
echo "Task may have failed or is taking longer than expected" | tee -a "$LOGFILE"
echo "Check logs manually:" | tee -a "$LOGFILE"
echo "  tail -f /home/john/Thunderbird/logs/inbox_watcher.log" | tee -a "$LOGFILE"
echo "  tail -f /home/john/Thunderbird/logs/claude_headless.log" | tee -a "$LOGFILE"
exit 1