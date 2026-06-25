#!/usr/bin/env python3
"""
HALE BUS WRITE HANDLER — Session End Checkpoint

Writes current Hale instance state to the inter-Hale communication bus.
Called at session end to persist state for other instances to read.

Mandatory integration: append to every session's stop hook.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

HALE_BUS_PATH = Path.home() / "Thunderbird" / "core" / "hale_bus" / "hale_bus_state.json"
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
    HALE_BUS_PATH.write_text(json.dumps(bus_state, indent=2))
    return bus_state


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
