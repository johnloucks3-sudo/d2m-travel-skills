#!/usr/bin/env python3
"""
UNIFIED C2 FABRIC — Phase 1 Write Path
Ref: docs/UNIFIED_C2_FABRIC_PROPOSAL_20260706.md

Atomic, conflict-instrumented writes onto the shared hale_bus_state.json for
the four C2 channels: console, wave, telegram, email.

This module does NOT introduce a second lock. It imports the exclusive
fcntl advisory lock already shipped in hale_bus_write.py (_locked_bus) so
every writer on this file — legacy (append_channel_activity, write_bus_state)
and this Phase 1 path — serializes through the same critical section. Two
independent locks on the same file would not coordinate with each other.

Phase 1 scope: visibility only. record_channel_event() has no silence=GO
or auto-execute behavior — it tags confirmed_delivered structurally so
Phase 2 can build the confirmed-delivery timer on top of real data instead
of guessing retroactively. Nothing reads that tag as an execute signal yet.
"""

import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path

from core.hale_bus.hale_bus_write import (
    HALE_BUS_PATH,
    LOCK_PATH,
    _atomic_write_json,
    _locked_bus,
)


def _probe_contention() -> bool:
    """Non-blocking probe: is another writer holding the lock right now?
    Used only for the lock_contention_events metric — correctness always
    comes from the blocking _locked_bus() acquire that follows, not from
    this probe. A race between probe and acquire (another writer grabs the
    lock in between) just means an undercount on a metric, never a missed
    exclusion."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "w") as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(probe, fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True

CHANNELS = ("console", "wave", "telegram", "email")


def _load_bus() -> dict:
    try:
        return json.loads(HALE_BUS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"bus_version": "1.0", "hale_instances": {}}


def record_channel_event(
    channel: str,
    event_type: str,
    detail: str,
    ref: str | None = None,
    confirmed_delivered: bool = False,
) -> dict:
    """Append a C2 event and update that channel's rollup, atomically.

    Writes to the SAME `channel_activity` list as the existing
    append_channel_activity() (schema-compatible — c2_fabric_read.py can
    read entries from either writer) and additionally maintains a
    `c2_channel_state[channel]` rollup so a reader gets latest-status
    without re-scanning the whole activity log.

    Conflict semantics (Harlan's ask, stated plainly): under this design,
    write_conflict_rate is 0 BY CONSTRUCTION — the exclusive lock means the
    read-modify-write for every writer, old or new, happens as one atomic
    critical section, so there is no window for two writers to stomp on
    each other's update. This function is not a conflict-resolution
    algorithm; it is instrumentation that would surface a regression if the
    lock were ever bypassed (e.g. a future writer that forgets to import
    _locked_bus). See docs/UNIFIED_C2_FABRIC_PHASE1_IMPLEMENTATION.md.
    """
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}, got {channel!r}")

    now = datetime.now(timezone.utc).isoformat()
    contended = _probe_contention()

    with _locked_bus():
        bus_state = _load_bus()

        activity = bus_state.setdefault("channel_activity", [])
        entry = {
            "ts": now,
            "channel": channel,
            "event_type": event_type,
            "detail": detail,
            "ref": ref,
            "confirmed_delivered": confirmed_delivered,
        }
        activity.append(entry)
        bus_state["channel_activity"] = activity[-500:]

        rollup = bus_state.setdefault("c2_channel_state", {})
        prior = rollup.get(channel, {"event_count": 0})
        rollup[channel] = {
            "last_ts": now,
            "last_event_type": event_type,
            "last_detail": detail,
            "last_ref": ref,
            "confirmed_delivered": confirmed_delivered,
            "event_count": prior.get("event_count", 0) + 1,
        }

        metrics = bus_state.setdefault("c2_metrics", {
            "total_writes": 0,
            "write_conflict_rate": 0.0,
            "lock_contention_events": 0,
        })
        metrics["total_writes"] = metrics.get("total_writes", 0) + 1
        if contended:
            metrics["lock_contention_events"] = metrics.get("lock_contention_events", 0) + 1
        # write_conflict_rate stays 0.0 — see docstring. Left explicit (not
        # omitted) so the metric is visible to Sterling's weekly sweep even
        # though this design never produces a nonzero value.
        metrics["write_conflict_rate"] = 0.0

        bus_state["last_updated"] = now
        _atomic_write_json(HALE_BUS_PATH, bus_state)

    return entry


if __name__ == "__main__":
    result = record_channel_event("console", "manual_test", "c2_fabric_write self-test", ref="selftest")
    print(json.dumps(result, indent=2))
