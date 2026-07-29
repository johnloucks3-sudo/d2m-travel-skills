# FIX: Silver human-override on CLOSE (2026-07-29)

## Root cause (one sentence)

Actor identity did not flow into the two live CLOSE paths at all —
`OpsCenter/mission_board_sync.py`'s `EXEC: closeout` / `EXEC: complete`
(which dispatch to `core/staffing/staff_summary_sheet.py::close_sss` and
`core/relay/delegation_wiring.py::certify_mission_and_record`) had zero
concept of "who is closing this," so every close — Commander or AI — ran the
identical full anti-theater / cross-Hale / Silver back-gate battery; the
one place that *did* have actor threading (`tcd/writeback.py::_handle_close`,
fixed by a prior uncredited agent in commit `1b967d2e` at 10:43 today) was
only ever invoked with `actor="commander"` from `tcd/web.py`, the web app
CLAUDE.md itself records as **decommissioned 2026-07-18** — so that fix was
unreachable from any live surface, and the MCP daemon that would have served
it hadn't been restarted since 03:09 today anyway (before the 10:43 commit
landed), so even the reachable half was dead code in production.

## Actor-identity trace

1. **`OpsCenter/mission_board_sync.py::process_exec_command`** — takes a raw
   command string only. No caller (nexus.py inbox scan, email C2, MCP tools)
   passes any notion of who typed it.
2. **`cmd_sss_close`** (EXEC: closeout) → **`close_sss`** — signature was
   `close_sss(sss, certified_by=None, cross_hale_evidence=None)`. No actor
   parameter existed anywhere in the SSS model.
3. **`cmd_complete`** (EXEC: complete) → **`certify_mission_and_record`** —
   same story: `assigned_to`/`certified_by` are seat names, never a
   human/AI distinction.
4. **`tcd/writeback.py::_handle_close`** — the ONE place actor already
   flowed (`actor: str = "ai"`, `actor == "commander"` bypass), but its only
   caller passing `"commander"` is `tcd/web.py`, which per
   `/home/john/Thunderbird/CLAUDE.md` was decommissioned 2026-07-18. Every
   live caller (`tcd/sheet_sync.py`, `tcd/mcp_tools.py`,
   `scripts/tcd_cli_review.py`, `core/ops/n8n_webhook_event_router.py`)
   defaults to `actor="ai"` — meaning every real close through the retained
   TCD Sheet-mirror data plane was gated as if an AI did it.

**Conclusion:** the SSS/mission-board path (§2–3) — the live
"USAF Staff Summary Sheet ... `EXEC: sss|chop|decide|accomplish|closeout|sheet`"
tasking model CLAUDE.md names as current — is where the Commander is actually
hitting the wall, and it had no actor concept whatsoever. That's the fix.

## What changed

- **`core/silver/gate.py`**
  - `PASS, HOLD, OVERRIDE = "PASS", "HOLD", "OVERRIDE"` (new verdict value).
  - `Verdict` gains `overridden_by: str | None = None`; `.ok` now also
    treats `OVERRIDE` as ok (a close may proceed).
  - New `human_override(mission_id, work_product, overridden_by, *, stage="back") -> Verdict`
    (before `_page_hold`, ~line 258) — writes an attributed `OVERRIDE` row to
    the SAME `OpsCenter/silver_ledger.jsonl` every PASS/HOLD lands in.
    Raises `ValueError` if `overridden_by` is empty (never a silent/unattributed row).
  - `brief_section()` now counts and lists overrides distinctly (🟡 OVERRIDE line).

- **`core/staffing/staff_summary_sheet.py::close_sss`** (~line 419)
  - New params `human_override: Optional[str] = None`, `human_note: Optional[str] = None`.
  - New `HUMAN_ACTOR = "Commander"` constant.
  - If `human_override` given: must equal `"Commander"` case-insensitively
    (anything else raises `SSSError` — an AI seat cannot self-attribute a
    human close by passing an arbitrary human-sounding string). On the
    literal match: skips anti-theater, cross-Hale evidence, artifact,
    criteria, and `run_gate()` entirely; sets `certified_by="Commander"`,
    status `closed`; calls `gate.human_override()`; logs an attributed line
    including `human_note` if given; mirrors to the bus. Every other call
    (no `human_override`) is byte-for-byte the pre-existing gated path.

- **`OpsCenter/mission_board_sync.py`**
  - `cmd_sss_close` (~line 643): the certifier slot now recognizes the
    reserved literal `COMMANDER` — `EXEC: closeout SSS-ID :: COMMANDER [:: reason]`
    calls `close_sss(m, human_override="Commander", human_note=reason)`. Any
    other certifier value runs the unchanged AI-seat gate.
  - `cmd_complete` (~line 800): new `human_override=False` param. When true
    (dispatcher sets it from a `COMMANDER` second token —
    `EXEC: complete MISSION-ID COMMANDER`), calls `gate.human_override()`
    directly, marks the mission completed, logs an attributed line, and
    **never calls `certify_mission_and_record`**. The pre-existing
    delegation-seat branch is otherwise untouched.
  - Dispatcher (`process_exec_command`, ~line 980) parses the `COMMANDER`
    token for `complete`. `cmd_help()` updated with both new forms.

- **`tcd/writeback.py::_handle_close`** (~line 158) — the already-committed
  `actor == "commander"` branch now also calls `gate.human_override()` so the
  Commander's TCD-board close is visible in `silver_ledger.jsonl`, not only
  in `hale_decisions.md` (it was writing to the latter only before; an audit
  scanning the Silver ledger for "did anything bypass the gate" would have
  seen nothing).

