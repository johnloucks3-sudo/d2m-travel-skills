#!/usr/bin/env python3
"""
ci_probe_lifecycle-excursion-engine.py — CI probe for the excursion engine.
Exit 0 = GREEN, 1 = RED.
Final output line: GREEN/RED lifecycle-excursion-engine: <detail>
"""
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

STATE_FILE = Path("/home/john/Thunderbird/OpsCenter/state/excursion_engine_state.json")


def fail(m: str):
    print(f"RED lifecycle-excursion-engine: {m}")
    sys.exit(1)


def main() -> None:
    # 1. State file must exist
    if not STATE_FILE.exists():
        fail("state file missing — engine never ran")

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"state file unreadable: {exc}")

    # 2. Check last_run freshness (25-hour threshold)
    last_run_raw = state.get("last_run")
    if not last_run_raw:
        fail("state file has no last_run timestamp")

    try:
        last_run = datetime.fromisoformat(last_run_raw.replace("Z", "+00:00"))
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        age_hours = (now - last_run).total_seconds() / 3600.0
    except Exception as exc:
        fail(f"cannot parse last_run '{last_run_raw}': {exc}")

    if age_hours > 25:
        fail(f"stale: last run {age_hours:.1f}h ago")

    # 3. Load dossiers and find in-window bookings (1–180 days)
    try:
        from core.booking.thunderbird_tp_scheduler import scan_dossiers
    except ImportError as exc:
        fail(f"cannot import scan_dossiers: {exc}")

    today = date.today()
    try:
        records = scan_dossiers()
    except Exception as exc:
        fail(f"scan_dossiers() raised: {exc}")

    in_window = [
        r for r in records
        if r.status == "active"
        and r.departure is not None
        and 1 <= (r.departure - today).days <= 180
    ]

    entries: dict = state.get("entries", {})

    missing = [r for r in in_window if str(r.path) not in entries]

    # 4. Coverage gap check
    if missing:
        names = ", ".join(r.client for r in missing)
        fail(f"{len(missing)} in-window booking(s) without excursion research: {names}")

    # 5. GREEN
    evaluated = state.get("evaluated", "?")
    triggered = state.get("triggered", "?")
    age_min = int(age_hours * 60)
    print(f"GREEN lifecycle-excursion-engine: ran {age_min}m ago; evaluated {evaluated}, triggered {triggered}")
    sys.exit(0)


if __name__ == "__main__":
    main()
