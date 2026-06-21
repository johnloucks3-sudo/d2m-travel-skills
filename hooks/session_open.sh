#!/bin/bash
# Session-open forcing function — runs via SessionStart hook.
# Closes non-gated missions, checks credentials, surfaces action queue.
# Initiative gap fix: Wing acts on state, not prompts.

set -euo pipefail

TBIRD="/home/john/Thunderbird"
LOG="$TBIRD/logs/session_open.log"
REPORT="$TBIRD/session_open_report.md"

mkdir -p "$TBIRD/logs"

echo "=== SESSION OPEN $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

# 1. Session init (persona inboxes + credential timers)
python3 "$TBIRD/OpsCenter/session_init.py" >> "$LOG" 2>&1 || true

# 2. Mission auto-executor (classify + auto-close)
python3 "$TBIRD/OpsCenter/mission_auto_executor.py" >> "$LOG" 2>&1 || true

# 3. Session context blast (refresh OpsCenter/session_context_latest.md)
python3 "$TBIRD/core/memory/session_context_blast.py" >> "$LOG" 2>&1 || true

echo "=== DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

# Surface the report path so Hale sees it on session open
if [ -f "$REPORT" ]; then
    echo ""
    echo "🦅 SESSION OPEN COMPLETE — report at $REPORT"
fi
