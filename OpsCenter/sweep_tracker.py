"""
sweep_tracker.py — Sweep Idempotency Guard
==========================================
Prevents double-execution of scheduled jobs across restarts and reboots.
Services check before running; mark complete after. Survives reboots via JSON.

Usage:
    from OpsCenter.sweep_tracker import SweepTracker

    tracker = SweepTracker("morning_briefing")
    if tracker.already_ran_today():
        print("Already sent today — skipping")
        sys.exit(0)
    # ... do the work ...
    tracker.mark_complete(status="sent", note="All 8 sources OK")

    # Or for fixed-interval jobs (not daily):
    tracker = SweepTracker("email_sweep", cooldown_minutes=60)
    if tracker.in_cooldown():
        sys.exit(0)
    tracker.mark_complete()
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKER_FILE = ROOT / "logs" / "sweep_tracker.json"
MT_OFFSET = timedelta(hours=-6)   # MDT; adjust to -7 for MST


def _now_mt() -> datetime:
    return datetime.now(timezone(MT_OFFSET))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _load() -> dict:
    try:
        if TRACKER_FILE.exists():
            return json.loads(TRACKER_FILE.read_text())
    except Exception:
        pass
    return {}


def _save(data: dict) -> None:
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(data, indent=2))


class SweepTracker:
    """
    Tracks last-run state for a named sweep/job.

    Args:
        name:              Unique job identifier (e.g. "morning_briefing")
        cooldown_minutes:  If set, uses cooldown-based dedup instead of daily.
                           Use for jobs that run multiple times per day.
        daily_reset_hour:  MT hour at which "today" resets (default: midnight = 0).
                           Set to 1 to match 01:30 MDT morning brief window.
    """

    def __init__(
        self,
        name: str,
        cooldown_minutes: int | None = None,
        daily_reset_hour: int = 0,
    ):
        self.name = name
        self.cooldown_minutes = cooldown_minutes
        self.daily_reset_hour = daily_reset_hour

    def _get_record(self) -> dict:
        return _load().get(self.name, {})

    def already_ran_today(self) -> bool:
        """
        True if this job has already completed successfully today (MT).
        'Today' is the MT calendar day, resetting at daily_reset_hour MT.
        """
        rec = self._get_record()
        last_run = rec.get("last_success_utc")
        if not last_run:
            return False
        try:
            last_dt_utc = datetime.fromisoformat(last_run)
            last_dt_mt  = last_dt_utc.astimezone(timezone(MT_OFFSET))
            now_mt      = _now_mt()
            # Determine the reset boundary for today
            reset_today = now_mt.replace(
                hour=self.daily_reset_hour, minute=0, second=0, microsecond=0
            )
            return last_dt_mt >= reset_today
        except (ValueError, TypeError):
            return False

    def in_cooldown(self) -> bool:
        """
        True if the job ran within the cooldown window.
        Only meaningful when cooldown_minutes is set.
        """
        if self.cooldown_minutes is None:
            return self.already_ran_today()
        rec = self._get_record()
        last_run = rec.get("last_success_utc")
        if not last_run:
            return False
        try:
            last_dt = datetime.fromisoformat(last_run)
            cooldown = timedelta(minutes=self.cooldown_minutes)
            return (_now_utc() - last_dt) < cooldown
        except (ValueError, TypeError):
            return False

    def mark_complete(self, status: str = "ok", note: str = "") -> None:
        """Record a successful completion."""
        data = _load()
        data[self.name] = {
            "last_success_utc": _now_utc().isoformat(),
            "last_success_mt":  _now_mt().strftime("%Y-%m-%d %H:%M MT"),
            "status": status,
            "note": note,
            "run_count": data.get(self.name, {}).get("run_count", 0) + 1,
        }
        _save(data)

    def mark_failed(self, error: str = "") -> None:
        """Record a failed run (does NOT update last_success, so dedup will not block retry)."""
        data = _load()
        rec = data.get(self.name, {})
        rec["last_failure_utc"] = _now_utc().isoformat()
        rec["last_failure_mt"]  = _now_mt().strftime("%Y-%m-%d %H:%M MT")
        rec["last_error"] = error[:200]
        rec["fail_count"] = rec.get("fail_count", 0) + 1
        data[self.name] = rec
        _save(data)

    def status(self) -> dict:
        """Return full status record for this job."""
        return self._get_record()

    def reset(self) -> None:
        """Force a reset so the job will run again on next trigger."""
        data = _load()
        data.pop(self.name, None)
        _save(data)


def get_all_statuses() -> dict:
    """Return all tracked job statuses."""
    return _load()


if __name__ == "__main__":
    # Self-test
    t = SweepTracker("_test_job_")
    assert not t.already_ran_today(), "Should not have run yet"
    t.mark_complete(note="test run")
    assert t.already_ran_today(), "Should be marked complete"
    t.reset()
    assert not t.already_ran_today(), "Should be reset"
    print("SweepTracker self-test PASSED")

    # Show all current statuses
    import json as _json
    statuses = get_all_statuses()
    print(f"\nCurrent tracked jobs ({len(statuses)}):")
    for name, rec in statuses.items():
        print(f"  {name:30s} last={rec.get('last_success_mt', 'never'):20s} runs={rec.get('run_count', 0)}")
