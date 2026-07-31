# Suspense Date Coverage — Findings & Proposed Fix

**Date:** 2026-07-30
**Scope:** `core/comms/commander_queue.py::build_queue()`, `OpsCenter/mission_board.json`,
`tcd/item_model.py`, `tcd/collectors.py`, `OpsCenter/mission_board_sync.py`.
**Constraint honored:** `OpsCenter/mission_board.json` was NOT modified. No writes made
anywhere. `scripts/backfill_suspense_dates.py` was run in its default `--dry-run` mode
only — `--execute` was never invoked.

---

## 1. Where suspense_date comes from, and why it's mostly missing

`build_queue()` (`core/comms/commander_queue.py:259-290`) pulls two kinds of item onto
the Commander's desk:

- **missions** (status `pending_review` / `in_coordination`, not closed) —
  `suspense_date = m.get("suspense_date", "")`, read straight off the mission record
  in `OpsCenter/mission_board.json`.
- **alerts** (from `hale_state.json::deferred_alerts`) —
  `suspense_date = a.get("trigger_date", "")`. Alerts have their own, separately-fed
  date field, unaffected by this report.

**Measured against the live queue right now (re-running `build_queue()` directly, not a
static grep):**

| | count | has `suspense_date` |
|---|---|---|
| missions | 53 | **3** (SSS-005, SSS-006, SSS-007) |
| alerts | 10 | 10 (100%) |

Across the full board (`OpsCenter/mission_board.json`, all 211 missions regardless of
status), only 3 carry `suspense_date` — the same three. It is not that missions lose the
field somewhere downstream; **it is never set in the first place.**

### Root cause — confirmed in code

