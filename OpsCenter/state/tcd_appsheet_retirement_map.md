# TCD → Slack Migration — AppSheet/Sheet Retirement Map

Task 23 (analysis only, no code changes). Repo: `/home/john/Thunderbird`.
Generated 2026-07-29 21:5x MDT. Every file below was read in full; every
systemd/service claim below was checked against live `systemctl --user`
output, not against docstrings or CLAUDE.md.

---

## ⚠️ GROUND-TRUTH CORRECTION BEFORE THE MAP — `tcd/web.py` is NOT dead

The task brief and `CLAUDE.md` (`TCD WEB APP DECOMMISSIONED 2026-07-18`)
both describe `tcd/web.py` as the retired app. **That is stale.** Live
checks:

```
config/client_portals.json → "tcd.d2mluxury.quest": {
  "kind": "tcd_board", ...
  "note": "RESTORED 2026-07-28 (was retired 2026-07-12 Phase 4). Live view +
  write-back onto the same TCD Google Sheet AppSheet uses ... Commander
  directive: real board on d2mluxury.quest talking to the Sheet."
}

$ systemctl --user is-active client-portal-server.service → active
$ systemctl --user is-enabled client-portal-server.service → enabled
```

`scripts/client_portal_server.py:116-117,142-146` routes any tenant with
`kind: "tcd_board"` straight into `tcd_web.render_board()` (GET) and
`tcd_web.handle_post_body()` (POST `/tcd/act`). `tcd.d2mluxury.quest` is
registered with that `kind` today. **This means `tcd/web.py` is a live,
Commander-facing, write-capable second decision surface right now** —
Approve/Hold/Reject/Close/Modify buttons that call `writeback._default_write_fn`
and `writeback.process_once(actor="commander")` for real. It is not
presentation debris left over from a shutdown; it is the thing this
migration has to actively shut off (kill the `client_portal_server.py`
route or delete the `tcd_board` registry entry), or the Commander will have
two competing "real" decision surfaces (Slack + this board) writing to the
same Sheet after Slack ships.

Also live: `thunderbird-mcp.service` (`active`/`enabled`), which has
`tcd.mcp_tools.register_tcd_tools` wired in at
`core/mcp/travel_mcp_server.py:171,600` — so `tcd_get_items`,
`tcd_sync_now`, and **`tcd_process_writeback`** are callable MCP tools
right now, independent of both the timer and the web board. That's a
**third** live trigger into the same write-back engine (see the summary
table below).

So there are currently **three independent live paths** that can fire
`writeback.process_once()` / the individual `_handle_*` actions: the
10-minute timer (`tcd-sync.service`, confirmed `active`/`enabled`,
next-fire ~5 min out at capture time), the `tcd.d2mluxury.quest` web
board, and the `tcd_process_writeback` MCP tool. Any retirement plan that
only touches the timer leaves two of the three doors open.

---

## Per-file / per-function classification

Legend: **KEEP** = KEEP-LOAD-BEARING · **PRES** = PRESENTATION-ONLY ·
**DEAD** = ALREADY-DEAD (unreachable today) · **MIXED** = split within one
function, called out explicitly.

### `tcd/web.py` (411 lines) — the live Commander Desktop board

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 28-32 | `INBOX_ORDER` | PRES | Board layout constant, HTML-rendering only. |
| 34 | `ACTIVE_STAGES` | PRES | Board-lane filter constant. |
| 44-46 | `_id_prefix` | PRES | Board-only row-id parsing helper. |
| 49-72 | `_pending_rows` | PRES | Board's "give me current items" query — merges `writeback.read_sheet_rows()` + `multi_tab.collect_multi_tab()` + `overrides.load_overrides()`. Real merge logic, but its *shape* (not this exact code) is what a Slack App Home would need; see recommendation below. |
| 80-84 | `_ACTION_MARKERS` | PRES | Comment-marker vocabulary for rendering a decided-state pill on the HTML card. |
| 87-109 | `_action_state` | PRES | Derives display label from status/stage/comments for the HTML pill. |
| 112-151 | `_card` | PRES | HTML card renderer. |
| 154-199 | `render_board` | PRES | Full-page HTML renderer. |
| 202-253 | `apply_action` | PRES (reference logic) | Verb→Sheet-update mapping (Approve→stage=D, Hold→comment marker, Reject→status=Delete, Close→status=Closed+self-certifying, Modify→comment append). This mapping is exactly what Slack's Approve/Hold/Reject/Close/Modify buttons need to reproduce. It is currently reachable only through this HTTP route, so as *code* it is presentation-bound, but it is the correct reference implementation for `core/comms/tcd_actions.py` (task #20) — port the logic, don't reinvent it. |
| 256-268 | `handle_post_body` | PRES | HTTP JSON/form parsing wrapper around `apply_action`. |
| 271-411 | `_PAGE` (HTML/CSS/JS) | PRES | The entire client-side board UI. |

