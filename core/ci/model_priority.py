"""Model priority-of-fires — let CI remediation + Commander comms PREEMPT routine traffic.

The 10-hour incident's second harm: the Commander's Telegram command timed out because
136 routine timers were all grabbing the model — his command had no precedence. This is
the fix: a priority flag that HIGH-priority consumers (CI remediation, Commander comms)
claim, and that routine consumers honor by yielding ("knock it off" / river-city).

Pure logic (_is_active / _should_yield) is unit-tested; the file flag is the transport.

Routine model consumers add at the top of their run:
    from core.ci.model_priority import should_yield
    if should_yield("routine"): sys.exit(0)   # a priority mission holds the range — defer a cycle

High-priority consumers wrap their work:
    with priority_window("hale", "CI remediation: ttyd.service"):
        ... dispatch the fixer ...
"""
from __future__ import annotations
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PRIORITY_FLAG = Path("/home/john/Thunderbird/config/model_priority.flag")
DEFAULT_TTL_S = 180
# Precedence: higher number wins. Commander > CI remediation > routine.
PRECEDENCE = {"commander": 30, "hale": 20, "ci": 20, "routine": 0}


# ---------- pure, testable ----------

def _is_active(record: dict | None, now: datetime) -> bool:
    if not record:
        return False
    until = record.get("until")
    if not until:
        return False
    dt = datetime.fromisoformat(until)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return now < dt


def _should_yield(record: dict | None, my_class: str, now: datetime) -> bool:
    """A consumer of `my_class` yields iff an active claim outranks it."""
    if not _is_active(record, now):
        return False
    holder = (record or {}).get("owner_class", "ci")
    return PRECEDENCE.get(my_class, 0) < PRECEDENCE.get(holder, 20)


# ---------- file transport ----------

def _read() -> dict | None:
    try:
        return json.loads(PRIORITY_FLAG.read_text())
    except Exception:
        return None


def claim_priority(owner: str, reason: str, owner_class: str = "ci",
                   ttl_seconds: int = DEFAULT_TTL_S, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    until = now.timestamp() + ttl_seconds
    rec = {"owner": owner, "owner_class": owner_class, "reason": reason,
           "claimed": now.isoformat(),
           "until": datetime.fromtimestamp(until, tz=timezone.utc).isoformat()}
    try:
        PRIORITY_FLAG.parent.mkdir(parents=True, exist_ok=True)
        PRIORITY_FLAG.write_text(json.dumps(rec) + "\n")
    except Exception:
        pass


def release_priority() -> None:
    try:
        PRIORITY_FLAG.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass


def priority_active(now: datetime | None = None) -> dict | None:
    rec = _read()
    return rec if _is_active(rec, now or datetime.now(timezone.utc)) else None


def should_yield(my_class: str = "routine", now: datetime | None = None) -> bool:
    return _should_yield(_read(), my_class, now or datetime.now(timezone.utc))


def guard_routine(caller: str = "routine") -> bool:
    """Routine model consumers call this at startup. Returns True if a higher-priority
    mission holds the range (caller should defer this cycle). Usage:
        from core.ci.model_priority import guard_routine
        import sys
        if guard_routine(): sys.exit(0)
    """
    return should_yield(caller)


@contextmanager
def priority_window(owner: str, reason: str, owner_class: str = "ci", ttl_seconds: int = DEFAULT_TTL_S):
    claim_priority(owner, reason, owner_class, ttl_seconds)
    try:
        yield
    finally:
        release_priority()
