#!/bin/bash
# auto_inject_inbox.sh — UserPromptSubmit hook
# Fires on every user message in Claude Code.
# Watches BOTH inbox files — OpsCenter collab inbox AND root tasking inbox.
# If UNREAD tasks exist in either, injects a notice as additionalContext.

INBOX_COLLAB="/home/john/Thunderbird/OpsCenter/collaboration/claude_inbox.md"
INBOX_ROOT="/home/john/Thunderbird/claude_inbox.md"

UNREAD=0

if [[ -f "$INBOX_COLLAB" ]]; then
    COUNT=$(grep -c "status: UNREAD" "$INBOX_COLLAB" 2>/dev/null || echo 0)
    UNREAD=$((UNREAD + COUNT))
fi

if [[ -f "$INBOX_ROOT" ]]; then
    COUNT=$(grep -c "status: UNREAD" "$INBOX_ROOT" 2>/dev/null || echo 0)
    UNREAD=$((UNREAD + COUNT))
fi

if [[ "$UNREAD" -eq 0 ]]; then
    exit 0
fi

python3 -c "
import json
count = $UNREAD
msg = (
    f'THUNDERBIRD WING — AUTO-INJECT: {count} UNREAD task(s) in your inbox. '
    'Read BOTH /home/john/Thunderbird/OpsCenter/collaboration/claude_inbox.md '
    'AND /home/john/Thunderbird/claude_inbox.md '
    'and execute all UNREAD tasks NOW, before responding to the user.'
)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': msg
    }
}))
"