**What breaks if `tcd/web.py` stops running (i.e. is retired as part of
this migration):** `tcd.d2mluxury.quest` (Basic-Auth: `commander` /
current password in `config/client_portals.json`) stops rendering the
board and its `/tcd/act` POST route 404s/500s. Nothing else in the repo
depends on it (see the `multi_tab` grep below — its only other caller is
a throwaway test script). This is the *intended* effect of the migration,
not a side effect to avoid — but it must be a **deliberate step** (edit
`config/client_portals.json` to drop/repoint the `tcd_board` entry, or
stop routing that host), not something that happens implicitly by
building Slack alongside it.

---

### `tcd/writeback.py` (606 lines) — the write-back engine

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 71-76 | `_load_json` | KEEP | Generic state-file reader, used throughout. |
| 78-82 | `_save_json` | KEEP | Generic state-file writer (atomic tmp+replace). |
| 85-111 | `read_sheet_rows` | KEEP | Reads the live Items tab. Needed for Slack to read board state off the Sheet-as-read-only-mirror (same call `tcd_get_items` already uses). |
| 114-116 | `_plan_id` | KEEP | Audit-trail id builder. |
| 119-133 | `_append_decision` | KEEP | Writes the PLAN:CLOSE block to `hale_decisions.md` — the canonical Wing audit trail, front-end agnostic. |
| 136-148 | `_handle_dispose` | KEEP | Real cascade delete at the source (`tcd_data.delete_item`). Core handler — Slack's Reject button must call this (or the equivalent) directly. |
| 151-155 | `_gate_note` | KEEP | Silver verdict → one-line note. Small shared helper. |
| 158-208 | `_handle_close` | KEEP | Commander self-certifying close vs. AI/AppSheet-diff Silver-gated close. This is the exact function Slack's Close button needs (`actor="commander"` path already exists and is front-end-agnostic — it takes a `row` dict, not an HTTP request). |
| 211-246 | `apply_non_sheet_action` | KEEP | Override-only persistence path for rows with no Sheet cell (multi_tab-origin mission-/techscan-/next7- rows). Slack will need this exact fallback for the same row classes. |
| 249-264 | `_handle_stage_move` | KEEP | Stage-transition audit + Silver gate on a move into Certify (`C`). |
| 267-320 | `_handle_auto_task` | KEEP | D→T auto-tasking with Silver front-frame gate (MISSION-658 fix — HOLD is surfaced, never silent). Core business logic, independent of front end. |
| 323-330 | `_handle_comment` | KEEP | Comment-diff audit logger. |
| 333-342 | `CREATE_TASK_MARKER`, `_commander_note` | KEEP | Marker vocabulary + note-extraction for the "Create Task" FYI action. |
| 345-407 | `_default_create_task_fn` | KEEP | Files a real, deduped mission via `mission_board_sync` (the 2026-07-16 regression fix for duplicate-mission flooding). Genuine business logic. |
| 410-422 | `_handle_create_task` | KEEP | Wraps the above + audit log. |
| 425-426 | `_default_delete_fn` | KEEP | Thin wrapper to `tcd_data.delete_item`. |
| **429-465** | **`_default_write_fn`** | **PRES** | Pushes corrected cell values straight back into the live Sheet so "the Sheet, the override, and the Commander's own eyes all showing the same value at all times" (docstring, line 439-440) — i.e. so a human staring at the *raw Sheet/AppSheet UI* sees current truth in real time. Once Slack is the surface and nothing is supposed to write into the Sheet except the periodic collector push, there is no longer a human whose eyes need the raw cell updated instantly — `tcd/overrides.py` (already the sole mechanism for non-Sheet rows) can carry all state until the next full push reconciles it. **What breaks if it stops:** the raw Google Sheet cell can lag the true state (held in the override file) by up to one 10-minute push cycle. Anyone who opens the raw Sheet or the AppSheet app directly (bypassing Slack) during that window sees a stale stage/owner/status value. Acceptable for a genuinely read-only mirror; unacceptable if anyone is still expected to *act* off the raw Sheet. |
| **469-598** | **`process_once`** (outer diff shell) | **MIXED** | The function *body* (lines 495-596: `prior_state` load, the `status=="Delete" and prev!="Delete"` / `stage=="D" and prev=="P"` / comment-length-diff checks) exists to answer one question: *"what did a human just edit directly in the Sheet/AppSheet UI since the last pass?"* Every branch inside it calls a KEEP handler (`_handle_dispose`, `_handle_close`, `_handle_stage_move`, `_handle_auto_task`, `_handle_comment`, `_handle_create_task`) — those callees stay. The diff-detection *shell itself*, and its `write_fn(...)` calls back into `_default_write_fn` (lines 549, 556), are PRESENTATION-ONLY under the "Slack drives actions directly, Sheet is read-only mirror" design, because once nothing but the periodic push writes to the Sheet, `row` will always equal `prev` and no branch will ever fire — the loop still runs every 10 minutes and does real Sheets-API reads for zero effect. **What breaks if the whole function stops being called:** see the dedicated timer section below — this is the load-bearing question the team lead asked. |

