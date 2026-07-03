#!/usr/bin/env python3
"""
update_usage.py — Write a manual usage snapshot to the ledger.

Usage:
    python3 scripts/update_usage.py <weekly_all_pct> <sonnet_pct> <runs_used> <runs_total>
    python3 scripts/update_usage.py 28 34 9 15
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TB = Path("/home/john/Thunderbird")
LEDGER = TB / "OpsCenter" / "usage_ledger.json"
RATE_MD = TB / "OpsCenter" / "collaboration" / "rate_limit_status.md"

def load():
    try:
        return json.loads(LEDGER.read_text())
    except Exception:
        return {"routine_runs": [], "manual_snapshots": [], "reset_day": "Thursday", "reset_time_mt": "21:00"}

def save(data):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(data, indent=2))

def update_rate_md(wkly, sonnet, runs_used, runs_total):
    from datetime import timedelta
    mt = datetime.now(timezone(timedelta(hours=-6)))
    content = f"""# CLAUDE USAGE STATUS — UPDATED FROM MAX PLAN SCREEN
Updated: {mt.strftime('%Y-%m-%d %H:%M MT')}

## Status
### Weekly (all models): {wkly}% used
### Weekly (Sonnet only): {sonnet}% used
### Daily Routine Runs: {runs_used}/{runs_total} used

Claude Sonnet: MAX Wkly-{wkly}% | Sonnet-{sonnet}% | Runs-{runs_used}/{runs_total}
Groq: UNKNOWN
Deepseek: UNKNOWN
OpenCode: GREEN
"""
    RATE_MD.write_text(content)

def main():
    if len(sys.argv) < 5:
        print("Usage: update_usage.py <weekly_all_pct> <sonnet_pct> <runs_used> <runs_total>")
        sys.exit(1)

    wkly       = int(sys.argv[1])
    sonnet     = int(sys.argv[2])
    runs_used  = int(sys.argv[3])
    runs_total = int(sys.argv[4])

    data = load()
    ts = datetime.now(timezone.utc).isoformat()
    data["manual_snapshots"].append({
        "ts": ts,
        "weekly_all_pct": wkly,
        "weekly_sonnet_pct": sonnet,
        "runs_used": runs_used,
        "runs_total": runs_total,
        "source": "manual_paste",
    })
    # Keep last 20 snapshots
    data["manual_snapshots"] = data["manual_snapshots"][-20:]
    save(data)

    update_rate_md(wkly, sonnet, runs_used, runs_total)

    # Re-run blackboard sync
    import subprocess
    subprocess.run(
        ["python3", str(TB / "OpsCenter" / "blackboard_sync.py")],
        cwd=str(TB), capture_output=True
    )

    # Check overflow threshold
    import importlib.util, os
    watcher = TB / "scripts" / "cc_overflow_watcher.py"
    spec = importlib.util.spec_from_file_location("cc_overflow_watcher", watcher)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.check(verbose=True)

    print(f"✅ Ledger updated: Wkly {wkly}% | Sonnet {sonnet}% | Runs {runs_used}/{runs_total}")
    print(f"   Snapshot ts: {ts[:16]}")
    print(f"   Chyron synced.")

if __name__ == "__main__":
    main()
