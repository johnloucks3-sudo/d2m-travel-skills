#!/bin/bash
# Session-open forcing function — runs via SessionStart hook.
# Closes non-gated missions, checks credentials, surfaces action queue.
# Initiative gap fix: Wing acts on state, not prompts.

set -euo pipefail

# Skip expensive init in headless/dispatch mode (no TTY = non-interactive subprocess)
if [ ! -t 0 ]; then
    echo '{"continue": true, "suppressOutput": true}'
    exit 0
fi

TBIRD="/home/john/Thunderbird"
LOG="$TBIRD/logs/session_open.log"
REPORT="$TBIRD/session_open_report.md"

mkdir -p "$TBIRD/logs"

echo "=== SESSION OPEN $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

# 0a. llmtrim — ensure daemon running, export proxy for all subprocesses this session
if ! pgrep -x llmtrim >/dev/null 2>&1; then
    llmtrim start >> "$LOG" 2>&1 || true
fi
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:43117}"
export NODE_EXTRA_CA_CERTS="${NODE_EXTRA_CA_CERTS:-$HOME/.llmtrim/ca.pem}"

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