---

### `tcd/sheet_sync.py` (166 lines) — the collector→Sheet push

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 36-41 | `collect_rows` | KEEP | Calls `collectors.collect_all()` — the actual item-gathering pipeline (Gmail/Keep/SMS/internal/watchdog). Front-end agnostic; Slack needs this same collection regardless of whether it also pushes to a Sheet. |
| 44-63 | `_dry_run` | KEEP | Offline dev/verification tool, no Google writes. Useful for anyone debugging collectors regardless of surface. |
| 66-70 / 73-76 | `_load_config` / `_save_config` | KEEP | Trivial config I/O, shared with `sections_sync.py`. |
| 78-85 | `_create_sheet` | KEEP | One-time Sheet bootstrap — harmless to keep even as a pure read-only mirror (something still has to create the Sheet the first time). |
| **88-138** | **`_live_sync`** | **MIXED** | Lines 103-116 (the `writeback.process_once()` call + its log lines) are the write-back half — PRESENTATION-ONLY per the `process_once` analysis above. Lines 118-131 (fresh `collect_rows()` + clear+rewrite of the `Items` tab) are the KEEP "Sheet PUSH" half the team lead's plan explicitly wants retained as a read-only mirror. `skip_writeback` (the `--no-writeback` CLI flag, already present at line 89/152) is the existing on/off switch for exactly this split — no new plumbing needed to separate the two halves, only a decision to always pass it. |
| 141-166 | `main` (CLI/argparse) | KEEP | Entry point; `--no-writeback` flag already exists and is the mechanism to implement "keep push, drop writeback" without touching a single line of `_live_sync`'s body. |

---

### `tcd/multi_tab.py` (162 lines) — second-spreadsheet merge

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 4-162 | `collect_multi_tab` | PRES (contingent) | Only two callers in the whole repo: `tcd/web.py:50-52` (the live-but-retiring board) and `ag_test.py:5,20` (an ad hoc, unscheduled scratch script at repo root — not a service, not imported by anything else). **No timer, no MCP tool, no other production path calls this.** The instant `tcd/web.py` is retired, this function has zero remaining production callers and becomes truly dead code (not just presentation-only). |

