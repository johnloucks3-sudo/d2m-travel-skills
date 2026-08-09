#!/usr/bin/env python3
"""reconcile_kzn_board.py — W7 dual-ledger reconcile (RT-EFFICACY).

KAIZEN async tickets (OpsCenter/tickets/*.json) are the live authority for
Commander-ticket work; the mission board barely sees them. This one-way
mirror makes the board a faithful read of the ticket ledger:

  - every open/done ticket file becomes/refreshes a mission row whose id is
    the ticket's kzn- id (findable in both stores by the same key);
  - ticket status maps to mission status (open->active, done/closed->done);
  - idempotent: re-running updates, never duplicates (board's add_mission
    dedupes on title anyway; we also match on the kzn- id first);
  - uses mission_board_sync.add_mission API — never writes mission_board.json
    directly (Wing doctrine: mission board via sync script only).

Report mode (--dry-run) prints what would change without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TICKETS = ROOT / "OpsCenter" / "tickets"
STATUS_MAP = {"open": "active", "assigned": "active", "in_progress": "active",
              "pending_review": "active", "done": "done", "closed": "done"}


def load_tickets() -> list[dict]:
    out = []
    for p in sorted(TICKETS.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def ticket_title(t: dict) -> str:
    spec = (t.get("spec") or t.get("title") or "").strip().replace("\n", " ")
    return (spec[:90] + "…") if len(spec) > 90 else (spec or t.get("ticket_id", "ticket"))


def reconcile(*, dry_run: bool = False) -> dict:
    sys.path.insert(0, str(ROOT / "OpsCenter"))
    from mission_board_sync import load_board, add_mission, save_board, acquire_lock, release_lock

    tickets = load_tickets()
    board = load_board()
    missions = board.get("missions", board) if isinstance(board, dict) else board
    by_source = {str(m.get("source", "")): m for m in missions}

    made = updated = skipped = 0
    changes = []
    fd = acquire_lock()
    try:
        for t in tickets:
            tid = t.get("ticket_id")
            if not tid:
                continue
            status = STATUS_MAP.get(str(t.get("status", "open")).lower(), "active")
            desc = f"KAIZEN ticket {tid} | seat={t.get('seat','')} | {t.get('verify_step','')}"
            title = f"[KAIZEN] {ticket_title(t)}"
            existing = by_source.get(f"kaizen:{tid}")
            if existing:
                if existing.get("status") == status:
                    skipped += 1
                    continue
                existing["status"] = status
                updated += 1
                changes.append(f"update {tid} ({existing['id']}): -> {status}")
                continue
            msg, mid = add_mission(board, title, description=desc, priority="P2",
                                   assigned_to="unassigned",
                                   acceptance_criteria=str(t.get("verify_step") or ""),
                                   source=f"kaizen:{tid}")
            if mid is None:
                # add_mission blocked it as an entity/title duplicate — another
                # existing row holds this ticket; don't churn on re-runs.
                skipped += 1
                changes.append(f"dup-blocked {tid}: {str(msg)[:60]}")
                continue
            made += 1
            changes.append(f"add {mid} {tid} ({title[:40]})")
    finally:
        if not dry_run:
            save_board(board, fd)   # save_board() releases the lock itself
        else:
            release_lock(fd)        # nothing written — release only

    return {"tickets": len(tickets), "made": made, "updated": updated,
            "skipped": skipped, "changes": changes}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    r = reconcile(dry_run=dry)
    print(f"{'DRY-RUN ' if dry else ''}tickets={r['tickets']} added={r['made']} "
          f"updated={r['updated']} unchanged={r['skipped']}")
    for c in r["changes"][:20]:
        print("  ", c)