`OpsCenter/mission_board_sync.py:325` — `add_mission()` is the single mission-creation
entry point (the docstring says so explicitly: "the ONE place mission-creation ...
logic lives"). Its signature:

```python
def add_mission(board, title, description="No description", priority="P0",
                assigned_to="unassigned", source=None, acceptance_criteria=None,
                certified_by=None, deadline_hours=None, task_type=None,
                from_seat="CC", ground_truth_sources=None):
```

**There is no `suspense_date` parameter.** Line 394 hardcodes `"suspense_date": None`
into every new mission. The only way to set it afterward is a separate, manual command
— `EXEC: add suspense <id> <date>` (`mission_board_sync.py:802`) — that nothing calls
automatically at creation time. A caller who already knows the deadline when creating
the mission (e.g. "$24,798 FPD due August 1") has nowhere to put it in the same call;
it has to come back later and issue a second, easy-to-forget command. That is the
structural reason 208/211 missions have never carried the field, not an extraction or
sync bug.

---

## 2. TCD Item model — no suspense_date field at all

`tcd/item_model.py` (`Item` dataclass, `SHEET_COLUMNS`) carries a single generic
`date` field — populated from the *source* (Gmail received date, mission `created_at`
via `scripts/tcd_data.py`, etc.), not a deadline. There is no `suspense_date` /
`due_date` / `deadline` column anywhere in `SHEET_COLUMNS` or `Item`.

`tcd/collectors.py::collect_local()` pulls missions in via
`td.build_missions(state)` (in `scripts/tcd_data.py`, not read here per scope) — that
build function would need to be the one to carry `suspense_date` through if TCD's
Google Sheet surface is meant to show it. As it stands, even the 3 missions that DO
have `suspense_date` in the board (SSS-005/006/007) have no path to show that date on
the TCD sheet — confirming the earlier finding that TCD has a `date` field but no
`suspense_date` field.

**This gap is real but out of this fix's scope** — `tcd/writeback.py` is another
agent's file per the tasking, and wiring `suspense_date` through
`collect_local()`/`item_model.py`/the Sheet columns is a second, TCD-side change.
Flagging it here so it doesn't get lost: SO-2026-07-19 named the suspense date a
load-bearing SSS field, and the TCD surface currently cannot display it.

---

## 3. Prose-date audit — the hard count

Searched every one of the 53 queue-eligible missions' `title` + `description` for date
signals (ISO dates, "Month Day", "due", "FPD", "by <Month>", "N days out/left",
"deadline") where `suspense_date` is blank.

**12 of 53** open missions have *some* date-shaped text in prose with no
`suspense_date` field. Breaking that down by how trustworthy the signal actually is
(this matters — the first, naive regex pass overcounted at 25 by including 23 items
that are already closed via the closure ledger and never reach the real desk):

**Explicit, unambiguous, and clearly the mission's OWN deadline (3):**

| ID | Phrase | Extracted date |
|---|---|---|
| MISSION-666 | "...no later than July 25..." | 2026-07-25 |
| MISSION-705 | "...no later than July 25..." | 2026-07-25 |
| MISSION-714 | "...confirm payment track by July 25" | 2026-07-25 |

All three are already **overdue** — today is 2026-07-30, five days past the date typed
into their own prose. That prose-only deadline never fired anything.

**Date signal present but NOT a safe backfill (9):** either it's a *trip* date, not a
task deadline (MISSION-048, 688, 756 — "Kuklinski Dec 17" is when the client sails, not
when the mission is due), a bare acronym with no date attached (MISSION-710, 723, 743 —
"FPD" alone), a *stale historical* reference to a deadline already blown for a different
prior task (MISSION-728, 742 — "brief shows April 15 due date, now three months past"),
or vague relative phrasing with no anchor (MISSION-743 — "before end of week", no date
math attempted). None of these should be auto-backfilled; each needs a human or a
smarter mission-specific rule to assign the real due date.

**One false positive worth naming:** MISSION-671 contains an ISO date
(`2026-07-17`) that is a CHIEF SILVER front-frame timestamp ("front-framed
2026-07-17"), not a deadline — proof that naive ISO-date extraction alone is unsafe and
why the backfill script below anchors on deadline-shaped phrases, not bare dates.

---

## 4. Proposed fix

**A. Immediate backfill (script written, NOT executed — see §5).**
`scripts/backfill_suspense_dates.py` fills only missions where `suspense_date` is blank
AND the prose contains one of two hand-vetted, high-precision phrasings that in every
observed case anchor an action verb to the date, not an incidental date mention:

1. description matches `no later than <Month> <Day>`
2. title *ends with* `by <Month> <Day>`

Year comes from each mission's own `created_at`, never assumed from "today". It never
overwrites an existing value. Dry-run output in §5.

**B. Stop it recurring — fix `add_mission()`.**
Add an optional `suspense_date: str | None = None` parameter to
`OpsCenter/mission_board_sync.py::add_mission()` (line 325) and wire it into
`cmd_add`'s argv parser (line 430) and any MCP/structured callers, so a caller that
already knows the deadline sets it in the SAME call that creates the mission — no
second manual `EXEC: add suspense` step to forget. This is the mission-creation-time
fix the tasking asked for; **not implemented here**, since it touches the shared
mission-creation path other agents may be mid-edit on — recommend a dedicated,
reviewed change rather than folding it into this investigation.

**C. Consider a soft gate, not a hard block.** Given the FPD near-miss, a P0/P1 mission
created with financial or date-bearing language and no `suspense_date` is exactly the
failure mode that recurred. A non-blocking warning at creation time (surfaced the way
other soft gates in this codebase work, e.g. `build_flash_task`'s checkability warning)
would catch it without adding friction to routine missions that genuinely have no date.

**D. TCD column.** Separately, add `suspense_date` to `tcd/item_model.py::SHEET_COLUMNS`
so the Google Sheet surface can show it once §B exists. Left to the TCD owner per scope.

---

## 5. Dry-run output (as run, `--execute` never invoked)

```
$ python3 scripts/backfill_suspense_dates.py
backfill_suspense_dates: 5 mission(s) eligible (blank suspense_date + unambiguous deadline phrase)

  MISSION-040      [cancelled       ] -> suspense_date=2026-07-17
    title:   Stage two client TP drafts in WF-17 queue by Jul 17
    matched: 'by Jul 17'

  MISSION-666      [pending_review  ] -> suspense_date=2026-07-25
    title:   Surface Loucks Grandeur FPD reminder at 7-day mark
    matched: 'no later than July 25'

  MISSION-705      [pending_review  ] -> suspense_date=2026-07-25
    title:   Close Kuklinski and Westbrook welcome emails this week
    matched: 'no later than July 25'

  MISSION-714      [pending_review  ] -> suspense_date=2026-07-25
    title:   Loucks Grandeur FPD — confirm payment track by July 25
    matched: 'by July 25'

  MISSION-720      [rolled_up       ] -> suspense_date=2026-07-31
    title:   Confirm or escalate Loucks Grandeur FPD payment by July 31
    matched: 'by July 31'

DRY RUN — no changes written. Re-run with --execute to apply.
```

Note the scan runs against the whole board (all statuses), so it also caught two
terminal missions (MISSION-040 `cancelled`, MISSION-720 `rolled_up`) — harmless to
backfill for audit completeness since `build_queue()` filters `TERMINAL` statuses out
before sorting, but they will not affect the live desk either way. The three that
matter for the Commander's actual desk right now are MISSION-666, MISSION-705, and
MISSION-714 — all `pending_review`, all already 5 days overdue against their own
stated deadline.

**Recommendation:** authorize `--execute` for this script (it only fills blanks, never
overwrites, and takes a timestamped backup before writing), then track item 4B
(`add_mission()` parameter) as the actual root-cause fix so this doesn't recur on the
next 208 missions.
