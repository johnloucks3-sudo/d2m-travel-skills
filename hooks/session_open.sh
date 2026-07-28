#!/bin/bash
# Session-open forcing function — runs via SessionStart hook.
# Closes non-gated missions, checks credentials, surfaces action queue.
# Initiative gap fix: Wing acts on state, not prompts.
#
# FIXED 2026-07-16 (hot-window triage): this used to skip ALL init work
# (session_init.py, mission_auto_executor.py, session_context_blast.py)
# whenever stdin wasn't a TTY, on the assumption that "no TTY" meant a
# throwaway headless one-off. Headless/dispatched sessions are now the
# NORMAL way most work runs, not the exception -- this silently stopped
# the deferred-alert pipeline and session_open_report.md for 14+ days
# straight with zero error surfaced. SessionStart hooks run async with
# their own timeout budget regardless of TTY, so there's no real cost to
# always doing the work; only the human-readable completion banner is now
# gated on TTY, since headless/API contexts don't need it printed.

set -euo pipefail

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

if [ -t 0 ]; then
    # Interactive terminal: surface the report path for a human to see.
    if [ -f "$REPORT" ]; then
        echo ""
        echo "🦅 SESSION OPEN COMPLETE — report at $REPORT"
    fi
else
    # Headless/dispatched: work is done (above), just ack the hook cleanly.
    echo '{"continue": true, "suppressOutput": true}'
fi