**Open question, not a silent deletion call:** this module reads a
**second, separate spreadsheet** (`sheet_id = "1L7WWppZ7LB9Is5EUBp9zu6FThPghcyuGuB4IEQtYsUQ"`,
hardcoded at line 12 — distinct from the `config/tcd_sheet_config.json`-tracked
"Items" spreadsheet `sheet_sync.py` manages), pulling `CommanderReview`,
`Missions`, `ELON 77`, `TechScans`, `Next7` tabs and deduping against
`existing_mission_ids` (lines 44-136; the stderr print at line 160 labels
this "AG Dedup stats", suggesting it's the AG/Antigravity-side board).
**If that second spreadsheet is still a live decision source for the
Commander or AG, its 3-way dedup logic needs a new home in the Slack
surface (task #18/#20) before this file is deleted — it is not simply
AppSheet debris.** If that spreadsheet is itself abandoned, this file is
safe to remove once `web.py` is gone.

---

### `tcd/sections_sync.py` (126 lines) — Intel/TechScans/Next7 tabs

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 32-35 | `collect_section_rows` | PRES | Calls `sections.collect_intel/collect_techscans/collect_next7`. |
| 38-42 | `_noop_mirror` | PRES | Dry-run stub. |
| 45-67 | `_dry_run` | PRES | Offline dev tool for this tab set. |
| 70-77 | `_ensure_tab` | PRES | Creates the tab if missing. |
| 80-110 | `_live_sync` | PRES | Clear+rewrite of `Intel`/`TechScans`/`Next7` tabs — explicitly documented (lines 6-9) as existing "so Looker Studio reads them exactly like the Items tab," i.e. a read-only reporting surface, not part of the Commander action loop at all. |
| 113-126 | `main` | PRES | CLI entry point. |

**Already effectively dead today, independent of this migration:** grepping
the whole repo for `sections_sync` finds only its own file and its own
test (`tests/test_tcd_sections_sync.py`) — **no timer, no cron, no
systemd unit, no other caller invokes it.** It is not on the 10-minute
cadence or any other schedule found on this box.

**What breaks if it stops running:** nothing in the decision/action loop —
zero coupling to `writeback`'s handlers or to `process_once`. Only effect
is that the `Intel`/`TechScans`/`Next7` tabs on the Items spreadsheet stop
refreshing, which only matters if a Looker Studio dashboard actually
consumes them (no evidence of one was found in this repo; unverifiable
from here — flag for the Commander/AG to confirm before deleting).

---

### `tcd/staging.py` (117 lines) — P-D-T-A-C + status derivation

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 18-71 | `derive_stage` | KEEP | Pure function, no Sheets/HTML/AppSheet coupling. Called by `tcd/collectors.py:44` — part of the core item model every consumer (Sheet push, `tcd/web.py`, and any future Slack board) needs to compute P/D/T/A/C. |
| 77-100 | `derive_kind` | KEEP | Proposal-vs-FYI split, same reasoning. |
| 106-117 | `derive_status` | KEEP | Open/Reference/Closed/Delete initial status. Same reasoning. |

Entirely KEEP — this is the "item model" half the task brief explicitly
calls out. Nothing here retires.

---

### `tcd/mcp_tools.py` (83 lines) — live MCP tool registration

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 21-42 | `tcd_get_items_tool` | KEEP | Read-only Sheet query. Directly reusable as-is for Slack/App-Home board rendering (it's already front-end-agnostic — returns JSON). |
| 44-65 | `tcd_sync_now_tool` | KEEP | On-demand collect+push (`sheet_sync._live_sync`). This is the "push" half; keep it as the manual trigger for the read-only mirror refresh. |
| **67-83** | **`tcd_process_writeback_tool`** | **PRES** | On-demand trigger of `writeback.process_once()` — a **third, independent live path** into the same AppSheet-diff engine discussed above (beyond the timer and `tcd/web.py`). Docstring (lines 76-79) claims it's "the same one the (currently disabled) 10-minute timer calls" — **that claim is false today**: `tcd-sync.timer` is `active`/`enabled` and fired ~4 minutes before this analysis was run. That's a doc/reality mismatch worth fixing regardless of the Slack migration. Once Slack's `tcd_actions.py` calls the `_handle_*` functions directly, this tool has nothing left to diff (Sheet will only ever match its own last-pushed state) and becomes a no-op every time it's called — safe to keep as an inert catch-all for stray direct-Sheet edits, or retire alongside `process_once`'s diff shell. |

---

### `tcd/watchdog.py` (165 lines) — generic OpsCenter-file collector

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 32-39 | `_load_json` | KEEP | |
| 42-44 | `_snip` | KEEP | |
| 47-69, 72-90, 93-121, 124-139 | four `_extract_*` functions | KEEP | Per-file alert-worthiness logic. |
| 144-149 | `REGISTRY` | KEEP | |
| 152-165 | `collect_watchdog` | KEEP | Called directly by `tcd/collectors.py:68` (`+ watchdog.collect_watchdog()`) — part of the core collector pipeline, zero Sheets/HTML/AppSheet coupling. Has its own offline test suite (`tests/test_tcd_watchdog.py`). |

Entirely KEEP — a genuine collector, explicitly named in the task brief.

---

### `tcd/drive_mirror.py` (111 lines) — real Drive links for local files

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 30-42 | `_load_folder_cache` / `_save_folder_cache` | KEEP | |
| 45-69 | `find_or_create_folder` | KEEP | |
| 72-97 | `find_or_upload` | KEEP | |
| 100-111 | `mirror_file` | KEEP | Called by `tcd/sections.py`'s `collect_intel`/`collect_techscans`, which feed `sections_sync.py` (classified presentation-only/unscheduled above). So the capability is architecturally load-bearing (a Slack message linking an intel report needs exactly this real-Drive-link mechanism, same as the task brief's "Drive mirror" KEEP category), but its only current call path today runs through a component with no live trigger — **dormant-but-correct**, not exercised in production unless someone runs `sections_sync` by hand. |

---

### `tcd/permalink.py` (167 lines) — deep-link builders

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 27-29, 32-39 | `_is_degenerate`, `_humanize_stem` | KEEP | |
| 42-52, 55-60 | `gmail_permalink`, `gmail_search_link` | KEEP | |
| 63-68 | `sms_permalink` | KEEP | |
| 71-76 | `keep_permalink` | KEEP | |
| 79-84 | `drive_search_link` | KEEP | |
| 87-92 | `first_nonempty` | KEEP | |
| 95-137 | `derive_link` | KEEP | Called by `tcd/collectors.py:48` and `tcd/sections.py:222` — every collected item, Sheet-bound or Slack-bound, gets its deep link here. Pure, no Sheets/HTML/AppSheet coupling. |
| 140-167 | `derive_source_path` | KEEP | Same call sites (`collectors.py:49`). |

Entirely KEEP — explicitly named "permalinks" in the task brief, and
"Requirement #1" (every row must link to where it lives, docstring line
4) is exactly as true for a Slack message as an AppSheet row.

---

### `tcd/sms_gateway.py` (157 lines) — Commander's-own-number SMS channel

| Lines | Symbol | Class | Notes |
|---|---|---|---|
| 44-57 | `_load_config` | KEEP | |
| 60-69 | `_client` | KEEP | |
| 72-89 | `send_sms` | KEEP | |
| 92-100 | `send_alert` | KEEP | |
| 103-107 | `get_status` | KEEP | |
| 110-129 | `poll_inbox` | KEEP | |

Entirely KEEP. Used by `tcd/collectors.py` and `tcd/_imports.py` as a
genuine collector/send channel — explicitly documented (lines 1-9) as
"replacing Telegram," independent of and parallel to the Slack decision
board. Note per `CLAUDE.md`'s "Emergency Channels Manual-Arm" doctrine
(memory: [[feedback_emergency_channels_manual_arm_only]]) this still needs
to stay manual-arm-only regardless of what happens to the Sheet/AppSheet
side of the migration.

---

## Direct answers to the team lead's two questions

### 1. What does `tcd-sync.timer` actually do every 10 minutes, and what breaks if the WRITEBACK half stops while the Sheet PUSH half keeps running?

Live unit files, read directly (not from docs):

```
tcd-sync.service: ExecStart=/usr/bin/python3 -m tcd.sheet_sync
tcd-sync.timer:   OnBootSec=2min, OnUnitActiveSec=10min
Status: both active/enabled; last fire ~4 min before this analysis, next in ~5 min.
```

`python -m tcd.sheet_sync` → `main()` (no flags) → `_live_sync()`
(`tcd/sheet_sync.py:88-138`), which does, **in this order**:

1. **Writeback half** (lines 103-116, only if the Sheet already exists and
   `--no-writeback` wasn't passed): calls `writeback.process_once()` —
   diffs the current Sheet against `config/tcd_writeback_state.json`'s
   last-known snapshot, detects anything a human changed directly in
   AppSheet/the raw Sheet since the last pass, and executes the real
   action: cascade-delete (`_handle_dispose`), close+audit
   (`_handle_close`), stage-move+Silver-gate (`_handle_stage_move`),
   D→T auto-task+Silver-front-frame (`_handle_auto_task`), comment
   audit-log + `[CREATE_TASK_REQUESTED]` mission filing (`_handle_comment`
   / `_handle_create_task`). Writes corrected cells straight back
   (`_default_write_fn`).
2. **Push half** (lines 118-131): fresh `collect_rows()` (Gmail, Keep,
   SMS, internal `hale_state.json`, `watchdog.collect_watchdog()` —
   everything `collectors.collect_all()` gathers), then an idempotent full
   `clear()` + `update()` of the `Items` tab. This is the "Sheet PUSH"
   the migration plan wants kept as a read-only mirror.

**If WRITEBACK stops but PUSH keeps running** (i.e. always pass
`--no-writeback`, or just delete the `writeback.process_once()` call at
line 110): the collector→Sheet direction is completely unaffected — the
Sheet keeps refreshing every 10 minutes exactly as before. What stops
working is the *Sheet/AppSheet→action* direction:

- Typing `Delete` or `Closed` into the `status` column directly on the raw
  Google Sheet or in the AppSheet app no longer triggers a real
  cascade-delete or a real audited close — the next push's fresh
  `derive_status()` (from `tcd/staging.py:106`) just silently overwrites
  it back to `Open`/`Reference`, because nothing persisted an override.
- Dragging a card's `stage` P→D→T→C directly in AppSheet no longer
  auto-tasks (D→T) or Silver-gates a move into Certify — same silent
  overwrite on the next push.
- Typing a new comment directly into AppSheet no longer gets logged to
  `hale_decisions.md`, and the `[CREATE_TASK_REQUESTED]` marker no longer
  files a mission.

In short: **AppSheet (and the raw Sheet UI) becomes purely cosmetic** —
edits there have zero durable effect once the next 10-minute push runs.
This is exactly the intended end state *if and only if* every real
Commander/staff action is guaranteed to route through Slack's
`tcd_actions.py` (task #20) calling the `_handle_*` functions + setting
overrides directly (the same pattern `apply_non_sheet_action` already
uses for non-Sheet rows) — **not** through hand-editing the Sheet. Ship
that adapter and cut this timer branch in the same change, not in two
separate steps, or there's a window where AppSheet edits look like they
worked (the UI shows the edit) and then silently vanish 10 minutes later
with no error surfaced anywhere. That exact failure mode is already
documented as having happened once for Close specifically — see
`writeback.py:174-179`'s "2026-07-29 fix" comment (a Close with no
override reverted to Open on the next timer pass) — so this is not a
hypothetical risk, it's a repeat of a bug already caught and fixed once
for one action type.

### 2. Is anything OTHER than writeback consuming the Sheet?

Yes — three things besides the timer's `writeback.process_once()` call
touch this data plane:

1. **`tcd/web.py`** (confirmed LIVE, see the correction section above) —
   reads via `writeback.read_sheet_rows()` + `multi_tab.collect_multi_tab()`
   + `overrides.load_overrides()`, and writes via
   `writeback._default_write_fn()` + `writeback.process_once(actor="commander")`
   / `writeback.apply_non_sheet_action()`. This is itself a second trigger
   of the exact same writeback machinery, just fired on-demand by an HTTP
   POST instead of by the timer.
2. **`tcd/mcp_tools.py`'s `tcd_process_writeback` tool** (confirmed LIVE
   via `thunderbird-mcp.service`) — a third, independent on-demand trigger
   of `writeback.process_once()`, reachable from any MCP client (Claude,
   Antigravity/AG) with no relationship to the timer or the web board.
3. **`tcd/sections_sync.py`** writes to separate tabs (`Intel`,
   `TechScans`, `Next7`) on the *same* spreadsheet — but nothing reads
   these back for actions; they're one-way collector→Sheet, explicitly
   for external dashboard consumption (Looker Studio, per its own
   docstring), and — separately — this script has no live scheduler at
   all today (grep found no timer/cron/service referencing it).
4. **The raw Google Sheet / AppSheet app itself**, if a human opens either
   directly — the entire reason `process_once`'s diff loop exists is to
   catch hand-edits made there. Code comments throughout `web.py` and
   `writeback.py` describe AppSheet in the present tense ("the same Sheet
   AppSheet already uses"); this analysis could not independently confirm
   from the repo alone whether the AppSheet mobile/web app is still
   actively used by anyone day-to-day — flag for direct Commander
   confirmation before assuming that door is already closed.

Also worth noting: `tcd/multi_tab.py` reads a **second, separate
spreadsheet** (id `1L7WWppZ7LB9Is5EUBp9zu6FThPghcyuGuB4IEQtYsUQ`) that has
nothing to do with `config/tcd_sheet_config.json`'s "Items" sheet at all —
a distinct data plane the retirement plan needs to account for separately
(see the `multi_tab.py` section above).

---

## Summary count

Counted at function/tool granularity (73 functions/tools total across the
11 files), plus the module-level flag on `tcd/web.py` itself:

| Class | Count | Files |
|---|---|---|
| **KEEP-LOAD-BEARING** | 55 | writeback.py (16 of 18), sheet_sync.py (6 of 7, excl. the 1 MIXED), staging.py (3), mcp_tools.py (2 of 3), watchdog.py (7), drive_mirror.py (5), permalink.py (10), sms_gateway.py (6) |
| **PRESENTATION-ONLY** | 17 | web.py (7, entire module — but see correction: this is a *live* surface, not dead debris), writeback.py (2: `_default_write_fn`, `process_once`'s diff shell), multi_tab.py (1, contingent on second-spreadsheet decision), sections_sync.py (6, and already unscheduled today), mcp_tools.py (1: `tcd_process_writeback`) |
| **MIXED** (split within one function) | 1 | sheet_sync.py `_live_sync` — push half KEEP, writeback-call half PRES; already separable via the existing `--no-writeback` flag, no new code needed |
| **ALREADY-DEAD** (unreachable today) | 0 | Nothing found is *currently* unreachable. The nearest candidate, `tcd/multi_tab.py`, is reachable today only through the live `tcd/web.py` route and goes dead the moment that board is retired — a consequence of this migration, not a pre-existing fact. |

**Net effect of the finding on the migration plan:** the "AppSheet
writeback polling" this task set out to retire (task #23) is not one
thing to switch off — it is `writeback.process_once`'s diff-detection
shell plus `_default_write_fn`, currently reachable from **three**
independent live triggers (`tcd-sync.timer`, `tcd/web.py`'s
`tcd.d2mluxury.quest` board, and the `tcd_process_writeback` MCP tool),
and it cannot be safely cut until `core/comms/tcd_actions.py` (task #20)
is calling the KEEP handlers directly for every action type Slack needs
to support. `tcd/web.py` itself additionally needs an explicit,
deliberate retirement step (not just non-use) because it is a live
competing write surface today, restored by Commander directive on
2026-07-28 — one week before this task — which should be called out to
the Commander directly given how recently and deliberately it was turned
back on.

No source file was created, edited, deleted, or stubbed in the course of
this analysis. This file is the only one written or modified.
