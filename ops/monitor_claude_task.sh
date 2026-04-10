#!/bin/bash
# Monitor Claude task status
TASK_ID="CLAUDE-HAIKU-GMAIL-PROTOCOL-001"
INBOX_FILE="/home/john/Thunderbird/claude_inbox.md"
LOG_FILE="/home/john/Thunderbird/logs/task_monitor.log"

# Create log directory if needed
mkdir -p /home/john/Thunderbird/logs

echo "Monitoring task: $TASK_ID" | tee -a $LOG_FILE
echo "Start time: $(date)" | tee -a $LOG_FILE

# Check initial status
if grep -q "status: UNREAD" $INBOX_FILE && grep -q "$TASK_ID" $INBOX_FILE; then
    echo "✅ Task $TASK_ID found with UNREAD status" | tee -a $LOG_FILE
else
    echo "❌ Task $TASK_ID not found or not UNREAD" | tee -a $LOG_FILE
    exit 1
fi

# Monitor for 30 minutes max
for i in {1..6}; do
    echo "Check $i: $(date)" | tee -a $LOG_FILE
    
    if grep -q "status: COMPLETE" $INBOX_FILE && grep -q "$TASK_ID" $INBOX_FILE; then
        echo "🎉 Task $TASK_ID COMPLETED!" | tee -a $LOG_FILE
        echo "Results:" | tee -a $LOG_FILE
        grep -A 20 -B 5 "$TASK_ID" $INBOX_FILE | tee -a $LOG_FILE
        exit 0
    fi
    
    if [ $i -eq 3 ]; then
        echo "⚠️  15 minutes elapsed - task still UNREAD" | tee -a $LOG_FILE
    fi
    
    if [ $i -eq 6 ]; then
        echo "🚨 30 minutes elapsed - TASK TIMEOUT" | tee -a $LOG_FILE
        echo "ESCALATING TO COMMANDER" | tee -a $LOG_FILE
        # Add escalation logic here
        exit 2
    fi
    
    sleep 300 # 5 minutes

done
