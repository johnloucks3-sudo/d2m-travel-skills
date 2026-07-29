"""
core/comms/commander_queue.py — the Commander's desk, and the ledger that makes his
closures permanent.

C2 RECALIBRATION task 10, Commander directive 2026-07-29:
    "I have tried to reduce my queue and it keeps getting overridden."

WHY IT KEPT COMING BACK
-----------------------
scripts/commander_decision_inbox_update.py — on an hourly systemd timer since it was
written — was a 51-line stub. Lines 34-39 were an unimplemented TODO:

    # In production, this would:
    # 1. Compare pending items against last update
    # 3. Identify completed items to archive     <-- never written

Nothing ever archived anything. Meanwhile every generator (mission board sync, brief
engines, alert scanners) re-derived the Commander's queue from source state on each
run. A closure was a local edit with no record, so the next regeneration resurrected
it. He was not imagining the override; it was the designed behaviour.

THE FIX
-------
One append-only ledger, consulted by everything:

    OpsCenter/state/commander_closures.jsonl   append-only, never rewritten
    OpsCenter/state/commander_queue.json       derived view, safe to regenerate

A closed id can never re-enter the queue, by any path, ever. `is_closed()` is the
single predicate every generator must call before putting an item on his desk. The
ledger is append-only on purpose: an audit trail you can silently rewrite is not one.

This makes the whole CLASS of resurrection bug structurally impossible, rather than
patching it per-symptom the way commit 0f4ce31a3 had to.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parents[2]

CLOSURES_PATH = ROOT / "OpsCenter" / "state" / "commander_closures.jsonl"
QUEUE_PATH = ROOT / "OpsCenter" / "state" / "commander_queue.json"
BOARD_PATH = ROOT / "OpsCenter" / "mission_board.json"
STATE_PATH = ROOT / "hale_state.json"

# Board statuses that mean the item is sitting on the Commander's desk.
AWAITING_COMMANDER = {"pending_review", "in_coordination"}
# Statuses that mean it is already resolved and must never be re-surfaced.
TERMINAL = {"completed", "cancelled", "closed", "rolled_up"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # one corrupt line must not un-close everything
    return rows


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────────────────────────
# The closure ledger — the whole point of this module
# ─────────────────────────────────────────────────────────────────────────────────

def close(item_id: str, *, by: str = "Commander", reason: str = "",
          source: str = "") -> dict:
    """Close an item permanently. Idempotent; re-closing is a no-op that still records.

    `by` defaults to Commander because that is the authority this ledger exists to
    protect. A seat closing on his behalf should say so explicitly.
    """
    item_id = str(item_id).strip()
    if not item_id:
        raise ValueError("close() requires a non-empty item_id")
    row = {"ts": _now(), "item_id": item_id, "by": by,
           "reason": reason, "source": source}
    _append_jsonl(CLOSURES_PATH, row)
    return row


def reopen(item_id: str, *, by: str = "Commander", reason: str = "") -> dict:
    """Reverse a closure by APPENDING a reversal, never by editing history.

    A closure ledger you can rewrite is not an audit trail, so an erroneous close is
    corrected the way a ledger corrects anything: with a counter-entry that is itself
    on the record. Needed because closes are permanent by design, and a mistaken one
    would otherwise be unfixable — including my own on 2026-07-29, when a regression
    test was run against live data and closed a real mission.
    """
    item_id = str(item_id).strip()
    if not item_id:
        raise ValueError("reopen() requires a non-empty item_id")
    row = {"ts": _now(), "item_id": item_id, "by": by,
           "reason": reason, "action": "reopen"}
    _append_jsonl(CLOSURES_PATH, row)
    return row


def closed_ids() -> set[str]:
    """Every id currently closed — replaying the ledger in order so that a later
    reopen wins over an earlier close, and a later close wins over a reopen."""
    state: dict[str, bool] = {}
    for r in _read_jsonl(CLOSURES_PATH):
        iid = r.get("item_id")
        if not iid:
            continue
        state[str(iid)] = (r.get("action") != "reopen")
    return {k for k, closed in state.items() if closed}


def is_closed(item_id: str) -> bool:
    """THE predicate. Every generator must call this before adding to his desk."""
    return str(item_id) in closed_ids()


def closure_count() -> int:
    return len(closed_ids())


# ─────────────────────────────────────────────────────────────────────────────────
# Derived queue
# ─────────────────────────────────────────────────────────────────────────────────

def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def build_queue() -> dict:
    """Recompute the Commander's desk from source, minus everything he has closed.

    Safe to run on a timer: it is derived, so regenerating cannot resurrect a closure
    the way the old stub's absence did.
    """
    closed = closed_ids()
    board = _load(BOARD_PATH, {})
    missions = board.get("missions", []) if isinstance(board, dict) else []

    items: list[dict] = []
    suppressed = 0

    for m in missions:
        mid = str(m.get("id", "")).strip()
        if not mid:
            continue
        status = (m.get("status") or "").lower()
        if status in TERMINAL:
            continue
        if status not in AWAITING_COMMANDER:
            continue
        if mid in closed:
            suppressed += 1
            continue
        items.append({
            "id": mid,
            "kind": "mission",
            "title": str(m.get("title", ""))[:160],
            "priority": m.get("priority", "P2"),
            "status": status,
            "assigned_to": m.get("assigned_to", ""),
            "suspense_date": m.get("suspense_date", ""),
            "created_at": m.get("created_at", ""),
        })

    state = _load(STATE_PATH, {})
    for a in (state.get("deferred_alerts") or []):
        aid = str(a.get("id", "")).strip()
        if not aid:
            continue
        if aid in closed:
            suppressed += 1
            continue
        items.append({
            "id": aid,
            "kind": "alert",
            "title": str(a.get("message", ""))[:160],
            "priority": a.get("priority", "P2"),
            "status": "deferred",
            "client": a.get("client", ""),
            "amount": a.get("amount", ""),
            "fpd": a.get("fpd", ""),
            "suspense_date": a.get("trigger_date", ""),
        })

    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    items.sort(key=lambda i: (rank.get(str(i.get("priority")).upper(), 9),
                              str(i.get("suspense_date") or "9999")))

    return {
        "generated": _now(),
        "open_count": len(items),
        "suppressed_by_closure": suppressed,
        "total_closures_on_record": len(closed),
        "items": items,
    }


def write_queue() -> dict:
    q = build_queue()
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return q


def filter_open(ids: Iterable[str]) -> list[str]:
    """Convenience for generators: drop anything already closed."""
    closed = closed_ids()
    return [str(i) for i in ids if str(i) not in closed]


def summary_md(limit: int = 12) -> str:
    """One 'your desk' block for the 06:30 brief — not 96 separate pages."""
    q = build_queue()
    if not q["items"]:
        return "**Your desk is clear.** No open items awaiting you."
    lines = [f"**{q['open_count']} items awaiting you** "
             f"({q['suppressed_by_closure']} suppressed by your closures)\n",
             "| Pri | Item | Title | Due |", "|---|---|---|---|"]
    for it in q["items"][:limit]:
        lines.append(f"| {it.get('priority','')} | {it['id']} | "
                     f"{it['title'][:60]} | {it.get('suspense_date','') or '—'} |")
    if q["open_count"] > limit:
        lines.append(f"\n_… and {q['open_count'] - limit} more._")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "close":
        r = close(sys.argv[2], reason=" ".join(sys.argv[3:]))
        print(f"closed {r['item_id']} — permanent, will never re-enter the queue")
    else:
        q = write_queue()
        print(f"queue: {q['open_count']} open | "
              f"{q['suppressed_by_closure']} suppressed by closure | "
              f"{q['total_closures_on_record']} closures on record")
