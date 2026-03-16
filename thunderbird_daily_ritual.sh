#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Thunderbird Daily Ritual — Dreams2Memories Travel, LLC
# Runs: morning briefing, payment alerts, tech monitor, Claude Code digest
# Schedule: systemd timer at 0700 MT (briefing) + 1000 MT (tech/articles)
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M')
LOG_FILE="$LOG_DIR/daily_ritual_${TIMESTAMP}.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ── PHASE 1: Morning Briefing (0700) ──
run_briefing() {
    log "=== PHASE 1: MORNING BRIEFING ==="

    log "Sending morning briefing email..."
    cd "$SCRIPT_DIR"
    python3 thunderbird_morning_briefing.py 2>>"$LOG_FILE"
    log "Morning briefing: DONE"

    log "Checking payment alerts..."
    python3 thunderbird_payment_alerts.py 2>>"$LOG_FILE"
    log "Payment alerts: DONE"
}

# ── PHASE 2: Tech Monitor + Claude Code Digest (1000) ──
run_tech_digest() {
    log "=== PHASE 2: TECH MONITOR + CLAUDE CODE DIGEST ==="

    log "Running tech monitor sweep..."
    cd "$SCRIPT_DIR"
    python3 thunderbird_tech_monitor.py --run 2>>"$LOG_FILE" || log "Tech monitor: FAILED (non-fatal)"

    log "Refreshing Claude Code articles page..."
    python3 thunderbird_claude_code_digest.py 2>>"$LOG_FILE" || log "Claude Code digest: FAILED (non-fatal)"

    log "Phase 2: DONE"
}

# ── DISPATCH ──
case "${1:-all}" in
    briefing)  run_briefing ;;
    tech)      run_tech_digest ;;
    all)       run_briefing; run_tech_digest ;;
    *)         echo "Usage: $0 {briefing|tech|all}" ;;
esac

# Clean up old logs (keep 14 days)
find "$LOG_DIR" -name "daily_ritual_*.log" -mtime +14 -delete 2>/dev/null || true

log "=== DAILY RITUAL COMPLETE ==="
