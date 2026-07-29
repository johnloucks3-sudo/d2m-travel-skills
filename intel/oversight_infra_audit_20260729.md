# Oversight / Delegation Infrastructure Audit — 2026-07-29

Scope: every component named in the tasking, plus what grep turned up around them. All claims below are grounded in file reads, grep call-site counts, `sqlite3 .schema`, live file sizes/timestamps, and a real `pytest` run — not docstrings. Where a claim rests only on a docstring, that is stated explicitly.

---

## 1. Component Inventory

| Component | Path | Lines | Data store | Real callers (non-test)? | Status |
|---|---|---|---|---|---|
| Delegation outcomes ledger | `core/staffing/delegation_outcomes.py` | 281 | `OpsCenter/delegation_outcomes.jsonl` (append-only, fcntl-locked) | Yes — `dispatch_oc.py`, `reconcile_oc.py`, `delegation_wiring.py`, `integrity_check.py`, `wing_ops_report.py` | **LIVE, new today** |
| CC integrity double-check | `core/staffing/integrity_check.py` | 224 | writes into delegation_outcomes.jsonl via `verify_and_record` | `verify_and_record()`: **ZERO** (tests only). `cc_integrity_double_check()`: none either. | **THEATER** — code correct, unused |
| Staff Summary Sheet (USAF model) | `core/staffing/staff_summary_sheet.py` | 819 | lives inline in `mission_board.json` mission dicts; writes to `OpsCenter/silver_ledger.jsonl` + `hale_decisions.md` via gate/wiring calls | Yes — `mission_board_sync.py` (`cmd_sss_*`), `sss_render.py`, `comms/thunderbird_sss.py`, `scripts/send_35_item_surge_report.py` | **LIVE** |
| Directive ledger | `core/staffing/directive_ledger.py` | 148 | `OpsCenter/mandatory_directives.jsonl` | `must_haves_must_dos()`: yes, from `hooks/plan_mode_mandates.py`. `capture()`: **ZERO callers anywhere** | **HALF-THEATER** (see §3) |
| Task delegation router | `core/relay/task_delegation.py` | 208 | none (pure function) | Yes, heavily — `slot_router.py`, `multi_brain_router.py`, `email_task_ingest.py`, `nexus.py`, `crew_runner.py`, `delegation_wiring.py`, `delegation_preflight.py` | **LIVE** |
| Delegation preflight | `core/relay/delegation_preflight.py` | 60 | none | **ZERO callers anywhere** | **DEAD** |
| Delegation wiring (certify/mirror) | `core/relay/delegation_wiring.py` | 307 | mirrors to C2 Fabric bus (`core/hale_bus/c2_fabric_write.py`) + delegation_outcomes.jsonl | Yes — `certify_mission_and_record()` is the real gate inside `mission_board_sync.py::cmd_complete()` | **LIVE** |
| Contact AG (Gemini) | `core/relay/contact_ag.py` | 219 | logs full prompt+stdout+stderr to `OpsCenter/collaboration/routing_log.md` | Yes — `integrity_check.py`, `dispatch_oc.py`, `task_templates.py`, `scripts/execute_60_item_4wave_surge.py`, `core/relay/deepseek_claude_code.py`, `ag_test.py`, `core/ai_infra/c2_subcommander_harness.py` | **LIVE** |
| Dispatch to OC (async ticket) | `core/relay/dispatch_oc.py` | 65 | writes to the real `core.hale_bus.brain_bridge.BrainBridge` board (same one `scripts/oc_worker.py` polls) | `dispatch_to_oc()`: **ZERO callers anywhere** | **DEAD** (correctly wired, never invoked) |
| Reconcile OC | `core/relay/reconcile_oc.py` | 151 | reads delegation_outcomes.jsonl + BrainBridge | Yes — `core/ops/evening_consolidated_eod_engine.py:453` (`reconcile_due()`) | **LIVE** |
| Task templates (spec builders) | `core/relay/task_templates.py` | 127 | none | **ZERO callers anywhere** | **DEAD** |
| Silver gate (front/back) | `core/silver/gate.py` | 376 | `OpsCenter/silver_ledger.jsonl` (3,114 lines, 728KB, last write today 16:03 MDT — minutes-apart cadence) + mirrors into `hale_decisions.md` | Yes, extremely — `delegation_wiring.py`, `staff_summary_sheet.py`, `delegation_outcomes.py`, `task_templates.py`, `reconcile_oc.py`, `tcd/writeback.py`, `OpsCenter/hale_morning_brief.py`, `.claude/hooks/hale_orchestrator_backstop.py`, `scripts/silver_gate.py` (CLI shim) | **LIVE — the most mature component in this audit** |
| Silver scorecard | `core/silver/scorecard.py` | small | `OpsCenter/collaboration/seat_scorecard.jsonl` (87 lines, last write today) | Yes — called from `delegation_wiring.py`, `staff_summary_sheet.py`, `integrity_check.py` on PASS | **LIVE** |
| Wing page (paging lane) | `core/comms/wing_page.py` | exists, confirmed | — | Yes — `gate.py::_page_hold()`, `delegation_outcomes.py::page_commander()`, `delegation_wiring.py` | **LIVE** |
| Wing ops daily digest | `core/ops/wing_ops_report.py` | 118 | reads delegation_outcomes rollup + scorecard | Yes — wired into **both** `morning_consolidated_brief_engine.py:191` and `evening_consolidated_eod_engine.py:463` | **LIVE, new today** |
| Morning/Evening brief engines | `core/ops/morning_consolidated_brief_engine.py` (346), `core/ops/evening_consolidated_eod_engine.py` (585) | — | HTML email via wing send | call `wing_ops_report`, evening also calls `reconcile_oc.reconcile_due()` | **LIVE** |
| OC worker (real) | `scripts/oc_worker.py` | 250 | `core.hale_bus.brain_bridge.BrainBridge`; status file; `dispatch_claude.py` for actual model calls | systemd `opencode-worker.service` (confirmed active) | **LIVE** |
| OC worker (decoy) | `scripts/opencode_worker.py` | n/a | imports nonexistent `brain_bridge` module at repo root → `ImportError` | none load-bearing | **DEAD**, documented as dead in 3 other files' docstrings |
| Mission board sync | `OpsCenter/mission_board_sync.py` | 865 | `OpsCenter/mission_board.json` (198 missions: 69 pending_review, 30 in_progress, 28 completed, 27 active, 4 closed, 40 cancelled; `last_updated` 2026-07-27) | CLI (`EXEC:` commands), imported by many | **LIVE** |
| Nexus daemon | `OpsCenter/nexus.py` | 1,127 | `OpsCenter/mission_board.json`, `logs/nexus_audit.log` | systemd, `route_and_dispatch` | **LIVE** — separate dispatch path from oc_worker/BrainBridge (Poe/OpenCode/Claude routing for the older mission-board flow) |
| PreToolUse policy gate | `hooks/pretooluse_policy.py` | 228 | `logs/policy_audit.jsonl` | Claude Code hook, fail-closed | **LIVE** |
| PostToolUse audit logger | `hooks/posttooluse_audit.py` | 147 | `logs/policy_audit.jsonl` (81,675 lines, 20.5MB, last write this session) | Claude Code hook | **LIVE — heaviest-volume log in the whole audit** |
| Plan-mode mandate hook | `hooks/plan_mode_mandates.py` | 39 | reads `directive_ledger.must_haves_must_dos()` | `ExitPlanMode` PreToolUse hook | **LIVE (read side only — see §3)** |
| TCD data plane | `tcd/*.py` (14 files, 3,146 lines total: `writeback.py` 595, `web.py` 411, `collectors.py` 266, `sections.py` 255, etc.) | — | Sheets/Keep/Drive/Calendar via `tcd/writeback.py`, `tcd/sheet_sync.py` | Retained per CLAUDE.md (web app retired, data plane kept) | **LIVE data plane**, `writeback.py` calls into `silver.gate` |
| `router_cost.db` | `core/ai_infra/data/router_cost.db` | — | SQLite, 1 table: `pools(name, consumed, soft_limit, hard_limit, updated_ts)` | budget tracking only | **Narrow** — cost pools, not task/oversight data |

