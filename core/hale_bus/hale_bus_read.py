#!/usr/bin/env python3
"""
HALE BUS READ HANDLER — Session Startup Mandatory Load

Reads inter-Hale communication bus at session startup.
Every Hale instance MUST call this before operating.

Critical path: load in session_init.py before any other operations.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

HALE_BUS_PATH = Path.home() / "Thunderbird" / "core" / "hale_bus" / "hale_bus_state.json"


def read_bus_state():
    """
    Read the inter-Hale communication bus.

    Returns:
        dict: Current bus state or empty dict if unavailable
    """
    if not HALE_BUS_PATH.exists():
        return {}

    try:
        return json.loads(HALE_BUS_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ HALE BUS READ ERROR: {e}")
        return {}


def get_other_instances_state(exclude_instance=None):
    """
    Get state from all other active Hale instances.

    Args:
        exclude_instance: Instance type to exclude (e.g., "claude_code")

    Returns:
        dict: Map of instance -> state
    """
    bus_state = read_bus_state()
    instances = bus_state.get("hale_instances", {})

    if exclude_instance:
        instances = {k: v for k, v in instances.items() if k != exclude_instance}

    return instances


def get_critical_directives():
    """Get critical directives that other instances left for this Hale."""
    bus_state = read_bus_state()
    return bus_state.get("critical_state", {}).get("commander_directives", [])


def get_fpd_alerts():
    """Get FPD (Final Payment Due) alerts shared across instances."""
    bus_state = read_bus_state()
    return bus_state.get("critical_state", {}).get("fpd_alerts", [])


def get_handoff_queue():
    """Get work items queued for this instance by other instances."""
    bus_state = read_bus_state()
    return bus_state.get("critical_state", {}).get("handoff_queue", [])


def startup_brief(instance_type):
    """
    Generate a startup brief from the inter-Hale bus.
    Called at session open to brief the new instance on system state.

    Args:
        instance_type: The instance coming online (e.g., "claude_code")

    Returns:
        str: Formatted brief
    """
    bus_state = read_bus_state()

    if not bus_state:
        return "🟢 HALE BUS: No prior state. Starting fresh.\n"

    brief = []
    brief.append(f"⚡ INTER-HALE STATE LOAD [{instance_type}]")
    brief.append(f"Last update: {bus_state.get('last_updated', 'unknown')}")
    brief.append(f"Source: {bus_state.get('source_instance', 'unknown')}\n")

    # Active instances
    instances = get_other_instances_state(exclude_instance=instance_type)
    active = {k: v for k, v in instances.items() if v.get("status") == "ONLINE"}
    if active:
        brief.append("🟢 OTHER ACTIVE INSTANCES:")
        for inst, state in active.items():
            brief.append(f"  {inst}: {len(state.get('open_missions', []))} missions, {len(state.get('active_projects', []))} projects")

    # Critical directives
    directives = get_critical_directives()
    if directives:
        brief.append("\n🔴 CRITICAL DIRECTIVES:")
        for d in directives:
            brief.append(f"  {d.get('id')}: {d.get('scope')} [{d.get('status')}]")

    # FPD alerts
    fpds = get_fpd_alerts()
    if fpds:
        brief.append("\n⚠️  FPD ALERTS:")
        for fpd in fpds:
            brief.append(f"  {fpd.get('client')}: {fpd.get('fpd')} ({fpd.get('days_remaining')}d)")

    # Handoff queue
    handoffs = get_handoff_queue()
    if handoffs:
        brief.append("\n📋 HANDOFF QUEUE:")
        for h in handoffs:
            brief.append(f"  {h.get('from_instance')} → {h.get('to_instance')}: {h.get('task')}")

    return "\n".join(brief)


def load_bus_at_startup(instance_type):
    """
    Mandatory call at session startup.
    Loads inter-Hale state and prints brief.

    Args:
        instance_type: Type of instance starting (e.g., "claude_code")
    """
    brief = startup_brief(instance_type)
    if brief:
        print(brief)

    # Load specific state items
    bus_state = read_bus_state()
    if bus_state:
        return {
            "other_instances": get_other_instances_state(exclude_instance=instance_type),
            "critical_directives": get_critical_directives(),
            "fpd_alerts": get_fpd_alerts(),
            "handoff_queue": get_handoff_queue(),
        }
    return {}


if __name__ == "__main__":
    # Test load
    state = load_bus_at_startup("claude_code")
    print(f"\n✅ Loaded: {len(state)} state categories")
