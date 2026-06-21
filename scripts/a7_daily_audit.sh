#!/usr/bin/env bash
# A7 Daily Audit — fires 06:30 MT via a7-daily-audit.timer
# Writes OpsCenter/a7_metrics_dashboard.json
# Flags RED items to Hale before 07:00 brief
set -euo pipefail

THUNDERBIRD="/home/john/Thunderbird"
LOG="$THUNDERBIRD/logs/a7_daily_audit_$(date +%Y%m%d).log"

mkdir -p "$THUNDERBIRD/logs"
exec > >(tee -a "$LOG") 2>&1

echo "[$(date -Iseconds)] A7 Daily Audit starting"
cd "$THUNDERBIRD"

# Duplicate script scan
echo "[$(date -Iseconds)] Scanning for duplicate versioned scripts..."
python3 -c "
import json, re
from pathlib import Path
from collections import defaultdict
root = Path('$THUNDERBIRD')
dirs = defaultdict(list)
for f in root.rglob('*_v[0-9]*.py'):
    dirs[str(f.parent)].append(f.name)
issues = {d: files for d, files in dirs.items() if len(files) >= 3}
if issues:
    print('RED: Duplicate scripts detected:')
    for d, files in issues.items():
        print(f'  {d}: {files}')
else:
    print('GREEN: No duplicate script sprawl')
"

# Booking Master dedup scan — SUNDAY ONLY (weekly Baldrige sweep)
# Read-only: detects + flags duplicate confirmation groups. Never deletes —
# deletions remain Commander-gated (tiered dry-run + approval).
if [ "$(date +%u)" = "7" ]; then
    echo "[$(date -Iseconds)] [SUNDAY] Booking Master dedup scan..."
    set +e
    DEDUP_OUT=$(python3 core/finance/harlan_booking_master.py --dedup 2>&1)
    DEDUP_RC=$?
    set -e
    echo "$DEDUP_OUT"
    if [ "$DEDUP_RC" = "2" ]; then
        echo "RED: Booking Master duplicates reappeared — flag to Hale before 07:00 brief"
        STAMP=$(date '+%Y-%m-%d %H:%M MT')
        printf '\n## [A7 STERLING — SUNDAY AUDIT] Booking Master duplicates — %s\nDedup scan exit 2. Review: python3 core/finance/harlan_booking_master.py --dedup\nDeletions are Commander-gated (Tier A/B/C). Do not auto-delete.\n' "$STAMP" >> "$THUNDERBIRD/claude_inbox.md" 2>/dev/null \
            && echo "Flagged to claude_inbox.md" || echo "INFO: inbox flag skipped"
    elif [ "$DEDUP_RC" = "0" ]; then
        echo "GREEN: Booking Master clean (0 duplicate groups)"
    else
        echo "INFO: dedup scan could not complete (rc=$DEDUP_RC) — Sheets auth?"
    fi

    # SELF-DISABLE-001 policy block event audit — Sunday sweep picks up enforcement failures
    echo "[$(date -Iseconds)] [SUNDAY] SELF-DISABLE-001 policy block audit..."
    set +e
    python3 core/policy/self_disable_audit_extractor.py > "$THUNDERBIRD/logs/a7_self_disable_audit_$(date +%Y%m%d).log" 2>&1
    AUDIT_RC=$?
    set -e
    if [ "$AUDIT_RC" = "0" ]; then
        # Check if there are any block events in the audit file
        BLOCK_COUNT=$(wc -l < "$THUNDERBIRD/logs/policy_audit_self_disable_001.jsonl" 2>/dev/null || echo "0")
        if [ "$BLOCK_COUNT" -gt "0" ]; then
            echo "🔴 RED: $BLOCK_COUNT SELF-DISABLE-001 block events detected — enforcement failures being logged"
            STAMP=$(date '+%Y-%m-%d %H:%M MT')
            printf '\n## [A7 STERLING — SUNDAY AUDIT] SELF-DISABLE-001 Block Events — %s\n%d enforcement block events detected in policy_audit.jsonl\nFile: logs/policy_audit_self_disable_001.jsonl\nAction: Review for patterns of unauthorized access attempts.\n' "$STAMP" "$BLOCK_COUNT" >> "$THUNDERBIRD/claude_inbox.md" 2>/dev/null \
                && echo "Flagged to claude_inbox.md" || echo "INFO: inbox flag skipped"
        else
            echo "GREEN: No SELF-DISABLE-001 block events"
        fi
    else
        echo "INFO: SELF-DISABLE-001 audit could not complete (rc=$AUDIT_RC)"
    fi
else
    echo "[$(date -Iseconds)] Booking Master dedup scan skipped (Sunday-only)"
    echo "[$(date -Iseconds)] SELF-DISABLE-001 audit skipped (Sunday-only)"
fi

# SLA violations scan
echo "[$(date -Iseconds)] Checking SLA violations..."
if [ -f "$THUNDERBIRD/logs/task_sla_violations.log" ]; then
    VIOLATIONS=$(wc -l < "$THUNDERBIRD/logs/task_sla_violations.log")
    echo "SLA violations (24h log lines): $VIOLATIONS"
else
    echo "INFO: No SLA violations log found"
fi

# Update dashboard timestamp
python3 -c "
import json, datetime
from pathlib import Path
dash = Path('$THUNDERBIRD/OpsCenter/a7_metrics_dashboard.json')
if dash.exists():
    data = json.loads(dash.read_text())
    data['generated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dash.write_text(json.dumps(data, indent=2))
    print('Dashboard timestamp updated')
"

echo "[$(date -Iseconds)] A7 Daily Audit complete. See $LOG"
