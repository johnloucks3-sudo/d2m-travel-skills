#!/usr/bin/env python3
"""
HALE BUS WRITE HANDLER — Session End Checkpoint

Writes current Hale instance state to the inter-Hale communication bus.
Called at session end to persist state for other instances to read.

Mandatory integration: append to every session's stop hook.
"""

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# HALE_BUS_STATE_PATH override exists so concurrency tests can point at a
# scratch file instead of the production bus (core/hale_bus/test_c2_fabric_concurrency.py).
HALE_BUS_PATH = Path(os.environ.get(
    "HALE_BUS_STATE_PATH",
    str(Path.home() / "Thunderbird" / "core" / "hale_bus" / "hale_bus_state.json"),
))
LOCK_PATH = HALE_BUS_PATH.with_suffix(".lock")


@contextmanager
def _locked_bus():
    """Advisory file lock — Unified C2 Fabric Phase 1 (2026-07-06). Prevents
    concurrent writers (Console/Wave/Telegram/Email all now write this file)
    from corrupting each other's updates. Read-modify-write happens inside
    the lock so no writer can act on stale state.

    core/hale_bus/c2_fabric_write.py imports this SAME contextmanager rather
    than opening its own lock — two independent locks on one file would not
    coordinate with each other and mutual exclusion would be lost."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)


def _atomic_write_json(path: Path, data: dict):
    """Write JSON via temp-file + os.replace so a reader never observes a
    half-written file. Must be called from inside _locked_bus() — the lock
    serializes writers, this makes each individual write crash-safe."""
    tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
    tmp_path.write_text(json.dumps(data, indent=2))
    os.replace(tmp_path, path)
INSTANCE_MAPPING = {
    "CLAUDE_CODE": "claude_code",
    "OPENCODE": "opencode",
    "DEEPSEEK_TELEGRAM": "deepseek_telegram",
    "COPILOT_CLI": "copilot_cli",
    "CODEX": "codex",
    "GEMINI_CLI": "gemini_cli",
    "BROWSER": "browser",
    "HEADLESS_SPAWN": "headless_spawn",
}


def get_instance_type():
    """Detect which Hale instance is running this code."""
    # Environment variables or runtime context hints
    if os.getenv("CLAUDE_CODE_SESSION"):
        return INSTANCE_MAPPING["CLAUDE_CODE"]
    if os.getenv("OPENCODE_SESSION"):
        return INSTANCE_MAPPING["OPENCODE"]
    if os.getenv("DEEPSEEK_SESSION"):
        return INSTANCE_MAPPING["DEEPSEEK_TELEGRAM"]
    # Default fallback
    return INSTANCE_MAPPING["CLAUDE_CODE"]


def read_hale_state():
    """Read current hale_state.json to extract mission and project state."""
    state_path = Path.home() / "Thunderbird" / "hale_state.json"
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def write_bus_state(instance_type, open_missions, active_projects, alerts=None):
    """
    Write this instance's state to the inter-Hale bus.

    Args:
        instance_type: One of the INSTANCE_MAPPING values
        open_missions: List of mission IDs currently active
        active_projects: List of project IDs currently active
        alerts: Optional list of alert dictionaries
    """
    alerts = alerts or []
    now = datetime.now(timezone.utc).isoformat()

    with _locked_bus():
        # Read current bus state
        try:
            bus_state = json.loads(HALE_BUS_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            # Initialize fresh if file missing or corrupt
            bus_state = {
                "bus_version": "1.0",
                "hale_instances": {k: {"status": "OFFLINE"} for k in INSTANCE_MAPPING.values()},
            }

        # Update this instance's entry
        bus_state["last_updated"] = now
        bus_state["source_instance"] = instance_type

        if "hale_instances" not in bus_state:
            bus_state["hale_instances"] = {}

        bus_state["hale_instances"][instance_type] = {
            "status": "ONLINE",
            "last_seen": now,
            "open_missions": open_missions,
            "active_projects": active_projects,
            "pending_decisions": [],
            "alerts": alerts,
        }

        # Write back
        HALE_BUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(HALE_BUS_PATH, bus_state)
        return bus_state


CHANNELS = ("console", "wave", "telegram", "email")


def append_channel_activity(channel: str, event_type: str, detail: str, ref: str | None = None):
    """Unified C2 Fabric Phase 1 — append a cross-channel activity entry so any
    channel (Console/Wave/Telegram/Email) can see what happened on the others
    without the Commander repeating context. Locked read-modify-write."""
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}, got {channel!r}")
    now = datetime.now(timezone.utc).isoformat()
    with _locked_bus():
        try:
            bus_state = json.loads(HALE_BUS_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            bus_state = {"bus_version": "1.0", "hale_instances": {}}
        activity = bus_state.setdefault("channel_activity", [])
        activity.append({
            "ts": now, "channel": channel, "event_type": event_type,
            "detail": detail, "ref": ref,
        })
        # keep the log bounded — this is a visibility feed, not an audit archive
        bus_state["channel_activity"] = activity[-500:]
        _atomic_write_json(HALE_BUS_PATH, bus_state)
    return bus_state["channel_activity"][-1]


def read_channel_activity(since: str | None = None, channel: str | None = None) -> list:
    """Read cross-channel activity, optionally filtered by ISO timestamp or channel."""
    try:
        bus_state = json.loads(HALE_BUS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    entries = bus_state.get("channel_activity", [])
    if since:
        entries = [e for e in entries if e["ts"] > since]
    if channel:
        entries = [e for e in entries if e["channel"] == channel]
    return entries


def checkpoint_session(instance_type=None):
    """
    Main checkpoint function. Call at session end.

    Usage:
        from core.hale_bus.hale_bus_write import checkpoint_session
        checkpoint_session()
    """
    if not instance_type:
        instance_type = get_instance_type()

    # Read current operational state
    hale_state = read_hale_state()

    # Extract open missions and active projects
    open_missions = [m["id"] for m in hale_state.get("open_tasks", []) if m.get("status") in ("active", "in_progress")]
    active_projects = [p["id"] for p in hale_state.get("project_tracking", {}).get("active_projects", [])]

    # Write checkpoint
    bus_state = write_bus_state(instance_type, open_missions, active_projects)

    print(f"✅ HALE BUS CHECKPOINT: {instance_type}")
    print(f"   Wrote: {len(open_missions)} missions, {len(active_projects)} projects")
    print(f"   Bus: {HALE_BUS_PATH}")

    return bus_state


if __name__ == "__main__":
    checkpoint_session()
