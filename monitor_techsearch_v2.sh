#!/bin/bash

# Monitor watcher and claude_outbox for SPECIFIC tech search task completion
# Checks every 2 minutes until our task appears in claude_outbox.md

TASK_ID="TECHSECARCH-CLAUDECODE-20-20260424"
OUTBOX_FILE="/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md"
LOGFILE="/home/john/Thunderbird/logs/techsearch_monitor_detailed.log"

echo "=== Tech Search Task Monitor V2 (Specific) ===" | tee -a "$LOGFILE"
echo "Task ID: $TASK_ID" | tee -a "$LOGFILE"
echo "Start time: $(date '+%Y-%m-%d %H:%M:%S MT')" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

check_count=0
max_checks=30  # 60 minutes total
task_started=false

# Function to check for our specific task completion
check_task_completion() {
    # Check for our exact task ID or clear indicators
    if grep -q "TECHSECARCH\|20 distinct.*claude.code\|claude-code.*20 results" "$OUTBOX_FILE" 2>/dev/null; then
        echo "✅ SPECIFIC TASK FOUND in claude_outbox.md!" | tee -a "$LOGFILE"
        return 0
    fi
    
    # Check for new content added after our start time
    local outbox_mtime=$(stat -c %Y "$OUTBOX_FILE" 2>/dev/null || echo 0)
    local start_time=$(date -d "2026-04-24 06:15:00" +%s 2>/dev/null || echo 0)
    
    if [ $outbox_mtime -gt $start_time ]; then
        echo "⚠️  Outbox modified after task injection time - checking for new tech search content" | tee -a "$LOGFILE"
        # Get the last 50 lines added (approximate)
        local line_count=$(wc -l < "$OUTBOX_FILE" 2>/dev/null || echo 0)
        if [ $line_count -gt 50 ]; then
            tail -50 "$OUTBOX_FILE" | grep -q -i "tool.*table\|github.*stars\|collaboration.*features" && {
                echo "✅ NEW tech search content found in outbox!" | tee -a "$LOGFILE"
                return 0
            }
        fi
    fi
    
    return 1
}

while [ $check_count -lt $max_checks ]; do
    check_count=$((check_count + 1))
    current_time=$(date '+%Y-%m-%d %H:%M:%S MT')
    
    echo "=== Check #$check_count at $current_time ===" | tee -a "$LOGFILE"
    
    # 1. Check task status in claude_inbox
    echo "Task status in claude_inbox.md:" | tee -a "$LOGFILE"
    if grep -q "## TASK: $TASK_ID" /home/john/Thunderbird/claude_inbox.md; then
        task_line=$(grep -n "## TASK: $TASK_ID" /home/john/Thunderbird/claude_inbox.md | head -1)
        task_line_num=${task_line%%:*}
        
        # Get the status line (should be 2 lines after task header)
        status_line=$((task_line_num + 2))
        sed -n "${status_line}p" /home/john/Thunderbird/claude_inbox.md | tee -a "$LOGFILE"
        
        # Check if status changed from UNREAD
        if sed -n "${status_line}p" /home/john/Thunderbird/claude_inbox.md | grep -q "UNREAD"; then
            echo "Task still UNREAD" | tee -a "$LOGFILE"
        else
            echo "Task status CHANGED - may be processing or completed" | tee -a "$LOGFILE"
            task_started=true
        fi
    else
        echo "Task NOT FOUND in claude_inbox.md - may have been removed after processing" | tee -a "$LOGFILE"
        task_started=true
    fi
    
    # 2. Check watcher logs for activity related to our task
    echo -e "\nChecking watcher logs for recent activity:" | tee -a "$LOGFILE"
    tail -10 /home/john/Thunderbird/logs/inbox_watcher.log 2>/dev/null | grep -E "(spawn|claude.*headless|UNREAD|processing)" | tail -3 | tee -a "$LOGFILE"
    
    # 3. Check claude_headless logs for recent runs
    echo -e "\nChecking claude_headless logs:" | tee -a "$LOGFILE"
    tail -5 /home/john/Thunderbird/logs/claude_headless.log 2>/dev/null | tee -a "$LOGFILE" || echo "No claude_headless logs" | tee -a "$LOGFILE"
    
    # 4. Check for our specific task in outbox
    echo -e "\nChecking for specific task in claude_outbox.md:" | tee -a "$LOGFILE"
    if check_task_completion; then
        echo -e "\n🎯 TASK COMPLETED SUCCESSFULLY!" | tee -a "$LOGFILE"
        echo "Monitor ending." | tee -a "$LOGFILE"
        exit 0
    else
        echo "Task NOT YET in outbox" | tee -a "$LOGFILE"
    fi
    
    # 5. Check outbox file modification time
    if [ -f "$OUTBOX_FILE" ]; then
        outbox_mtime=$(date -d "@$(stat -c %Y "$OUTBOX_FILE" 2>/dev/null)" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "unknown")
        echo "Outbox last modified: $outbox_mtime" | tee -a "$LOGFILE"
    fi
    
    echo -e "\n--- Next check in 2 minutes (total checks: $check_count/$max_checks) ---\n" | tee -a "$LOGFILE"
    
    # Wait 2 minutes before next check
    if [ $check_count -lt $max_checks ]; then
        sleep 120
    fi
done

echo -e "\n⏰ MONITOR TIMEOUT: Checked $max_checks times (60 minutes total)" | tee -a "$LOGFILE"
echo "Task may have failed or is taking longer than expected" | tee -a "$LOGFILE"
echo "Recommended manual checks:" | tee -a "$LOGFILE"
echo "1. Check watcher: tail -f /home/john/Thunderbird/logs/inbox_watcher.log" | tee -a "$LOGFILE"
echo "2. Check claude_headless: tail -f /home/john/Thunderbird/logs/claude_headless.log" | tee -a "$LOGFILE"
echo "3. Check OAuth: cat /home/john/Thunderbird/OpsCenter/.claude_oauth_cache" | tee -a "$LOGFILE"
echo "4. Check task status manually in claude_inbox.md" | tee -a "$LOGFILE"
exit 1