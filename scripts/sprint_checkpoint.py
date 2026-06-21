#!/usr/bin/env python3
"""
M-300 — Sprint Checkpoint Writer (Otsukare pattern).

Writes a 6-item state snapshot before context limits are hit, enabling
clean session resume. Run manually or auto-triggered at context threshold.

Schema (6 items):
  1. sprint_phase       — current phase name + number
  2. completed_missions — list of mission IDs marked done this sprint
  3. in_progress        — list of {id, title, next_action} items
  4. pending_queue      — ordered list of IDs to execute next
  5. blockers           — list of {id, blocker, owner} items
  6. last_action        — one-line description of the last completed action

Usage:
  python3 scripts/sprint_checkpoint.py [--phase "Phase 2"] [--last-action "Fixed M-290"]
  python3 scripts/sprint_checkpoint.py --read
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_PATH = ROOT / "OpsCenter" / "sprint_checkpoint.json"
MISSION_BOARD = ROOT / "OpsCenter" / "mission_board.json"


def load_mission_board():
    if not MISSION_BOARD.exists():
        return []
    data = json.loads(MISSION_BOARD.read_text())
    return data.get("missions", [])


def build_checkpoint(phase: str = "", last_action: str = "") -> dict:
    """Snapshot current sprint state from mission board + args."""
    missions = load_mission_board()

    completed = [m["id"] for m in missions if m.get("status") in ("complete", "done")]
    in_progress = [
        {"id": m["id"], "title": m.get("title", ""), "next_action": m.get("description", "")[:120]}
        for m in missions
        if m.get("status") == "in_progress"
    ]
    pending = [m["id"] for m in missions if m.get("status") == "active" and m.get("priority") in ("P0", "P1")]
    blockers = [
        {"id": m["id"], "blocker": m.get("blocker", "unknown"), "owner": m.get("owner", "Hale")}
        for m in missions
        if m.get("status") == "blocked"
    ]

    existing = {}
    if CHECKPOINT_PATH.exists():
        try:
            existing = json.loads(CHECKPOINT_PATH.read_text())
        except Exception:
            pass

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sprint_phase": phase or existing.get("sprint_phase", "Unknown"),
        "completed_missions": completed,
        "in_progress": in_progress,
        "pending_queue": pending,
        "blockers": blockers,
        "last_action": last_action or existing.get("last_action", ""),
    }


def write_checkpoint(cp: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(cp, indent=2))
    print(f"✅ Checkpoint written → {CHECKPOINT_PATH}")
    print(f"   Phase:      {cp['sprint_phase']}")
    print(f"   Completed:  {len(cp['completed_missions'])} missions")
    print(f"   In-progress:{len(cp['in_progress'])} missions")
    print(f"   Pending:    {len(cp['pending_queue'])} missions")
    print(f"   Blockers:   {len(cp['blockers'])}")
    print(f"   Last action:{cp['last_action']}")


def read_checkpoint() -> None:
    if not CHECKPOINT_PATH.exists():
        print("No checkpoint found.")
        return
    cp = json.loads(CHECKPOINT_PATH.read_text())
    ts = cp.get("ts", "unknown")
    print(f"⚡ SPRINT CHECKPOINT — {ts}")
    print(f"   Phase:       {cp.get('sprint_phase', '?')}")
    print(f"   Last action: {cp.get('last_action', '?')}")
    print(f"   Completed ({len(cp.get('completed_missions', []))}): {', '.join(cp.get('completed_missions', [])[:10])}")
    print(f"   In-progress ({len(cp.get('in_progress', []))}):")
    for item in cp.get("in_progress", [])[:5]:
        print(f"     {item['id']} — {item['title'][:60]}")
    print(f"   Pending queue: {', '.join(cp.get('pending_queue', [])[:10])}")
    if cp.get("blockers"):
        print(f"   Blockers:")
        for b in cp["blockers"]:
            print(f"     {b['id']}: {b['blocker']} (owner: {b['owner']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sprint Checkpoint Writer (M-300 / Otsukare pattern)")
    parser.add_argument("--phase", default="", help="Current sprint phase name")
    parser.add_argument("--last-action", default="", dest="last_action", help="One-line description of last completed action")
    parser.add_argument("--read", action="store_true", help="Read and display the current checkpoint")
    args = parser.parse_args()

    if args.read:
        read_checkpoint()
        sys.exit(0)

    cp = build_checkpoint(phase=args.phase, last_action=args.last_action)
    write_checkpoint(cp)
