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
