#!/usr/bin/env python3
"""
scripts/clear_proposal_backlog.py — route the stage-P backlog through P->D->T.

WHY THIS EXISTS
---------------
On 2026-07-30 the live board held 267 items. 157 of them sat at stage P
("Proposed"), and the D and T gates had NEVER been transited — not once, ever:

    P 157 · A 44 · C 30 · REF 36 · D 0 · T 0

SO_PDTAC_WORKFLOW_20260711 states "No proposal sits unanswered >48h." The
pipeline did not stall; it was never routed. Work that SO-2026-05-04 and
SO_STRATOPSTAC_20260610 make Hale's to decide had been parked on the
Commander's desk instead — 154 of the 157 were `operational`.

One of them was a final payment 2 days out, sitting at "Proposed" since ~July 11.

Every mechanism needed to fix this ALREADY EXISTED in tcd/writeback.py —
_handle_stage_move, _handle_auto_task (Silver front frame -> assign_owner ->
set_override(stage="T")), _append_decision. Nothing was missing but the call.
This script is that call. It builds no new write path and reimplements no
handler.

COMMANDER'S DIRECTIVE (2026-07-30)
----------------------------------
    "Hand me only the ones that are not yours. YOU approve as a default.
     Only disapprove if there is a good reason, no deferring vital proposals."

So: approve is the default. Disapproval requires a stated reason. Nothing vital
is deferred. Items that are genuinely the Commander's — Strategic inbox, or
typed `decision` — are NEVER touched here; they are listed for him.

SILVER HOLDS ARE NOT FAILURES
-----------------------------
_handle_auto_task runs Silver's front frame on delegated work. A HOLD means the
item's "done" was never concretely defined, so no seat gets committed and the
reason is written into the row's own comments. Those items stop at D and are
reported. That is the gate working, not the script failing.

USAGE
    python3 scripts/clear_proposal_backlog.py --dry-run     # default, changes nothing
    python3 scripts/clear_proposal_backlog.py --execute
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tcd.collectors import collect_all              # noqa: E402
from tcd import writeback                           # noqa: E402


def is_commanders(item) -> bool:
    """Strategic inbox or a typed decision — his under SO_STRATOPSTAC.

    Deliberately generous: when in doubt an item stays with the Commander
    rather than being auto-approved. Erring toward his desk costs him a
    glance; erring the other way spends his authority without asking.
    """
    return ((getattr(item, "inbox", "") or "").strip().lower() == "strategic"
            or (getattr(item, "type", "") or "").strip().lower() == "decision")


def to_row(item) -> dict:
    """Item dataclass -> the plain dict the writeback handlers expect.

    `source` maps to the row's "from" column — the dataclass renames it
    because `from` is a Python keyword (see tcd/item_model.py).
    """
    return {
        "id": item.id,
        "title": getattr(item, "title", "") or "",
        "type": getattr(item, "type", "") or "",
        "inbox": getattr(item, "inbox", "") or "",
        "priority": getattr(item, "priority", "") or "",
        "stage": getattr(item, "stage", "") or "",
        "status": getattr(item, "status", "") or "",
        "from": getattr(item, "source", "") or "",
        "date": getattr(item, "date", "") or "",
        "snippet": getattr(item, "snippet", "") or "",
        "body": getattr(item, "body", "") or "",
        "link": getattr(item, "link", "") or "",
        "comments": getattr(item, "comments", "") or "",
        "owner": getattr(item, "owner", "") or "",
        "sourcePath": getattr(item, "sourcePath", "") or "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True)
    g.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    execute = args.execute

    items = collect_all(include_gmail=False, include_keep=False, include_sms=False)
    proposed = [i for i in items if (getattr(i, "stage", "") or "") == "P"]

    commanders = [i for i in proposed if is_commanders(i)]
    mine = [i for i in proposed if not is_commanders(i)]

    print(f"{'EXECUTE' if execute else 'DRY RUN'} — stage-P backlog")
    print(f"  total at P : {len(proposed)}")
    print(f"  Commander's: {len(commanders)}  (strategic or typed decision — untouched)")
    print(f"  Hale's     : {len(mine)}")
    print()

    print("COMMANDER'S ITEMS — surfaced, never auto-decided:")
    for i in commanders:
        print(f"  [{(getattr(i,'inbox','') or '')[:11]:11}] [{(getattr(i,'type','') or '')[:8]:8}] "
              f"{str(getattr(i,'title',''))[:72]}")
    print()

    if not execute:
        owners = Counter()
        for i in mine:
            from tcd import assignment
            owners[assignment.assign_owner(to_row(i))] += 1
        print("WOULD APPROVE (P -> D -> T), by assigned owner:")
        for o, n in owners.most_common():
            print(f"  {o:12} {n}")
        print("\nNo changes made. Re-run with --execute.")
        return 0

    tasked, held, errors = Counter(), [], []
    decisions_path = ROOT / "hale_decisions.md"

    for item in mine:
        row = to_row(item)
        try:
            # P -> D. The Commander's standing authority delegates this
            # (SO-2026-05-04); approve is the default per his 2026-07-30
            # directive. Recorded as a real stage move, not a silent flip.
            writeback._handle_stage_move(row, "P", decisions_path, to_stage="D")

            # D -> T. Silver's front frame gates delegated work inside this
            # call; a HOLD leaves the item at D with the reason in comments.
            owner = writeback._handle_auto_task(row, decisions_path)
            if owner:
                tasked[owner] += 1
            else:
                held.append((row["id"], row["title"][:60]))
        except Exception as exc:
            errors.append((row["id"], f"{type(exc).__name__}: {exc}"))

    print(f"TASKED  : {sum(tasked.values())}")
    for o, n in tasked.most_common():
        print(f"  {o:12} {n}")
    print(f"\nSILVER HELD at D: {len(held)}  (no checkable 'done' — gate working, not a failure)")
    for i, t in held[:10]:
        print(f"  {i[:34]:34} {t}")
    if len(held) > 10:
        print(f"  … and {len(held)-10} more")
    if errors:
        print(f"\nERRORS: {len(errors)}")
        for i, e in errors[:10]:
            print(f"  {i[:34]:34} {e}")

    print(f"\nInvariant: {sum(tasked.values())} tasked + {len(held)} held + "
          f"{len(errors)} errored = {sum(tasked.values())+len(held)+len(errors)} of {len(mine)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
