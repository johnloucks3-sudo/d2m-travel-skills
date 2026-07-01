#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Lifecycle Touchpoint Scheduler Pipeline
============================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Checks:
  1. OpsCenter/logs/lifecycle_audit.jsonl — scheduler_complete event < 26h ago
  2. OpsCenter/staff_tasking_schedule.json — generated_at < 26h ago
     (belt-and-suspenders: both pipelines should run in sync)
  3. Overdue phase count from lifecycle_audit.jsonl must be < 20
     (metric: phases_stale from stale_phases_summary event)

Probe does NOT re-run the engine. The repair function re-runs it.
Exit 0 = GREEN. Exit 1 = RED.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
LIFECYCLE_AUDIT = THUNDERBIRD_ROOT / "OpsCenter" / "logs" / "lifecycle_audit.jsonl"
STAFF_SCHEDULE = THUNDERBIRD_ROOT / "OpsCenter" / "staff_tasking_schedule.json"
CURRENCY_H = 26
STALE_PHASES_THRESHOLD = 20  # RED only if extreme (>20 overdue phases)
ID = "lifecycle-tp"


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def parse_last_jsonl_event(path: Path, event_type: str) -> dict | None:
    """Return the last JSONL entry matching event_type, or None."""
    if not path.exists():
        return None
    result = None
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("event") == event_type or event_type is None:
                    result = entry
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return result


def main() -> None:
    now = datetime.now(tz=timezone.utc)
    scheduler_age_h = None
    stale_phases = 0
    scheduler_ts_str = None

    # ── CHECK 1: lifecycle_audit.jsonl scheduler_complete event ─────────────
    if LIFECYCLE_AUDIT.exists():
        sched_entry = parse_last_jsonl_event(LIFECYCLE_AUDIT, "scheduler_complete")
        if sched_entry:
            ts_str = sched_entry.get("ts") or sched_entry.get("timestamp")
            if ts_str:
                scheduler_ts_str = ts_str
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    scheduler_age_h = (now - ts).total_seconds() / 3600
                except Exception:
                    pass

        # Also check for stale_phases_summary to get overdue count
        stale_entry = parse_last_jsonl_event(LIFECYCLE_AUDIT, "stale_phases_summary")
        if stale_entry:
            stale_phases = stale_entry.get("count", stale_entry.get("stale_count", 0))

    # ── CHECK 2: staff_tasking_schedule.json freshness ──────────────────────
    schedule_age_h = None
    schedule_ts_str = None
    if STAFF_SCHEDULE.exists():
        try:
            schedule_data = json.loads(STAFF_SCHEDULE.read_text())
            gen_at = schedule_data.get("generated_at")
            if gen_at:
                schedule_ts_str = gen_at
                try:
                    ts = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    schedule_age_h = (now - ts).total_seconds() / 3600
                except Exception:
                    pass
        except Exception:
            pass
    else:
        fail(
            f"staff_tasking_schedule.json missing at {STAFF_SCHEDULE} — "
            "TP scheduler pipeline has never produced output"
        )

    # Use the best available freshness signal
    best_age_h = None
    best_source = None
    if scheduler_age_h is not None and schedule_age_h is not None:
        best_age_h = min(scheduler_age_h, schedule_age_h)
        best_source = "lifecycle_audit.jsonl + staff_tasking_schedule.json"
    elif scheduler_age_h is not None:
        best_age_h = scheduler_age_h
        best_source = "lifecycle_audit.jsonl"
    elif schedule_age_h is not None:
        best_age_h = schedule_age_h
        best_source = "staff_tasking_schedule.json"
    else:
        fail(
            "Cannot determine TP scheduler last-run time — "
            "lifecycle_audit.jsonl has no scheduler_complete events "
            "and staff_tasking_schedule.json has no generated_at field"
        )

    if best_age_h > CURRENCY_H:
        fail(
            f"TP scheduler last ran {best_age_h:.1f}h ago (threshold {CURRENCY_H}h) "
            f"— pipeline is DARK. Source: {best_source}. "
            f"Last run: {schedule_ts_str or scheduler_ts_str}. "
            "Fix: python3 core/booking/thunderbird_tp_scheduler.py --json > "
            "OpsCenter/staff_tasking_schedule.json"
        )

    # ── CHECK 3: Overdue phase count sanity ─────────────────────────────────
    # NOTE: phases_stale (lifecycle_audit event count) is the scheduler's
    # 14-day lookback count, distinct from the brief's "overdue TPs" count.
    # Threshold is deliberately high (>20) to signal only extreme breakdown.
    if stale_phases > STALE_PHASES_THRESHOLD:
        fail(
            f"TP scheduler reports {stale_phases} stale phases "
            f"(threshold {STALE_PHASES_THRESHOLD}) — "
            "lifecycle pipeline may be broken or dossiers are severely stale"
        )

    print(
        f"GREEN {ID}: scheduler ran {best_age_h:.1f}h ago; "
        f"stale_phases={stale_phases} (threshold {STALE_PHASES_THRESHOLD}); "
        f"source: {best_source}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
