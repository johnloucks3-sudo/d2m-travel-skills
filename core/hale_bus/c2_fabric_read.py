#!/usr/bin/env python3
"""
UNIFIED C2 FABRIC — Phase 1 Read Path (read-only)
Ref: docs/UNIFIED_C2_FABRIC_PROPOSAL_20260706.md

Unified visibility across the four C2 channels (console, wave, telegram,
email) so a Commander question like "what happened on Telegram while I was
in Console" can be answered from one file, one read, no channel-hopping.

Read-only: no lock taken. Reads are safe against torn writes because every
writer (hale_bus_write.py + c2_fabric_write.py) commits via os.replace()
inside the shared lock — a reader always sees a complete prior state or a
complete new state, never a partial file.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from core.hale_bus.hale_bus_write import HALE_BUS_PATH

CHANNELS = ("console", "wave", "telegram", "email")


def read_full_state() -> dict:
    """Raw bus state, empty dict if missing/corrupt."""
    try:
        return json.loads(HALE_BUS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def get_channel_activity(since: str | None = None, channel: str | None = None) -> list:
    """Flat cross-channel activity log, optionally filtered."""
    entries = read_full_state().get("channel_activity", [])
    if since:
        entries = [e for e in entries if e["ts"] > since]
    if channel:
        entries = [e for e in entries if e["channel"] == channel]
    return entries


def get_channel_rollup(channel: str) -> dict:
    """Latest-status rollup for one channel: last event, timestamp,
    confirmed-delivery tag, and running event count. This is the piece the
    flat activity log doesn't give you for free — a reader wanting 'what's
    the state of Telegram right now' would otherwise have to scan the whole
    log and find the last matching entry themselves."""
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}, got {channel!r}")
    bus_state = read_full_state()
    rollup = bus_state.get("c2_channel_state", {}).get(channel)
    if rollup:
        return {"channel": channel, **rollup}

    # Fall back to scanning channel_activity for writers that predate
    # c2_channel_state (e.g. entries from the legacy append_channel_activity
    # path before this module existed).
    matches = [e for e in bus_state.get("channel_activity", []) if e.get("channel") == channel]
    if not matches:
        return {"channel": channel, "status": "NO_ACTIVITY"}
    last = matches[-1]
    return {
        "channel": channel,
        "last_ts": last.get("ts"),
        "last_event_type": last.get("event_type"),
        "last_detail": last.get("detail"),
        "last_ref": last.get("ref"),
        "confirmed_delivered": last.get("confirmed_delivered", False),
        "event_count": len(matches),
    }


def get_unified_channel_state() -> dict:
    """Rollup for all four channels in one call — the Phase 1 'single
    visibility ledger' the proposal asks for."""
    return {ch: get_channel_rollup(ch) for ch in CHANNELS}


def get_c2_metrics() -> dict:
    """Sterling/Harlan's weekly-tracked metrics: total_writes,
    write_conflict_rate, lock_contention_events."""
    bus_state = read_full_state()
    return bus_state.get("c2_metrics", {
        "total_writes": 0,
        "write_conflict_rate": 0.0,
        "lock_contention_events": 0,
    })


def unified_visibility_brief() -> str:
    """Formatted cross-channel brief — what happened where, without the
    Commander needing to check four channels separately."""
    state = get_unified_channel_state()
    metrics = get_c2_metrics()
    now = datetime.now(timezone.utc).isoformat()

    lines = [f"⚡ C2 FABRIC — UNIFIED VISIBILITY [{now}]"]
    for channel in CHANNELS:
        rollup = state[channel]
        if rollup.get("status") == "NO_ACTIVITY":
            lines.append(f"  {channel.upper()}: no activity recorded")
            continue
        delivered = "confirmed-delivered" if rollup.get("confirmed_delivered") else "delivery unconfirmed"
        lines.append(
            f"  {channel.upper()}: [{rollup.get('last_ts')}] {rollup.get('last_event_type')} "
            f"— {rollup.get('last_detail')} ({delivered}, {rollup.get('event_count')} events)"
        )
    lines.append(
        f"\nMetrics: {metrics.get('total_writes', 0)} total writes, "
        f"write_conflict_rate={metrics.get('write_conflict_rate', 0.0)}, "
        f"lock_contention_events={metrics.get('lock_contention_events', 0)}"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    print(unified_visibility_brief())
