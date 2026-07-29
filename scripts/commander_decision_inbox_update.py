#!/usr/bin/env python3
"""
Commander Decision Inbox — hourly queue refresh.

C2 RECALIBRATION task 10, Commander directive 2026-07-29.

HISTORY — WHY THIS FILE MATTERS
-------------------------------
Until 2026-07-29 this script was a 51-line stub. It ran hourly on
commander-decision-inbox-update.timer and did nothing but print a count. The work it
claimed to do lived in a comment:

    # In production, this would:
    # 1. Compare pending items against last update
    # 2. Identify new items to add
    # 3. Identify completed items to archive      <-- never implemented
    # 4. Update artifact HTML
    # 5. Update Google Sheets log

Step 3 never existed, so nothing the Commander closed was ever archived, and every
regeneration resurrected it. His report — "I have tried to reduce my queue and it keeps
getting overridden" — was an accurate description of the implementation.

The real logic now lives in core/comms/commander_queue.py, which keeps an append-only
closure ledger. This script is the thin timer entry point over it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.comms.commander_queue import write_queue  # noqa: E402


def main() -> int:
    try:
        q = write_queue()
    except Exception as exc:
        print(f"ERROR: queue refresh failed: {type(exc).__name__}: {exc}")
        return 1

    print(
        f"Decision Inbox: {q['open_count']} open | "
        f"{q['suppressed_by_closure']} suppressed by Commander closure | "
        f"{q['total_closures_on_record']} closures on record"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
