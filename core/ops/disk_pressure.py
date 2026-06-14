#!/usr/bin/env python3
"""
thunderbird-disk-pressure — Alert if any partition exceeds 85% usage.

Schedule: Every 15 minutes via systemd timer
Output:   OpsCenter/logs/disk_pressure.log
          hale_decisions.md on alerts
          Blackboard alert on critical (>95%)
"""

import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LOG_PATH = ROOT / "OpsCenter/logs/disk_pressure.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/disk_pressure.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"
BLACKBOARD = ROOT / "OpsCenter/collaboration/blackboard.md"
ALERT_STATE = ROOT / "OpsCenter/data/disk_pressure_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DISK-PRESSURE] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

WARN_PCT = 85.0
CRITICAL_PCT = 95.0

WATCH_PATHS = [
    Path("/home/john"),
    Path("/tmp"),
    Path("/"),
    ROOT / "logs",
    ROOT / "output",
]


def check_disk() -> list[dict]:
    results = []
    seen_devices = set()

    for watch_path in WATCH_PATHS:
        if not watch_path.exists():
            continue
        try:
            usage = shutil.disk_usage(watch_path)
            pct = usage.used / usage.total * 100
            device_key = str(usage.total)  # Use total as rough device ID

            if device_key in seen_devices:
                continue
            seen_devices.add(device_key)

            level = "OK"
            if pct >= CRITICAL_PCT:
                level = "CRITICAL"
            elif pct >= WARN_PCT:
                level = "WARNING"

            result = {
                "path": str(watch_path),
                "used_gb": round(usage.used / 1e9, 1),
                "total_gb": round(usage.total / 1e9, 1),
                "free_gb": round(usage.free / 1e9, 1),
                "pct": round(pct, 1),
                "level": level,
            }
            results.append(result)

            if level != "OK":
                log.warning(f"{level}: {watch_path} at {pct:.1f}% ({usage.free / 1e9:.1f}GB free)")
            else:
                log.info(f"OK: {watch_path} at {pct:.1f}%")

        except Exception as e:
            log.debug(f"Could not check {watch_path}: {e}")

    return results


def load_alert_state() -> dict:
    try:
        if ALERT_STATE.exists():
            return json.loads(ALERT_STATE.read_text())
    except Exception:
        pass
    return {}


def save_alert_state(state: dict) -> None:
    ALERT_STATE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE.write_text(json.dumps(state))


def should_alert(state: dict, path: str, level: str) -> bool:
    """Rate-limit alerts: only re-alert if level increased or 4h have passed."""
    key = path
    if key not in state:
        return True
    last = state[key]
    last_level = last.get("level", "OK")
    last_ts = datetime.fromisoformat(last.get("ts", "2000-01-01T00:00:00"))
    now = datetime.now()

    if level == "CRITICAL" and last_level != "CRITICAL":
        return True
    if (now - last_ts).total_seconds() > 4 * 3600:
        return True
    return False


def write_hale_decision(alerts: list[dict], run_dt: datetime) -> None:
    if not alerts:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Disk pressure alert — {len(alerts)} partition(s) above threshold\n",
    ]
    for a in alerts:
        lines.append(f"  - [{a['level']}] {a['path']}: {a['pct']}% ({a['free_gb']}GB free)\n")
    lines.append("**Domain:** Infrastructure / Storage\n**Type:** proactive alert\n**Outcome:** surfaced to Commander\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def write_blackboard_alert(critical: list[dict], run_dt: datetime) -> None:
    if not critical:
        return
    alert = (
        f"\n## DISK PRESSURE CRITICAL — {run_dt.strftime('%Y-%m-%d %H:%M')} MDT\n"
        + "\n".join(f"  {a['path']}: {a['pct']}% full ({a['free_gb']}GB free)" for a in critical)
        + "\n"
    )
    try:
        with open(BLACKBOARD, "a") as f:
            f.write(alert)
    except Exception as e:
        log.warning(f"Could not write blackboard: {e}")


def main() -> int:
    run_dt = datetime.now()
    results = check_disk()
    state = load_alert_state()

    alerts = [r for r in results if r["level"] != "OK" and should_alert(state, r["path"], r["level"])]
    critical = [r for r in alerts if r["level"] == "CRITICAL"]

    for r in results:
        if r["level"] != "OK":
            state[r["path"]] = {"level": r["level"], "ts": run_dt.isoformat(), "pct": r["pct"]}
    save_alert_state(state)

    entry = {
        "ts": run_dt.isoformat(),
        "results": results,
        "alerts": len(alerts),
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if alerts:
        write_hale_decision(alerts, run_dt)
        if critical:
            write_blackboard_alert(critical, run_dt)
        log.warning(f"{len(alerts)} disk pressure alert(s)")
    else:
        log.info("All partitions healthy")

    return 0


if __name__ == "__main__":
    sys.exit(main())
