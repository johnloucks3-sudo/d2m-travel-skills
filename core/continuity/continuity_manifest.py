#!/usr/bin/env python3
"""
CONTINUITY MANIFEST
Real-time view of offline mission queue and execution status.

Updated by: continuity_executor.py (on each spawn)
Consumed by: hale_brief.md (injected into morning brief)
"""

import json
from pathlib import Path
from datetime import datetime

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
CONTINUITY_DIR = THUNDERBIRD_ROOT / "core" / "continuity"
HALE_STATE = THUNDERBIRD_ROOT / "hale_state.json"
MANIFEST_FILE = CONTINUITY_DIR / "manifest.json"
CONTINUITY_LOG = CONTINUITY_DIR / "continuity_log.jsonl"


def build_manifest():
    """Generate current continuity status"""
    # Load deferred alerts
    try:
        with open(HALE_STATE) as f:
            state = json.load(f)
        alerts = state.get("deferred_alerts", [])
    except Exception:
        alerts = []

    # Load execution log
    log_entries = []
    if CONTINUITY_LOG.exists():
        with open(CONTINUITY_LOG) as f:
            for line in f:
                try:
                    log_entries.append(json.loads(line))
                except:
                    pass

    # Get latest status from log
    last_status = "IDLE"
    last_timestamp = None
    if log_entries:
        last = log_entries[-1]
        last_status = last.get("status", "UNKNOWN")
        last_timestamp = last.get("timestamp")

    # Count queued missions
    queued = []
    for alert in alerts:
        alert_id = alert.get("id")
        trigger_date = alert.get("trigger_date")
        priority = alert.get("priority", "P2")

        # Check if already executed
        result_file = CONTINUITY_DIR / "results" / f"{alert_id}_result.json"
        if result_file.exists():
            continue  # Skip completed

        # Check if triggered but not yet spawned
        if trigger_date <= datetime.now().isoformat():
            queued.append({
                "id": alert_id,
                "priority": priority,
                "message": alert.get("message", "")[:60],
                "trigger_date": trigger_date,
            })

    # Count executing
    executing = []
    for spawn_log in CONTINUITY_DIR.glob("spawn_*.log"):
        # Simple heuristic: if log exists and is recent, assume executing
        executing.append(spawn_log.stem.replace("spawn_", ""))

    # Build manifest
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "status": last_status,
        "last_log": last_timestamp,
        "queued_missions": len(queued),
        "executing_missions": len(executing),
        "queued": queued,
        "executing": executing,
        "network_status": "UNKNOWN",  # Would be detected by main watchdog
    }

    return manifest


def write_manifest(manifest):
    """Persist manifest to file"""
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    manifest = build_manifest()
    write_manifest(manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
