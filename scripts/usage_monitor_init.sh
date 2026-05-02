#!/bin/bash
# Claude Usage Monitor — Shell Integration Script
# Add to ~/.bashrc to enable monitoring functions and aliases
# Source this file or add contents directly to ~/.bashrc

THUNDERBIRD_DIR="${HOME}/Thunderbird"
MONITOR_PY="${THUNDERBIRD_DIR}/core/ops/thunderbird_usage_monitor.py"

# ── Ensure daemon is running (systemd may have restarted) ──────────────────

_ensure_usage_monitor() {
    local status
    status=$(systemctl is-active claude-usage-monitor.service 2>/dev/null || echo "inactive")
    if [[ "$status" != "active" ]]; then
        echo "[usage-monitor] ⚠️  Daemon inactive, starting..."
        systemctl start claude-usage-monitor.service 2>/dev/null || true
    fi
}

# Initialize on shell start (background)
_ensure_usage_monitor &

# ── Aliases for quick access ──────────────────────────────────────────────

alias usage='python3 '"${MONITOR_PY}"''
alias usage-alert='python3 '"${MONITOR_PY}"' --alert'
alias usage-json='python3 '"${MONITOR_PY}"' --json'
alias usage-weekly='python3 '"${MONITOR_PY}"' --weekly'

# Watch mode (live monitoring, 30-second refresh)
alias usage-watch='watch -n 30 "python3 '"${MONITOR_PY}"'"'

# ── Quick status function ─────────────────────────────────────────────────

usage-status() {
    local json
    json=$(python3 "${MONITOR_PY}" --json 2>/dev/null)

    if [[ -z "$json" ]]; then
        echo "[usage-monitor] ⚠️  Failed to fetch status"
        return 1
    fi

    local session_level weekly_level session_pct weekly_pct
    session_level=$(echo "$json" | jq -r '.session.level // "unknown"' 2>/dev/null)
    weekly_level=$(echo "$json" | jq -r '.weekly.level // "unknown"' 2>/dev/null)
    session_pct=$(echo "$json" | jq -r '.session.proj_pct // 0' 2>/dev/null)
    weekly_pct=$(echo "$json" | jq -r '.weekly.all_pct // 0' 2>/dev/null)

    echo "🔋 CLAUDE USAGE STATUS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "Session: %-6s (%3.0f%%)\n" "$session_level" "$session_pct"
    printf "Weekly:  %-6s (%3.0f%%)\n" "$weekly_level" "$weekly_pct"

    # Alert recommendation
    if [[ "$session_level" != "ok" ]] || [[ "$weekly_level" != "ok" ]]; then
        echo ""
        echo "⚠️  Threshold reached. Run 'usage-alert' to send notification."
    fi
}

# ── Full monitor check (human-readable output) ─────────────────────────────

usage-check() {
    echo "Polling ccusage..."
    python3 "${MONITOR_PY}"
}

# ── Extended info (all data in JSON) ───────────────────────────────────────

usage-full() {
    python3 "${MONITOR_PY}" --json | jq '.' 2>/dev/null || python3 "${MONITOR_PY}" --json
}

# ── Daemon management ─────────────────────────────────────────────────────

usage-daemon-status() {
    systemctl status claude-usage-monitor.service --no-pager
}

usage-daemon-logs() {
    journalctl -u claude-usage-monitor.service -n 50 -f
}

usage-daemon-restart() {
    echo "Restarting usage monitor daemon..."
    systemctl restart claude-usage-monitor.service
    echo "✅ Daemon restarted"
}

# ── REST API (if available) ──────────────────────────────────────────────

usage-api-status() {
    curl -s http://localhost:5771/api/usage/status | jq '.' 2>/dev/null || \
        echo "API not available (is thunderbird_usage_api.py running?)"
}

# ── Help ──────────────────────────────────────────────────────────────────

usage-help() {
    cat << 'HELP_EOF'
CLAUDE USAGE MONITOR — Available Commands
═══════════════════════════════════════════

Quick Commands:
  usage              Show usage status (human-readable)
  usage-status       Quick summary (ok/warn/crit/stop)
  usage-alert        Send Telegram alert (if threshold hit)
  usage-json         Full JSON output
  usage-watch        Live monitor (30-sec refresh)

Advanced:
  usage-check        Detailed breakdown
  usage-full         All data in JSON
  usage-weekly       Weekly budget only
  usage-daemon-status    Check daemon health
  usage-daemon-logs      View daemon logs (live)
  usage-daemon-restart   Restart daemon

API (localhost:5771):
  usage-api-status   Fetch status via REST API

Examples:
  $ usage-status
  🔋 CLAUDE USAGE STATUS
  Session: ok    ( 40%)
  Weekly:  ok    ( 32%)

  $ usage-watch
  # Live dashboard that refreshes every 30 seconds

  $ usage-json | jq '.session.remaining_minutes'
  # Extract specific fields with jq

HELP_EOF
}

# Export functions
export -f _ensure_usage_monitor
export -f usage-status
export -f usage-check
export -f usage-full
export -f usage-daemon-status
export -f usage-daemon-logs
export -f usage-daemon-restart
export -f usage-api-status
export -f usage-help

# Show help hint on first load (optional — comment out if too noisy)
# echo "[usage-monitor] Run 'usage-help' for available commands"
