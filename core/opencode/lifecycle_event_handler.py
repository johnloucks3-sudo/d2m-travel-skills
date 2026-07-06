"""
Lifecycle Event Handler — OpenCode Lifecycle Integration

Event dispatcher that:
  1. Listens for anchor-date updates (call check_client()/run_scan() whenever
     a dossier's booking/fpd/embark/disembark dates or payment_status change
     — e.g. from a dossier-watcher poll or a direct call after a TESS sync).
  2. Computes the client's current phase via phase_determination_engine.
  3. Compares against the last-known phase persisted in
     lifecycle_phase_state.json (keyed by booking_id). If it moved
     (or this is the client's first pass), emits a phase_changed /
     phase_assigned event.
  4. Maps the new phase to its active touchpoints by reading
     config/lifecycle_touchpoints.json and selecting entries whose
     anchor-relative target date falls inside the new phase's date window
     (phase_determination_engine.phase_window()).
  5. Queues an A2-research brain_bridge task (oc lane) for each active
     touchpoint — ops/mechanical work belongs in the oc lane per standing
     doctrine, not ground out inline.

State and touchpoint config live in files so this handler has no memory of
its own between calls — every call is a fresh read-compute-compare-write.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from core.opencode.phase_determination_engine import assign_phase, phase_window

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = Path(
    os.environ.get(
        "LIFECYCLE_PHASE_STATE_PATH", str(REPO_ROOT / "core" / "opencode" / "lifecycle_phase_state.json")
    )
)
TOUCHPOINTS_CONFIG_PATH = Path(
    os.environ.get(
        "LIFECYCLE_TOUCHPOINTS_CONFIG_PATH", str(REPO_ROOT / "config" / "lifecycle_touchpoints.json")
    )
)

ANCHOR_FIELD = {"B": "booking_date", "E": "embark_date", "FPD": "fpd", "D": "disembark_date"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return default


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def load_phase_state() -> dict:
    return _load_json(STATE_PATH, {})


def save_phase_state(state: dict) -> None:
    _atomic_write_json(STATE_PATH, state)


def _touchpoints_config() -> list[dict]:
    cfg = _load_json(TOUCHPOINTS_CONFIG_PATH, {"touchpoints": []})
    return cfg.get("touchpoints", [])


def select_active_touchpoints(
    phase_code: str,
    booking_date: date,
    fpd: date,
    embark_date: date,
    disembark_date: date,
) -> list[dict]:
    """
    Select touchpoints from config/lifecycle_touchpoints.json whose
    anchor-relative target date falls inside this client's window for
    phase_code. Anchor arithmetic: target = anchor_date + anchor_offset_days.
    """
    start, end = phase_window(phase_code, booking_date, fpd, embark_date, disembark_date)
    anchors = {"B": booking_date, "E": embark_date, "FPD": fpd, "D": disembark_date}

    active = []
    for tp in _touchpoints_config():
        origin = tp.get("anchor_origin")
        offset = tp.get("anchor_offset_days")
        if origin not in anchors or offset is None:
            continue
        target = anchors[origin] + timedelta(days=offset)
        if start is not None and target < start:
            continue
        if end is not None and target >= end:
            continue
        active.append({**tp, "target_date": target.isoformat()})
    return active


def check_client(
    client: dict,
    as_of: Optional[date] = None,
    bridge: Optional[Any] = None,
    queue_tasks: bool = True,
) -> Optional[dict]:
    """
    Evaluate one client record for a phase transition. Persists the new
    phase if it changed. Returns the transition event dict, or None if the
    phase is unchanged from the stored value.

    client keys: booking_id, client_label, booking_date, fpd, embark_date,
                 disembark_date, payment_status, payment_date, cruise_line
    bridge: an object with an .add(title, description, lane, priority) method
            (core.hale_bus.brain_bridge.BrainBridge by default). Tests inject
            a fake to avoid writing to the shared production board.
    """
    booking_id = client["booking_id"]
    result = assign_phase(
        booking_date=client["booking_date"],
        fpd=client["fpd"],
        embark_date=client["embark_date"],
        disembark_date=client["disembark_date"],
        payment_status=client.get("payment_status"),
        payment_date=client.get("payment_date"),
        cruise_line=client.get("cruise_line"),
        client_label=client.get("client_label", booking_id),
        as_of=as_of,
    )
    new_phase = result["phase_code"]

    state = load_phase_state()
    old_phase = state.get(booking_id, {}).get("phase_code")

    if old_phase == new_phase:
        return None

    active_touchpoints = []
    if new_phase != "PHASE_INVALID":
        active_touchpoints = select_active_touchpoints(
            new_phase, client["booking_date"], client["fpd"], client["embark_date"], client["disembark_date"]
        )

    event = {
        "event_type": "phase_assigned" if old_phase is None else "phase_changed",
        "booking_id": booking_id,
        "client_label": client.get("client_label", booking_id),
        "old_phase": old_phase,
        "new_phase": new_phase,
        "new_phase_name": result["phase_name"],
        "payment_status": result["payment_status"],
        "anchor_validation": result["anchor_validation"],
        "active_touchpoints": active_touchpoints,
        "as_of": result["as_of"],
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    if queue_tasks and active_touchpoints:
        _queue_touchpoint_tasks(event, bridge=bridge)

    state[booking_id] = {"phase_code": new_phase, "updated_at": event["ts"]}
    save_phase_state(state)

    return event


def _queue_touchpoint_tasks(event: dict, bridge: Optional[Any] = None) -> list[str]:
    """Queue one A2-research brain_bridge task (oc lane) per active touchpoint."""
    if bridge is None:
        from core.hale_bus.brain_bridge import BrainBridge

        bridge = BrainBridge()

    task_ids = []
    for tp in event["active_touchpoints"]:
        tid = bridge.add(
            title=f"A2 research — {event['client_label']} — {tp.get('touchpoint_id', tp.get('id', '?'))}: {tp.get('description', tp.get('label', ''))}",
            description=(
                f"Phase transition {event['old_phase']} -> {event['new_phase']} ({event['new_phase_name']}) "
                f"for booking {event['booking_id']}. Touchpoint target date {tp.get('target_date')}."
            ),
            lane="oc",
            priority="P1",
        )
        task_ids.append(tid)
    return task_ids


def run_scan(
    clients: list[dict],
    as_of: Optional[date] = None,
    bridge: Optional[Any] = None,
) -> list[dict]:
    """Evaluate every client in clients, return the list of fired events (transitions only)."""
    events = []
    for client in clients:
        event = check_client(client, as_of=as_of, bridge=bridge)
        if event:
            events.append(event)
    return events
