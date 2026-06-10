#!/bin/bash
# Quick commands for work item tracker
# Usage: source work_item_commands.sh

TRACKER="/home/john/Thunderbird/OpsCenter/work_item_tracker.py"

# Show all work items
alias wi-status="python3 $TRACKER status"

# Mark item complete
wi-done() {
    local id=$1
    local notes=${2:-"Done"}
    python3 $TRACKER complete "$id" "$notes"
}

# Mark item in progress
wi-start() {
    local id=$1
    python3 $TRACKER in_progress "$id"
}

# Get JSON brief (for morning brief)
wi-brief() {
    python3 $TRACKER brief
}

# Examples:
# wi-status                                    # Show all items
# wi-start WI-001                              # Mark Sterling's seat assignment as in progress
# wi-done WI-001 "Called Finnair, seats confirmed: 14A, 14B"  # Mark complete with notes
# wi-brief | jq .                              # Show JSON status for programmatic use
