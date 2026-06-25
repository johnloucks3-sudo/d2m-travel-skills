#!/usr/bin/env bash
# detect_max_exhaustion.sh — Stop hook for Claude MAX exhaustion
#
# Installed as a Claude Code Stop hook. Fires when a session ends.
# If the session was running under MAX and scored tool-success rate
# below threshold, flags the rate_limit_guard to degrade gracefully
# and may escalate to the claude-fb fallback wrapper on next session.
#
# Install:  registered in ~/.claude/settings.json hooks.Stop[]
# Logs:     ~/Thunderbird/logs/max_exhaustion_hook.log
# Notify:   writes to ~/Thunderbird/OpsCenter/max_exhaustion_flag

ME="max-exhaustion-hook"
FLAG_FILE="$HOME/Thunderbird/OpsCenter/max_exhaustion_flag"
LOG_FILE="$HOME/Thunderbird/logs/max_exhaustion_hook.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

log() { echo "[$TIMESTAMP] $ME: $*" >> "$LOG_FILE"; }
log "Stop hook fired"

# ── Detect whether we hit a MAX rate limit / budget exhaustion ──────────────
# Check if the session exit signal was non-zero (common on rate-limit kills)
EXIT_CODE=${CLAUDE_EXIT_CODE:-$?}
log "Session exit code: $EXIT_CODE"

# If exit code 137 (SIGKILL from OOM/kill), 130 (SIGINT), or non-zero
# — likely a rate-limit or budget exhaustion kill from max_proxy
if [ "$EXIT_CODE" -eq 137 ] || [ "$EXIT_CODE" -eq 130 ] || [ "$EXIT_CODE" -ne 0 ]; then
    log "Detected abnormal exit ($EXIT_CODE) — likely budget/rate-limit kill"

    # Write flag file so rate_limit_guard daemon or next session sees it
    echo "{\"detected_at\":\"$TIMESTAMP\",\"exit_code\":$EXIT_CODE,\"state\":\"EXHAUSTED\"}" > "$FLAG_FILE"
    log "Wrote exhaustion flag to $FLAG_FILE"

    # Check remaining budget from guard state
    if [ -f "$HOME/Thunderbird/hale_state.json" ]; then
        python3 -c "
import json
try:
    with open('$HOME/Thunderbird/hale_state.json') as f:
        s = json.load(f)
    pct = s.get('weekly_usage_pct', 0)
    print(f'Weekly usage: {pct}%')
    if pct >= 90:
        print('HARD_STOP')
    elif pct >= 85:
        print('CRIT')
    elif pct >= 70:
        print('WARN')
    else:
        print('OK — non-budget kill')
except Exception as e:
    print(f'check failed: {e}')
" >> "$LOG_FILE" 2>&1
    fi
else
    # Clean exit — clear any stale flag
    rm -f "$FLAG_FILE"
    log "Clean exit — no exhaustion detected"
fi

log "Hook complete"
exit 0
