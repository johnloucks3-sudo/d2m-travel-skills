#!/usr/bin/env bash
# batch-add.sh — Quick-add a Claude Code batch task for off-peak execution
#
# Usage:
#   ./scripts/batch-add.sh "Review all dossiers and update payment statuses"
#   ./scripts/batch-add.sh --priority 1 "Fix the commission calculation bug"
#
# Tasks are queued in batch_tasks.json and run during off-peak hours by
# the thunderbird-batch.timer systemd service.

set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

QUEUE="batch_tasks.json"
PRIORITY=3

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --priority|-p)
            PRIORITY="$2"
            shift 2
            ;;
        --help|-h)
            head -10 "$0" | grep '^#' | sed 's/^# \?//'
            exit 0
            ;;
        *)
            PROMPT="$1"
            shift
            ;;
    esac
done

if [[ -z "${PROMPT:-}" ]]; then
    echo "Usage: batch-add.sh [--priority N] \"task prompt\""
    exit 1
fi

# Initialize queue if needed
if [[ ! -f "$QUEUE" ]]; then
    echo "[]" > "$QUEUE"
fi

TASK_ID="cli-$(date +%Y%m%d-%H%M%S)"
TIMESTAMP=$(date -Iseconds)

# Append task using python for clean JSON manipulation
/home/john/Thunderbird/.venv/bin/python3 -c "
import json, sys
queue = json.loads(open('$QUEUE').read())
queue.append({
    'id': '$TASK_ID',
    'name': sys.argv[1][:60],
    'prompt': sys.argv[1],
    'type': 'claude_cli',
    'priority': int(sys.argv[2]),
    'status': 'pending',
    'created': '$TIMESTAMP',
})
open('$QUEUE', 'w').write(json.dumps(queue, indent=2))
print(f'Queued: {sys.argv[1][:60]}')
print(f'ID: $TASK_ID | Priority: {sys.argv[2]}')
print(f'Queue depth: {sum(1 for t in queue if t[\"status\"]==\"pending\")} pending')
" "$PROMPT" "$PRIORITY"
