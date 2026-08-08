#!/usr/bin/env bash
# claude_sync_push.sh — wraps claude-sync push, treating the transient .in_use
# TOCTOU race as non-fatal. The .in_use/<PID> files are ephemeral process locks
# that can vanish between claude-sync's directory scan and its hash step.
set -euo pipefail

LOG="${HOME}/.claude/sync.log"
# Resolve claude-sync to its real install path on first hit (systemd user units
# do not inherit ~/.claude/bin on PATH — a bare `claude-sync` call exits 127
# "command not found", which stymies both this wrapper and systemd start).
CLAUDE_SYNC="${CLAUDE_SYNC:-$HOME/.local/bin/claude-sync}"
TMPOUT=$(mktemp)
trap 'rm -f "$TMPOUT"' EXIT

"$CLAUDE_SYNC" push > "$TMPOUT" 2>&1
RC=$?

cat "$TMPOUT" >> "$LOG"

if [ "$RC" -ne 0 ]; then
    # Only suppress exit if the failure is purely the ephemeral .in_use race
    if grep -qE "failed to (detect changes|hash).*\.in_use.*no such file" "$TMPOUT" && \
       ! grep -qE "failed to upload|Error:(?!.*\.in_use)" "$TMPOUT"; then
        TS=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$TS] WARNING: Transient .in_use PID-file race — treating as success" >> "$LOG"
        exit 0
    fi
fi

exit "$RC"
