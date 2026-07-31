#!/usr/bin/env python3
"""
backfill_suspense_dates.py — fill OpsCenter/mission_board.json's ``suspense_date``
field for missions that already carry an explicit, unambiguous deadline in prose
but never got it promoted to a field.

WHY THIS EXISTS
----------------
core/comms/commander_queue.py::build_queue() sorts and surfaces the Commander's
desk by ``suspense_date``. As of 2026-07-30, of 53 missions on his desk, only 3
carry that field — everything else sorts to the bottom (`"9999"` fallback) and
never fires a heartbeat/overdue alert, no matter how urgent the prose says it is.
The Loucks Grandeur FPD was found 2 days from due with the deadline typed into a
mission TITLE ("...FPD Aug 1 is 21 days out") and nothing able to act on it.

SCOPE — deliberately narrow
----------------------------
This script does NOT try to parse every date-shaped string in every mission.
Broad extraction is exactly how you manufacture a WRONG suspense date (e.g. a
trip departure date like "Kuklinski Dec 17 air routing" is not a task
deadline — see OpsCenter/state/suspense_date_coverage.md for the false-positive
audit). It only fires on two hand-vetted, high-precision phrasings that in every
observed case mean "this task itself is due on this date":

    1. description contains  "no later than <Month> <Day>"
    2. title ENDS WITH        "by <Month> <Day>"

Both anchor on an action verb immediately controlling the date ("surface ...
no later than", "confirm payment track by"), not a date floating near an
unrelated noun. Year is taken from the mission's own `created_at` (never
assumed) so a December-created mission referencing "Jan 3" doesn't silently
roll to the wrong year.

Only fills BLANK suspense_date. Never overwrites an existing value — a human
or another process may have set it deliberately (e.g. SSS-005/006/007, or a
Commander override), and this script has no authority to second-guess that.

SAFETY
------
--dry-run is the DEFAULT and prints the full change set with no write.
--execute performs the write, after taking a timestamped backup of
OpsCenter/mission_board.json in the same directory.

This script has NOT been run with --execute. Per SO-2026-07-30 coordination
(mission_board.json is actively owned/edited by concurrent agents this
session), the write step is left for the Commander/lead to authorize and run.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "OpsCenter" / "mission_board.json"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH_RE = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"

DESC_PATTERN = re.compile(r"no later than\s+" + MONTH_RE + r"\s+(\d{1,2})\b", re.I)
TITLE_END_PATTERN = re.compile(r"\bby\s+" + MONTH_RE + r"\s+(\d{1,2})\s*$", re.I)


def _year_for(mission: dict) -> int:
    """Year comes from the mission's own created_at — never assumed from 'today'."""
    created = mission.get("created_at") or ""
    try:
        return datetime.fromisoformat(created.replace("Z", "+00:00")).year
    except ValueError:
        return datetime.now(timezone.utc).year


def extract_suspense_date(mission: dict) -> tuple[str, str] | None:
    """Returns (iso_date, matched_phrase) or None. Checks description first,
    then a title-final 'by <Month> <Day>' as a fallback."""
    year = _year_for(mission)
    desc = (mission.get("description") or "").strip()
    m = DESC_PATTERN.search(desc)
    if m:
        mon = MONTHS[m.group(1)[:3].lower()]
        day = int(m.group(2))
        return f"{year}-{mon:02d}-{day:02d}", m.group(0)

    title = (mission.get("title") or "").strip()
    m = TITLE_END_PATTERN.search(title)
    if m:
        mon = MONTHS[m.group(1)[:3].lower()]
        day = int(m.group(2))
        return f"{year}-{mon:02d}-{day:02d}", m.group(0)

    return None


def find_backfill_candidates(board: dict) -> list[dict]:
    candidates = []
    for mission in board.get("missions", []):
        if mission.get("suspense_date"):
            continue  # never overwrite
        hit = extract_suspense_date(mission)
        if hit is None:
            continue
        iso_date, phrase = hit
        candidates.append({
            "id": mission.get("id", ""),
            "status": mission.get("status", ""),
            "title": mission.get("title", ""),
            "matched_phrase": phrase,
            "suspense_date": iso_date,
        })
    return candidates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true",
                     help="Write changes to mission_board.json (default: dry-run only)")
    args = ap.parse_args()

    board = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    candidates = find_backfill_candidates(board)

    print(f"backfill_suspense_dates: {len(candidates)} mission(s) eligible "
          f"(blank suspense_date + unambiguous deadline phrase)\n")
    for c in candidates:
        print(f"  {c['id']:16s} [{c['status']:16s}] -> suspense_date={c['suspense_date']}")
        print(f"    title:   {c['title']}")
        print(f"    matched: {c['matched_phrase']!r}\n")

    if not args.execute:
        print("DRY RUN — no changes written. Re-run with --execute to apply.")
        return 0

    if not candidates:
        print("Nothing to write.")
        return 0

    backup = BOARD_PATH.with_suffix(
        f".json.bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    shutil.copy2(BOARD_PATH, backup)
    print(f"Backed up mission_board.json -> {backup}")

    by_id = {c["id"]: c["suspense_date"] for c in candidates}
    for mission in board.get("missions", []):
        if mission.get("id") in by_id:
            mission["suspense_date"] = by_id[mission["id"]]

    BOARD_PATH.write_text(json.dumps(board, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    print(f"Wrote {len(candidates)} suspense_date value(s) to {BOARD_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
