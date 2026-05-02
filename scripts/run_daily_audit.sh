#!/bin/bash
# Thunderbird OS — Daily Health Audit
# Runs at 06:00 MT (after morning brief)
# Output: /home/john/Thunderbird/output/audit_daily_YYYYMMDD.txt
# Ref: docs/SYSTEM_AUDIT_CHECKLIST.md Section H

AUDIT_DATE=$(date +%Y%m%d)
AUDIT_TIME=$(date +"%Y-%m-%d %H:%M %Z")
OUTPUT_FILE="/home/john/Thunderbird/output/audit_daily_${AUDIT_DATE}.txt"
PASS=0
WARN=0
FAIL=0

log() { echo "$1" | tee -a "$OUTPUT_FILE"; }
pass() { log "  ✅ $1"; ((PASS++)); }
warn() { log "  🟡 $1"; ((WARN++)); }
fail() { log "  🔴 $1"; ((FAIL++)); }

log "=== THUNDERBIRD DAILY HEALTH AUDIT — ${AUDIT_TIME} ==="
log ""

# ─── SECTION 1: USER SERVICES ───────────────────────────────────────────────
log "--- USER SERVICES ---"
for svc in d2m-tasking-watcher.service thunderbird-mcp.service; do
    if systemctl --user is-active --quiet "$svc" 2>/dev/null; then
        pass "$svc RUNNING"
    else
        fail "$svc NOT RUNNING"
    fi
done

for tmr in claude-token-monitor.timer claude-oauth-keepalive.timer thunderbird-watchdog.timer thunderbird-autosave.timer; do
    if systemctl --user is-active --quiet "$tmr" 2>/dev/null; then
        pass "$tmr active"
    else
        warn "$tmr inactive"
    fi
done
log ""

# ─── SECTION 2: SYSTEM SERVICES ─────────────────────────────────────────────
log "--- SYSTEM SERVICES ---"
for svc in thunderbird-gdrive-sync.timer thunderbird-evernote-backup.timer; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        pass "$svc active"
    else
        warn "$svc inactive (may be user-level or not installed)"
    fi
done
log ""

# ─── SECTION 3: OAUTH FRESHNESS ──────────────────────────────────────────────
log "--- OAUTH & CREDENTIALS ---"
python3 - <<'PYEOF' 2>&1 | tee -a "$OUTPUT_FILE"
import json, sys
from pathlib import Path
from datetime import datetime

creds_path = Path.home() / ".claude" / ".credentials.json"
if not creds_path.exists():
    print("  🔴 ~/.claude/.credentials.json MISSING")
    sys.exit(1)

try:
    creds = json.loads(creds_path.read_text())
    exp_ms = creds.get("claudeAiOauth", {}).get("expiresAt", 0)
    if exp_ms:
        remaining = datetime.fromtimestamp(exp_ms / 1000) - datetime.now()
        hours = remaining.total_seconds() / 3600
        if hours > 2:
            print(f"  ✅ Claude OAuth: {hours:.1f}h remaining")
        elif hours > 0:
            print(f"  🟡 Claude OAuth: only {hours:.1f}h remaining — refresh soon")
        else:
            print(f"  🔴 Claude OAuth: EXPIRED — re-auth required")
    else:
        print("  🟡 Claude OAuth: expiresAt field missing")
except Exception as e:
    print(f"  🔴 Claude OAuth check failed: {e}")
PYEOF
log ""

# ─── SECTION 4: MCP SERVER ───────────────────────────────────────────────────
log "--- MCP SERVER ---"
MCP_COUNT=$(pgrep -f "travel_mcp_server" | wc -l)
if [ "$MCP_COUNT" -eq 1 ]; then
    pass "MCP server: 1 instance running"
elif [ "$MCP_COUNT" -gt 1 ]; then
    warn "MCP server: $MCP_COUNT instances running (expected 1) — duplicate leak"
    pgrep -a -f "travel_mcp_server" | sed 's/^/    /' | tee -a "$OUTPUT_FILE"
else
    fail "MCP server: NOT RUNNING"
fi
log ""

# ─── SECTION 5: OPEN TASKS ───────────────────────────────────────────────────
log "--- OPEN TASKS (hale_state.json) ---"
python3 - <<'PYEOF' 2>&1 | tee -a "$OUTPUT_FILE"
import json
try:
    state = json.load(open("/home/john/Thunderbird/hale_state.json"))
    tasks = state.get("open_tasks", [])
    active = [t for t in tasks if t.get("status") not in ["COMPLETED", "RESOLVED"]]
    overdue = [t for t in active if t.get("status") == "OVERDUE"]
    awaiting = [t for t in active if "AWAITING" in t.get("status", "")]
    print(f"  {'✅' if len(active) == 0 else '🟡'} {len(active)} open tasks total")
    if overdue:
        print(f"  🔴 {len(overdue)} OVERDUE:")
        for t in overdue:
            print(f"     - [{t['id']}] {t['description'][:80]}")
    if awaiting:
        print(f"  🟡 {len(awaiting)} awaiting Commander:")
        for t in awaiting:
            print(f"     - [{t['id']}] {t['description'][:80]}")
except Exception as e:
    print(f"  🔴 Could not read hale_state.json: {e}")
PYEOF
log ""

# ─── SECTION 6: DOSSIERS ─────────────────────────────────────────────────────
log "--- DOSSIERS ---"
DOSSIER_COUNT=$(find /home/john/Thunderbird/dossiers/ -name "*.md" 2>/dev/null | wc -l)
pass "$DOSSIER_COUNT dossier files found"
log ""

# ─── SECTION 7: GIT STATUS ───────────────────────────────────────────────────
log "--- GIT STATUS ---"
UNCOMMITTED=$(cd /home/john/Thunderbird && git status --short 2>/dev/null | wc -l)
if [ "$UNCOMMITTED" -eq 0 ]; then
    pass "Working tree clean"
elif [ "$UNCOMMITTED" -lt 20 ]; then
    warn "$UNCOMMITTED uncommitted changes"
elif [ "$UNCOMMITTED" -lt 100 ]; then
    warn "$UNCOMMITTED uncommitted changes — commit soon"
else
    fail "$UNCOMMITTED uncommitted changes — ACTION REQUIRED"
fi
log ""

# ─── SECTION 8: RCLONE LAST SYNC ─────────────────────────────────────────────
log "--- RCLONE LAST SYNC ---"
LAST_SYNC=$(journalctl -u thunderbird-gdrive-sync.service --since "25 hours ago" 2>/dev/null | grep -i "exit\|error\|finished" | tail -3)
if [ -n "$LAST_SYNC" ]; then
    echo "$LAST_SYNC" | grep -qi "exit code 0\|finished" && pass "rclone last sync: OK" || warn "rclone last sync may have issues — check journal"
else
    warn "rclone: no journal entries in past 25h (sync may not have run yet today)"
fi
log ""

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
log "=== SUMMARY ==="
log "  ✅ PASS:  $PASS"
log "  🟡 WARN:  $WARN"
log "  🔴 FAIL:  $FAIL"
log ""
if [ "$FAIL" -gt 0 ]; then
    log "ACTION REQUIRED — $FAIL critical issue(s). COS to flag for Commander."
elif [ "$WARN" -gt 0 ]; then
    log "REVIEW RECOMMENDED — $WARN warning(s). COS review at morning brief."
else
    log "ALL CLEAR — System healthy."
fi
log ""
log "Full report: $OUTPUT_FILE"
log "Audit ref: docs/SYSTEM_AUDIT_CHECKLIST.md"