---

## 2. Full-content findings on the 6 "shipped" cross-Hale oversight functions

Read in full (not grepped): `dispatch_oc.py`, `task_delegation.py`, `contact_ag.py`, `integrity_check.py`, `delegation_wiring.py`, `directive_ledger.py`, `task_templates.py`, `delegation_outcomes.py`, `gate.py`. Key points that matter for the gap analysis:

- **`verify_and_record()` (integrity_check.py)** is the single named enforcement point in CLAUDE.md's "CC INTEGRITY DOUBLE-CHECK" hard rule. Grep for `verify_and_record(` outside its own definition and outside `tests/test_delegation_outcomes.py` returns **nothing**. Nothing in the live system calls it before a "done" claim. The rule is written down; the code path is not exercised in production.
- **`dispatch_to_oc()` (dispatch_oc.py)** correctly targets the *real* BrainBridge board (`core.hale_bus.brain_bridge.BrainBridge`, the same one `scripts/oc_worker.py`'s systemd-run poll loop claims from) — it is not misdirected at the dead `opencode_worker.py`/`brain_bridge` module. It is simply never called.
- **`check_before_self_execute()` (delegation_preflight.py)** has zero callers, including zero test callers (no `tests/test_*preflight*` file exists at all).
- **`directive_ledger.capture()`** has zero callers anywhere in the repo, including in the very hook (`plan_mode_mandates.py`) whose docstring says it's "driven by" the ledger — that hook only reads (`must_haves_must_dos()`), never writes. `OpsCenter/mandatory_directives.jsonl` has exactly 12 lines, all timestamped 2026-07-19T12:51, i.e. one historical batch capture, frozen for **10 days** as of today. Any Commander directive issued since 2026-07-19 has **not** entered this ledger and will not be bound to future Staff Summary Sheets or surfaced in a plan-mode mandate check. This is a 4th zero-caller function the same class as the other three — not previously flagged in this session's own internal audit ticket (`OPUS-REVIEW-20260729`, which counted only 3: verify_and_record, dispatch_to_oc, check_before_self_execute).
- **`task_templates.py`**'s three builders (`build_ag_task`, `build_oc_task`, `build_flash_task`) also have zero callers, despite CLAUDE.md's "Tasking clarity" section naming them as the required way to build specs.

**Self-correcting counter-evidence found in the data, not asserted by me:** `OpsCenter/delegation_outcomes.jsonl` (4 lines total — this ledger was born today) already contains a `reconciliation` row from earlier today where **CC itself caught 3 of these zero-caller functions** via an Opus review (`OPUS-REVIEW-20260729`) and a separate row where CC caught **AG** citing zero real URLs on a research ask (`AG-RESEARCH-20260729`, verdict `DISCREPANCY`). That is the compliance loop working exactly once, today, on the day it was built — informative for "how mature is this," not proof it runs going forward.

**What still works despite the above:** `staff_summary_sheet.py::close_sss()` binds mandates via `directive_ledger.active_gate_keys()` at *open* time (line ~228), and that function reads whatever is currently in the 12-line ledger fresh each call. So the two mandates captured on 7/19 (`cross_hale`, `silver`) **are** still enforced on every new sheet today — the gap is narrower than "the whole mechanism is dead": it's specifically "no NEW mandate issued after 7/19 gets captured."

---

## 3. Dead code / zero-caller list (confirmed by grep with parens, not just filename mentions)

| Function | File | Evidence |
|---|---|---|
| `check_before_self_execute()` | `core/relay/delegation_preflight.py` | 0 call sites, 0 tests |
| `dispatch_to_oc()` | `core/relay/dispatch_oc.py` | 0 call sites outside own file |
| `verify_and_record()` | `core/staffing/integrity_check.py` | 0 call sites outside `tests/test_delegation_outcomes.py` |
| `directive_ledger.capture()` | `core/staffing/directive_ledger.py` | 0 call sites anywhere, including the hook that documents it |
| `build_ag_task()`, `build_oc_task()`, `build_flash_task()` | `core/relay/task_templates.py` | 0 call sites anywhere |
| `scripts/opencode_worker.py` | — | imports nonexistent `brain_bridge` at repo root → `ImportError` on load; documented as dead in 3 separate files' docstrings (dispatch_oc.py, task_templates.py) |

**Test coverage check (ground truth, not claimed):** ran `pytest tests/test_delegation_outcomes.py tests/test_delegation_wiring.py tests/test_staff_summary_sheet.py -q` → **50 passed in 0.13s**. The wired components (delegation_outcomes, delegation_wiring, staff_summary_sheet) are genuinely tested and passing. There is no `tests/test_delegation_preflight.py`, `tests/test_dispatch_oc.py`, or `tests/test_task_templates.py` — the untested modules are exactly the dead ones.

---

## 4. Existing data stores that could feed a dashboard

| Store | Path | Format/schema | Size / freshness | Content |
|---|---|---|---|---|
| Delegation outcomes | `OpsCenter/delegation_outcomes.jsonl` | JSONL, `Outcome` dataclass: `ts, seat, action, verdict, ticket_id, task_type, dispatch_mode, discrepancy_detail, certified_by, verified_by, follow_up_due, reconciled, self_execute_rationale, routing_recommendation` | 4 lines, born today 09:48–15:48 | delegation/self-exec/integrity/certification/reconciliation events |
| Silver ledger | `OpsCenter/silver_ledger.jsonl` | JSONL, `Verdict` dataclass: `stage(front/back), mission_id, work_product, verdict(PASS/HOLD), checks_run[], holds[], ts` | **3,114 lines, 728KB**, last write today 16:03 MDT, ~2–3 min cadence | Every front-frame + back-gate check the Wing has run — by far the most complete audit trail in the system |
| Seat scorecard | `OpsCenter/collaboration/seat_scorecard.jsonl` | JSONL: `seat, task_type, category, traits_observed[], outcome, ref, date` | 87 lines, last write today | Per-seat pass/fail evidence for SSS/certification work |
| Mandatory directives | `OpsCenter/mandatory_directives.jsonl` | JSONL: `text, source, gates[], mandatory, ts` | 12 lines, frozen since 2026-07-19 | Commander directive capture (write path dead — see §3) |
| Mission board | `OpsCenter/mission_board.json` | dict: `active_missions[], suspended_missions[], completed_missions[], missions[], last_updated, suspense_watch[]` | 198 missions total, last_updated 2026-07-27 | The canonical task list; SSS sheets and delegation tickets live inline as mission dicts |
| Routing log | `OpsCenter/collaboration/routing_log.md` | Markdown, timestamped blocks with full prompt + stdout + stderr per AG contact | 26,073 lines | The only place a full agent-to-agent *transcript* (not just a verdict) is durably kept — but only for AG contacts, not OC |
| Policy audit log | `logs/policy_audit.jsonl` | JSONL: `ts, tool, decision, rule_id, excerpt, session` | **81,675 lines, 20.5MB**, live (last line is this session's own tool call) | Every tool call, allowed or blocked, across the whole Claude Code harness — the highest-volume log in the system, but generic (no task/ticket linkage) |
| Router cost DB | `core/ai_infra/data/router_cost.db` | SQLite, 1 table `pools(name, consumed, soft_limit, hard_limit, updated_ts)` | small | Budget-pool consumption only, not task outcomes |
| `hale_decisions.md` | repo root | Markdown, human-readable, mirrors both Silver and Wing-Ops lines | — | The one human-facing rollup that already interleaves gate verdicts + delegation outcomes |

---

## 5. Gap Analysis

| Requirement | What exists | What's missing | Severity |
|---|---|---|---|
| Visibility into all phases of a delegation | `delegation_wiring.py` mirrors `proposed→assigned→in_progress→pending_review→done/blocked` onto the C2 Fabric bus (`console` channel, filterable by `ref=mission_id`); SSS has the same 6-stage lifecycle | No single query/view stitches bus + delegation_outcomes.jsonl + silver_ledger.jsonl + routing_log.md into one per-ticket timeline. Each is queryable separately; nothing joins them | **Medium** |
| Artifacts of planned delegations (spec/plan BEFORE work starts) | `silver_front_frame()` requires checkable acceptance criteria + named ground-truth source before a ticket/sheet opens; `task_templates.py` designed for this but **unused** | The actual per-engine tasking spec (what prompt/steps were sent) is not durably captured except for AG (via routing_log.md). OC dispatch (`dispatch_to_oc`) never fires, so no OC-side pre-work artifact exists yet | **High** — the building blocks exist unwired |
| Interaction between agents/models (actual messages exchanged) | `contact_ag.py` durably logs full prompt+stdout+stderr to `routing_log.md` for every AG contact (26k lines, real) | **No equivalent for OC.** `scripts/oc_worker.py` writes only a status file + truncated 80-char result strings; no full transcript is kept. CC-self-execution has zero transcript capture beyond the harness's own `posttooluse_audit.py` excerpts (first 100 chars only) | **High** |
| Assessment of results | `certify_mission_and_record()`, `verify_and_record()`, `run_gate()` all produce PASS/HOLD/BLOCKED verdicts with reasons | `verify_and_record()` (the cross-engine claim-checker) has **zero production callers** — assessments happen only for delegated-ticket certification, not for CC's own "done" claims, which is the exact gap the Commander's 2026-07-19 directive was written to close | **Critical** — the rule exists, the enforcement doesn't |
| Problems / failures | `delegation_outcomes.py` VERDICTS include DISCREPANCY/UNVERIFIED/BLOCKED/DROPPED/STALLED/FAILED; `page_commander()` pages in real time on any failure verdict | Only 4 rows exist total (system born today) — no track record yet to judge whether paging actually fires reliably in steady state | **Medium** (mechanism sound, unproven over time) |
| Lost taskings (vanished) | `outstanding()` in delegation_outcomes.py detects OC tickets past `follow_up_due` with no reconciliation; `reconcile_oc.reconcile_due()` wired into the evening brief | This only covers tickets dispatched **through `dispatch_to_oc()`**, which nothing calls. Zero dispatches → zero possible "outstanding" detections. Separately, `mission_board_sync.py` has no stale/orphan/abandoned detection of its own (`suspense_watch` only tracks IDs with a set date, doesn't scan for overdue); overdue detection lives in a *different*, unaudited pair of scripts (`scripts/hale_heartbeat_scan.py`, `core/watchtower/thunderbird_heartbeat.py`) not wired to delegation_outcomes at all | **High** — real detection code exists but the pipe fed into it is dry |
| Exits from tasking NOT accomplished (silent abandonment) | `_opr_failed()` in staff_summary_sheet.py detects an OPR's own `nonconcur`; `close_sss()` blocks (never silently backstops) on a failed OPR; `block_sss()` exists for honest failure | Detection is manual/self-reported (OPR has to log a `nonconcur`) — nothing automatically flags "OPR went silent and nothing happened" the way `outstanding()` does for OC, and that path is unused (see above) | **High** |
| Successful taskings + their outputs | `certify_mission_and_record()` requires a `verification_artifact` (a real path/commit/URL) before PASS; Silver's `run_gate()` checks the artifact itself, not just the claim | No index of "here are this week's completed artifacts" — you'd have to grep silver_ledger.jsonl by mission_id manually | **Low-Medium** |
| Progress bars / timers / live todo lists | `scripts/oc_worker.py` writes a live status file (`state: running/busy/idle`, `current_task`, `cycles`); `nexus.py` has queue depth counters | No aggregated cross-seat live view — CC's own in-flight work has no equivalent status file; nothing surfaces "3 tickets in flight, 1 stalled" as a single glance | **Medium** |
| Accountability when an agent fails | `page_commander()`, Silver's `_page_hold()`, `certify_mission_and_record()`'s BLOCKED path, `rollup_stats()`'s `self_execute_unjustified` counter | All of this is genuinely wired **for delegated tickets**. For CC's own self-executed "done" claims — the thing the 2026-07-18 incident was actually about — the enforcement function (`verify_and_record`) is never invoked | **Critical** |
| Regular brutal appraisal of effectiveness | `wing_ops_report.build_wing_ops_digest()` is wired into **both** daily brief engines and renders pass/fail/redo counts + per-seat budget + a green/no-discrepancies line | Digest is only as honest as the 4-row ledger feeding it; with near-zero history it will read "green" by default (silence, not verified absence of problems) — same failure mode this session's own Opus review flagged for a different metric | **Medium** — mechanically sound, data-starved |

---

## 6. Ten highest-leverage fixes

1. **Wire `verify_and_record()` into the actual completion path** — the single highest-value fix. Either (a) add a PreToolUse/Stop hook that calls it automatically before any "done"/"complete" self-report, or (b) make `certify_mission_and_record()` / `close_sss()` require a `verify_and_record()` call for CC-self-executed work the same way they already require cross-seat certification for delegated work. Today the hard rule in CLAUDE.md and the code are disconnected.
2. **Give `directive_ledger.capture()` a real caller.** Simplest: hook it into the same place `must_haves_must_dos()` is read from, or into session-start/PreToolUse so every Commander message this session gets captured live, not just the one 2026-07-19 batch.
3. **Make OC dispatch produce a transcript, not just a truncated result string.** `scripts/oc_worker.py::_extract_result()` keeps only 300 chars; there is no `routing_log.md`-equivalent for OC. This is the biggest "interaction visibility" gap and the cheapest to close (mirror `contact_ag.py`'s log-append pattern).
4. **Either delete or actually call `dispatch_to_oc()`, `check_before_self_execute()`, `task_templates.py`'s three builders.** Right now they are attractive nuisances — CLAUDE.md tells future sessions to use them, nobody does, and that gap itself becomes a recurring audit finding (as it did in this session's own `OPUS-REVIEW-20260729` ticket). Pick one: wire them in or remove the standing-order text that claims they're used.
5. **Add an automatic "OPR went silent" detector**, not just the self-reported `nonconcur` path — a scheduled check on any `in_progress`/`assigned` SSS or mission past its `suspense_date` with no log update, feeding the same `outstanding()`/`page_commander()` machinery already built for OC tickets.
6. **Join `mission_board.json` + delegation_outcomes.jsonl + silver_ledger.jsonl + routing_log.md by `ticket_id`/`mission_id`** into one queryable per-ticket timeline. All four already share an ID scheme; nothing currently stitches them.
7. **Wire the existing heartbeat/watchdog scripts (`scripts/hale_heartbeat_scan.py`, `core/watchtower/thunderbird_heartbeat.py`) into `delegation_outcomes.record_outcome()`** so overdue-mission detection (which already exists, separately) produces the same durable, dashboard-queryable row as every other failure mode instead of its own side channel.
8. **Add a CC-side live status file**, mirroring `scripts/oc_worker.py`'s `write_status()` pattern, so "what is CC doing right now" is machine-readable the same way OC's state already is.
9. **Backfill or accept the data-starvation problem honestly in the digest itself** — `wing_ops_report.py` already shows `⚠STALE`; extend that convention so a "0 discrepancies" line explicitly distinguishes "checked and clean" from "nothing was checked" (the same failure this session already caught for a different subsystem — silence read as green).
10. **Add missing test coverage exactly where the code is dead**: `tests/test_delegation_preflight.py`, `tests/test_dispatch_oc.py`, `tests/test_task_templates.py` don't exist. Writing them would either (a) surface real wiring the moment they're wired in, or (b) make the "never called" status an explicit, tracked fact instead of something an auditor has to rediscover by grep each time.

---

*Audit method: file reads (full-content for all core files under 900 lines), `grep -rn` call-site verification (parenthesized calls only, distinguishing real invocation from docstring mention), live `sqlite3 .schema`, live file `ls -la`/`wc -l`/`tail` on every JSONL/log claimed as a data store, `systemctl --user list-units/list-timers`, and one real `pytest` run (50/50 passed). No code was modified.*
