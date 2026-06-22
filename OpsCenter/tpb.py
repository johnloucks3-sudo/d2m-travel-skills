#!/usr/bin/env python3
"""
Target Prosecution Board (TPB)
What the Wing is spending tokens on RIGHT NOW.
Not a todo list. Not a nag list. Current targets in prosecution.

Usage:
  python3 OpsCenter/tpb.py                     # show board (default)
  python3 OpsCenter/tpb.py status              # same
  python3 OpsCenter/tpb.py add "Target name"  # add as ENGAGED (or QUEUED if at cap)
  python3 OpsCenter/tpb.py queue "Target name"# add as QUEUED
  python3 OpsCenter/tpb.py complete T-01      # mark complete
  python3 OpsCenter/tpb.py park T-01          # pause target
  python3 OpsCenter/tpb.py engage T-01        # activate queued/parked target
  python3 OpsCenter/tpb.py reset-today        # clear done_today log
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent / "tpb_state.json"

# Status constants
ENGAGED = "ENGAGED"
QUEUED = "QUEUED"
PARKED = "PARKED"
COMPLETE = "COMPLETE"

# Status icons
ICONS = {
    ENGAGED: "🔴",
    QUEUED:  "🟡",
    PARKED:  "⏸",
}


def load_state() -> dict:
    if not STATE_FILE.exists():
        state = {
            "last_id": 0,
            "wip_cap": 5,
            "targets": [],
            "done_today": [],
            "last_updated": _now_iso()
        }
        save_state(state)
        return state
    with STATE_FILE.open() as f:
        return json.load(f)


def save_state(state: dict) -> None:
    state["last_updated"] = _now_iso()
    with STATE_FILE.open("w") as f:
        json.dump(state, f, indent=2)


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _now_mt_display() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M") + " MT"


def _next_id(state: dict) -> str:
    state["last_id"] += 1
    return f"T-{state['last_id']:02d}"


def _engaged_count(state: dict) -> int:
    return sum(1 for t in state["targets"] if t["status"] == ENGAGED)


def _format_elapsed(opened_at_iso: str) -> str:
    try:
        opened = datetime.fromisoformat(opened_at_iso)
        now = datetime.now()
        total_secs = int((now - opened).total_seconds())
        if total_secs < 0:
            total_secs = 0
        hours = total_secs // 3600
        minutes = (total_secs % 3600) // 60
        return f"+{hours}h{minutes:02d}m"
    except Exception:
        return "+?h??m"


def _find_target(state: dict, target_id: str) -> dict | None:
    tid = target_id.upper()
    for t in state["targets"]:
        if t["id"].upper() == tid:
            return t
    return None


def cmd_status(state: dict) -> None:
    engaged = _engaged_count(state)
    cap = state["wip_cap"]
    now_str = _now_mt_display()

    header = f"═══ TARGETS IN PROSECUTION {'═' * 28} {now_str} ═"
    print(header)
    print(f"  WIP: {engaged}/{cap}")
    print()

    engaged_targets = [t for t in state["targets"] if t["status"] == ENGAGED]
    queued_targets  = [t for t in state["targets"] if t["status"] == QUEUED]
    parked_targets  = [t for t in state["targets"] if t["status"] == PARKED]

    active_list = engaged_targets + queued_targets + parked_targets

    if not active_list:
        print("  (no active targets)")
    else:
        for t in active_list:
            icon = ICONS.get(t["status"], "  ")
            tid = t["id"]
            name = t["name"]
            status = t["status"]
            if t["status"] == ENGAGED:
                elapsed = _format_elapsed(t["opened_at"])
                line = f"  {icon} {tid:<6}  {name:<42} {status:<8} {elapsed}"
            else:
                line = f"  {icon} {tid:<6}  {name:<42} {status}"
            print(line)

    if state.get("done_today"):
        print()
        done_str = " · ".join(state["done_today"])
        # Wrap if too long
        print(f"  Done today: {done_str}")

    footer = "═" * len(header)
    print(footer)


def cmd_add(state: dict, name: str) -> None:
    if not name.strip():
        print("Error: target name cannot be empty.", file=sys.stderr)
        sys.exit(1)

    engaged = _engaged_count(state)
    cap = state["wip_cap"]

    tid = _next_id(state)
    status = ENGAGED if engaged < cap else QUEUED

    target = {
        "id": tid,
        "name": name.strip(),
        "status": status,
        "opened_at": _now_iso(),
        "completed_at": None,
        "notes": ""
    }
    state["targets"].append(target)
    save_state(state)

    if status == QUEUED:
        print(f"⚠  WIP cap reached ({cap}/{cap}). Added as QUEUED. Complete or park a target first.")
        print(f"   {tid}  {name}")
    else:
        print(f"✅ {tid} ENGAGED: {name}")


def cmd_queue(state: dict, name: str) -> None:
    if not name.strip():
        print("Error: target name cannot be empty.", file=sys.stderr)
        sys.exit(1)

    tid = _next_id(state)
    target = {
        "id": tid,
        "name": name.strip(),
        "status": QUEUED,
        "opened_at": _now_iso(),
        "completed_at": None,
        "notes": ""
    }
    state["targets"].append(target)
    save_state(state)
    print(f"🟡 {tid} QUEUED: {name}")


def cmd_complete(state: dict, target_id: str) -> None:
    t = _find_target(state, target_id)
    if t is None:
        print(f"Error: target {target_id} not found.", file=sys.stderr)
        sys.exit(1)

    name = t["name"]
    state["targets"].remove(t)
    state["done_today"].append(name)
    save_state(state)
    print(f"✅ {target_id} COMPLETE: {name}")


def cmd_park(state: dict, target_id: str) -> None:
    t = _find_target(state, target_id)
    if t is None:
        print(f"Error: target {target_id} not found.", file=sys.stderr)
        sys.exit(1)

    if t["status"] == PARKED:
        print(f"  {target_id} is already PARKED.")
        return

    t["status"] = PARKED
    save_state(state)
    print(f"⏸  {target_id} PARKED: {t['name']}")


def cmd_engage(state: dict, target_id: str) -> None:
    t = _find_target(state, target_id)
    if t is None:
        print(f"Error: target {target_id} not found.", file=sys.stderr)
        sys.exit(1)

    if t["status"] == ENGAGED:
        print(f"  {target_id} is already ENGAGED.")
        return

    engaged = _engaged_count(state)
    cap = state["wip_cap"]
    if engaged >= cap:
        print(f"⚠  WIP cap reached ({cap}/{cap}). Complete or park a target before engaging {target_id}.",
              file=sys.stderr)
        sys.exit(1)

    t["status"] = ENGAGED
    # Reset opened_at to now when re-engaging (so time-in-flight is meaningful)
    t["opened_at"] = _now_iso()
    save_state(state)
    print(f"🔴 {target_id} ENGAGED: {t['name']}")


def cmd_reset_today(state: dict) -> None:
    count = len(state["done_today"])
    state["done_today"] = []
    save_state(state)
    print(f"Done today log cleared ({count} entries removed).")


def main() -> None:
    args = sys.argv[1:]
    state = load_state()

    if not args or args[0] in ("status", "show"):
        cmd_status(state)
        return

    cmd = args[0].lower()
    rest = " ".join(args[1:]).strip()

    if cmd == "add":
        cmd_add(state, rest)
        print()
        cmd_status(state)

    elif cmd == "queue":
        cmd_queue(state, rest)
        print()
        cmd_status(state)

    elif cmd == "complete":
        if not rest:
            print("Error: provide a target ID, e.g. complete T-01", file=sys.stderr)
            sys.exit(1)
        cmd_complete(state, rest.split()[0])
        print()
        cmd_status(state)

    elif cmd == "park":
        if not rest:
            print("Error: provide a target ID, e.g. park T-01", file=sys.stderr)
            sys.exit(1)
        cmd_park(state, rest.split()[0])
        print()
        cmd_status(state)

    elif cmd == "engage":
        if not rest:
            print("Error: provide a target ID, e.g. engage T-01", file=sys.stderr)
            sys.exit(1)
        cmd_engage(state, rest.split()[0])
        print()
        cmd_status(state)

    elif cmd == "reset-today":
        cmd_reset_today(state)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
