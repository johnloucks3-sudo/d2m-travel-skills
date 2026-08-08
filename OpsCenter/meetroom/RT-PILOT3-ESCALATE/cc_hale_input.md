BLUF: Pilot #3 — new script, `scripts/mission_auto_escalate.py`. P0/P1 missions idle >2h get auto-rerouted to a different seat via the existing router, capped at one reroute per mission ever. Real, checkable, in-repo only — no external access needed.

## Silver front frame (checkable done + named ground truth)
- **Done means:** `scripts/mission_auto_escalate.py` exists, `python3 -m py_compile` passes, and running it against a real mission with `updated_at` backdated >2h changes that mission's `assigned_to` to a different seat, sets `escalation_count: 1`, appends a `logs` entry, and does NOT re-escalate a mission that already has `escalation_count >= 1`.
- **Ground truth:** a live test run against `OpsCenter/mission_board.json` (see test steps below).

## Include (exact scope)
Create exactly one new file: `scripts/mission_auto_escalate.py`. Do not modify `OpsCenter/mission_board_sync.py` or `core/relay/task_delegation.py` — import and reuse them, don't edit them.

## Exclude
- No systemctl commands, no timer file — that's a separate step after this is verified.
- No changes to any file except the one new script.
- Do not send real Telegram/email in this build — the report function should exist but only actually fire when explicitly run with `--live` (default: `--dry-run` prints what it would report).

## Exact patterns to reuse (copy these, don't reinvent)

Mission board lock/load/save, from `OpsCenter/mission_board_sync.py`:
```python
import fcntl, json
from pathlib import Path

BOARD_PATH = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")
LOCK_PATH = Path("/home/john/Thunderbird/OpsCenter/mission_board.lock")

def acquire_lock():
    fd = open(LOCK_PATH, 'w')
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # raises BlockingIOError if locked — let it raise, don't catch
    fd.write(str(__import__("os").getpid())); fd.flush()
    return fd

def release_lock(fd):
    fcntl.flock(fd, fcntl.LOCK_UN); fd.close()
    try: LOCK_PATH.unlink()
    except FileNotFoundError: pass

def load_board():
    return json.loads(BOARD_PATH.read_text())

def save_board(board, fd):
    BOARD_PATH.write_text(json.dumps(board, indent=2, default=str))
    release_lock(fd)
```

## CORRECTION — checked the real board before writing this, two real bugs avoided

**`assigned_to` uses PERSONA names ("Hale", "Dani", "Harlan", "Intel"), not
CC/OC/AG seat codes.** `route_task()` returns "CC"/"OC"/"AG" — a completely
different namespace (that's the model-lane router, not a persona router).
Do NOT call `route_task()` for the reassignment target — it would write a
nonsensical value into `assigned_to`. **Reassignment target is always the
literal string `"Hale"`** (the standing COS/orchestrator-of-last-resort in
this codebase) — simpler and correct, not a router call at all for this
version.

**`updated_at` values are inconsistently formatted — ~78 of the real ones
are naive (no timezone offset), the rest are aware (`+00:00`).** Parsing
naively will crash on the first real run. Always do:
```python
from datetime import datetime, timezone
dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
```

## Steps (in order — this is the whole algorithm, do not add or remove logic)

1. `load_board()`. Missions live at `board["missions"]` (confirmed real key, 253 entries — don't bother with the active_missions fallback, it's not needed).
2. From `datetime import datetime, timezone` — compute `now = datetime.now(timezone.utc)`.
3. For each mission where:
   - `status` in `("active", "in_progress", "pending_review", "in_coordination")` (these are the real observed "still open" values — cancelled/completed/rolled_up/closed are excluded, no others exist in the real data)
   - `priority` in `("P0", "P1")`
   - `updated_at` parses (using the naive/aware-safe parse above) to more than 2 hours before `now`
   - `mission.get("escalation_count", 0) < 1` (not already escalated once)

   Do:
   a. `old_owner = mission.get("assigned_to")`.
   b. If `old_owner == "Hale"`: already owned by the escalation target, no real escalation available. Add this mission to a `notify_only` list. Do NOT change the mission.
   c. Else: set `mission["assigned_to"] = "Hale"`, `mission["escalation_count"] = mission.get("escalation_count", 0) + 1`, append to `mission.setdefault("logs", [])` a string: `f"{now.isoformat()}: auto-escalated (idle >2h) — reassigned {old_owner} -> Hale"`. Add this mission to an `escalated` list.
4. Missions with `escalation_count >= 1` already: skip entirely (the cap), but count them in a `capped_skipped` list for the report (do not touch them).
5. If `escalated` or `notify_only` is non-empty: `acquire_lock()`, re-`load_board()` under the lock (in case it changed), re-apply the same mutations, `save_board(board, fd)`.
6. Build a report dict: `{"escalated": [...], "notify_only": [...], "capped_skipped": [...], "scan_time": now.isoformat()}`.
7. `--dry-run` (default): print the report as JSON, make no board changes at all (skip step 5 entirely in dry-run mode — read-only).
8. `--live`: do step 5's real board mutation, then print the same report, then call a `report()` function that imports `from core.comms.commander_channel import notify` and sends a WINDOW-urgency notify() with the report content if escalated or notify_only is non-empty. If both are empty, print "nothing to escalate" and do not call notify().

## First action
As your first tool call: `cat /home/john/Thunderbird/OpsCenter/mission_board.json | head -50` — see the real board structure before writing anything.

## What do you need to succeed?
This spec is meant to be complete and literal — every step above is the whole algorithm. If something in the real mission_board.json doesn't match what's described here (different field names, different status values actually in use), say so in your result and describe what you found instead of guessing past it.
