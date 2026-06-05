#!/usr/bin/env bash
# auto_session_monitor.sh — 10-min session health check
# Fires via auto-session-monitor.timer (every 10 min)
# Logs to: logs/auto_session_monitor_systemd.log
# Created: 2026-06-05 (MISSION-111 follow-up — staying time fix)

set -euo pipefail

THUNDERBIRD_DIR="/home/john/Thunderbird"
LOG="$THUNDERBIRD_DIR/logs/auto_session_monitor.log"
INBOX="$THUNDERBIRD_DIR/OpsCenter/collaboration/opencode_inbox.md"
WING_COMMS="$THUNDERBIRD_DIR/OpsCenter/collaboration/wing_comms.md"
PERSONA_NOTES="$THUNDERBIRD_DIR/Personas/memory/COS/session_notes.md"
MISSION_BOARD="$THUNDERBIRD_DIR/OpsCenter/mission_board.json"

TS=$(date "+%Y-%m-%d %H:%M MT")
HOUR=$(date +%H)

mkdir -p "$THUNDERBIRD_DIR/logs"

log() {
    echo "[$TS] $*" | tee -a "$LOG"
}

# ── 1. Session process check ────────────────────────────────────────────────
SESSION_PROCS=$(pgrep -f "claude.*--continue\|opencode.*--continue\|claude.*-p " 2>/dev/null | wc -l || echo 0)
if [ "$SESSION_PROCS" -gt 0 ]; then
    SESSION_STATUS="ACTIVE ($SESSION_PROCS procs)"
else
    SESSION_STATUS="IDLE"
fi

# ── 2. Token validity check ─────────────────────────────────────────────────
CREDS_FILE="$HOME/.claude/.credentials.json"
TOKEN_STATUS="UNKNOWN"
if [ -f "$CREDS_FILE" ]; then
    # Just check file is non-empty and recently touched
    CREDS_AGE=$(( $(date +%s) - $(stat -c %Y "$CREDS_FILE" 2>/dev/null || echo 0) ))
    if [ "$CREDS_AGE" -lt 3600 ]; then
        TOKEN_STATUS="FRESH (${CREDS_AGE}s old)"
    else
        TOKEN_STATUS="STALE (${CREDS_AGE}s old)"
    fi
fi

# ── 3. Inbox pending check ──────────────────────────────────────────────────
PENDING_COUNT=0
if [ -f "$INBOX" ]; then
    PENDING_COUNT=$(grep -c "PENDING\|UNREAD" "$INBOX" 2>/dev/null || echo 0)
fi

# ── 4. Mission board task count ─────────────────────────────────────────────
ACTIVE_TASKS=0
if [ -f "$MISSION_BOARD" ]; then
    ACTIVE_TASKS=$(python3 -c "
import json, sys
try:
    d = json.load(open('$MISSION_BOARD'))
    tasks = d.get('tasks', [])
    active = [t for t in tasks if t.get('status','') in ('in_progress','pending')]
    print(len(active))
except:
    print(0)
" 2>/dev/null || echo 0)
fi

# ── 5. Qdrant health ────────────────────────────────────────────────────────
QDRANT_STATUS="DOWN"
if curl -sf http://localhost:6333/health >/dev/null 2>&1; then
    QDRANT_STATUS="UP"
fi

# ── 6. Log the check-in ─────────────────────────────────────────────────────
STATUS_LINE="SESSION=$SESSION_STATUS | TOKEN=$TOKEN_STATUS | INBOX_PENDING=$PENDING_COUNT | ACTIVE_TASKS=$ACTIVE_TASKS | QDRANT=$QDRANT_STATUS"
log "CHECK-IN: $STATUS_LINE"

# ── 7. Write to wing_comms if overnight (22:00–06:00) and issues found ──────
if [ "$HOUR" -ge 22 ] || [ "$HOUR" -lt 6 ]; then
    if [ "$PENDING_COUNT" -gt 0 ] || [ "$QDRANT_STATUS" = "DOWN" ]; then
        printf "\n### AUTO-MONITOR %s\n%s\n" "$TS" "$STATUS_LINE" >> "$WING_COMMS"
    fi
fi

# ── 8. Append heartbeat to COS persona memory ───────────────────────────────
if [ -f "$PERSONA_NOTES" ]; then
    printf "\n### %s [auto-monitor]\n[heartbeat] %s\n" "$TS" "$STATUS_LINE" >> "$PERSONA_NOTES"
fi

exit 0
