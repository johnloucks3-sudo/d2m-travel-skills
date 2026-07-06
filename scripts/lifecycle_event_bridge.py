#!/usr/bin/env python3
"""
Lifecycle Event Bridge — OpenCode <-> Hale Comms

Runs a lifecycle scan (core.opencode.lifecycle_event_handler.run_scan) over a
set of client records and, for every phase_changed/phase_assigned event that
fires, notifies Hale via the shared hale_bus:

  - write_bus_state(instance_type="opencode", alerts=[...])  so any Hale
    instance's session-start bus read picks up the phase transitions
  - append_channel_activity(channel="console", event_type="phase_changed")
    so it also surfaces in the cross-channel activity feed

This is an internal notify only — no client-facing or external send. Task
queueing into the oc production lane already happened inside
lifecycle_event_handler (per-touchpoint brain_bridge tasks); this script's
job is purely to make sure Hale sees that the transition happened and why.

Usage:
    python3 scripts/lifecycle_event_bridge.py --clients path/to/clients.json
    python3 scripts/lifecycle_event_bridge.py --clients path/to/clients.json --as-of 2026-08-01
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.opencode.lifecycle_event_handler import run_scan  # noqa: E402
from core.hale_bus.hale_bus_write import write_bus_state, append_channel_activity  # noqa: E402


def _load_clients(path: str) -> list[dict]:
    raw = json.loads(Path(path).read_text())
    clients = []
    for c in raw:
        clients.append({
            **c,
            "booking_date": date.fromisoformat(c["booking_date"]),
            "fpd": date.fromisoformat(c["fpd"]),
            "embark_date": date.fromisoformat(c["embark_date"]),
            "disembark_date": date.fromisoformat(c["disembark_date"]),
            "payment_date": date.fromisoformat(c["payment_date"]) if c.get("payment_date") else None,
        })
    return clients


def notify_hale(events: list[dict]) -> None:
    """Push phase-transition events onto the shared bus for Hale to pick up."""
    if not events:
        return

    alerts = [
        {
            "type": event["event_type"],
            "booking_id": event["booking_id"],
            "client_label": event["client_label"],
            "old_phase": event["old_phase"],
            "new_phase": event["new_phase"],
            "new_phase_name": event["new_phase_name"],
            "active_touchpoint_count": len(event["active_touchpoints"]),
            "ts": event["ts"],
        }
        for event in events
    ]

    write_bus_state(
        instance_type="opencode",
        open_missions=[],
        active_projects=[e["booking_id"] for e in events],
        alerts=alerts,
    )

    for event in events:
        append_channel_activity(
            channel="console",
            event_type="phase_changed",
            detail=(
                f"{event['client_label']}: {event['old_phase']} -> {event['new_phase']} "
                f"({event['new_phase_name']}), {len(event['active_touchpoints'])} touchpoint(s) queued"
            ),
            ref=event["booking_id"],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenCode lifecycle event bridge")
    parser.add_argument("--clients", required=True, help="Path to a JSON list of client anchor records")
    parser.add_argument("--as-of", default=None, help="Reference date (YYYY-MM-DD), default: today")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    clients = _load_clients(args.clients)

    events = run_scan(clients, as_of=as_of)
    notify_hale(events)

    print(json.dumps({"events_fired": len(events), "events": events}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