`core/relay/delegation_wiring.py::certify_mission_and_record` /
`certify_mission()` were **not modified** — cross-Hale seat-to-seat
certification stays fully gated, unconditionally, exactly as designed.

## Ground-truth verification

Ran real code (not just tests) against tmp-redirected ledgers/board, then
the actual pytest suite.

**Case 1 — `close_sss` direct, human override, zero artifact:**
```
HUMAN OVERRIDE CLOSE: OK, status= closed certified_by= Commander
```
**Case 2 — same function, AI-seat (assigned CC, certifier OC, no artifact):**
```
AI CLOSE CORRECTLY BLOCKED (still not accomplished): cannot close an SSS in status 'tasked' (must be accomplished)
```
**Case 3 — forgery attempt (`human_override="CC"`):**
```
FORGERY CORRECTLY REJECTED: human_override must be 'Commander' (the Commander) — got 'CC'; an AI seat cannot self-attribute a human close
```
**Case 4 — real AI-seat lifecycle (artifact + cross-Hale evidence) still passes as PASS, not OVERRIDE:**
```
AI CLOSE OK: closed certified_by= OC
```

**Real CLI end-to-end** (`process_exec_command`, actual file-locked board):
```
✅ Staff Summary Sheet opened: SSS-001            [coordinated -- no chop/decide/accomplish]
✅ SSS-001 CLOSED — Commander override (human close is self-certifying, no gate)
SSS-001 after override closeout: closed certified_by= Commander
  logs[-1]= ...closed by COMMANDER OVERRIDE — no gate, human close is self-certifying — Yoda said ship it
⛔ Close-out held: cannot close an SSS in status 'coordinated' (must be accomplished)   [SSS-002, AI path, unchanged]

✅ Completed: MISSION-1 — test human override complete (Commander override, no gate)
⛔ Cannot complete MISSION-2 — delegation gate: no verification_artifact — cannot certify done (§3.5.2)   [unchanged]
```

**`tcd/writeback.py::_handle_close`, both actors, direct call:**
```
commander close done (no exception, no artifact required)
ai close done (recorded, but should show HOLD in ledger since bare claim)
```

**Ledger rows read back (ground truth, `OpsCenter/silver_ledger.jsonl` schema,
tmp-redirected copy)** — every override is a distinct, attributed row, never
confusable with a PASS:
```
PASS     | SSS-VERIFY-1 | overridden_by=None      | []
OVERRIDE | SSS-VERIFY-1 | overridden_by=Commander | []
PASS     | SSS-VERIFY-2 | overridden_by=None      | []   <- AI-seat sheet, still blocked before this line even ran
OVERRIDE | MISSION-1    | overridden_by=Commander | []
OVERRIDE | TCD-ROW-1    | overridden_by=Commander | []
HOLD     | TCD-ROW-2    | overridden_by=None      | ["artifact is a bare claim, not a concrete reference: 'done, trust me'"]
```

## Tests added

- `tests/test_staff_summary_sheet.py` — 5 new tests appended (Commander
  human-override section): closes with zero artifact, case-insensitive
  literal, AI-seat forgery rejected, **AI-seat close still fully gated
  without the override param** (regression guard), and a ledger-row
  assertion (`OVERRIDE` row present, distinct from any `PASS`).
- `tests/test_human_override_close.py` (new file) — 8 tests at the real CLI
  dispatch layer (`process_exec_command`) and `tcd/writeback.py`, each pair
  proving both directions: `test_sss_commander_closeout_needs_no_artifact` /
  `test_sss_ai_seat_closeout_still_gated`;
  `test_mission_complete_commander_override_no_artifact` /
  `test_mission_complete_ai_seat_still_gated_no_override_token`;
  `test_writeback_commander_close_no_artifact` /
  `test_writeback_ai_actor_close_still_gated`.

**Full run:**
```
tests/test_human_override_close.py tests/test_staff_summary_sheet.py
tests/test_delegation_wiring.py tests/test_tcd_writeback.py
tests/test_mission_dedupe_entity.py tests/test_delegation_outcomes.py
118 passed, 11 passed  (129 total, 0 failed)
```

## Operational follow-up taken

Restarted `thunderbird-mcp.service` and `thunderbird-mcp-tailscale.service`
(both confirmed `active` after restart) — `core/silver/gate.py` and
`tcd/writeback.py` are on the "needs daemon restart, no hot-reload" list, and
both were stale relative to the 10:43 commit that already touched them
before I even started. The `mission_board_sync.py` CLI path needs no restart
— it's a fresh `python3` invocation per call, live immediately.

## Residual risk / what's still not solved

There is **no cryptographic proof of humanness** anywhere in this design —
`human_override="Commander"` / the `COMMANDER` CLI token / `actor="commander"`
are all trust-based attribution, identical in kind to the pre-existing
`tcd/web.py` precedent (which relies on that endpoint's Basic-Auth, not on
anything in the gate itself). Nothing stops an AI seat from typing the
literal string `COMMANDER` into an `EXEC:` command if it chooses to — the
control here is procedural (CLAUDE.md/Standing Orders forbidding an AI from
self-invoking the override), not structural. I flagged the specific reserved
literal to make an accidental/casual collision unlikely (no seat name is
`COMMANDER`) and made every use of it attributed + ledger-visible so a
misuse is at least auditable after the fact, but a determined AI agent
could still type it. Closing that gap would need the override to originate
only from a channel structurally tied to the Commander (e.g., the Basic-Auth
TCD Sheet edit itself, or a Telegram/AgentMail message from the Commander's
own verified account) rather than a CLI string — that wiring does not exist
today and is out of scope for this fix.
