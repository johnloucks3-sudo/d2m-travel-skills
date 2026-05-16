# OpenCode Memory — Session 2026-05-16 (evening)

## Headless Dispatch Fix — dispatch_opencode.py

**Problem:** Shell-based `opencode run` dispatch failed. `--cwd` is invalid (should be `--dir`), and `${}` template vars in `$prompt` expanded to empty strings → no positional arg → help screen.

**Fix:** Created `OpsCenter/dispatch_opencode.py` — Python subprocess wrapper that builds clean arg vectors. No shell interpolation issues. Supports `--prompt`/`--prompt-file`, `--foreground` (with NDJSON text extraction), and background mode. Model auto-fallback chain: big-pickle → deepseek-v4-flash-free → gemini-2.5-flash.

**Rule established for all wing:** NEVER call `opencode run` or `claude -p` directly from shell. ALL headless dispatch goes through `dispatch_opencode.py` or `dispatch_claude.py`.

**Other P1 items closed this session:**
- 30s JS auto-refresh on cost dashboard (meta refresh + timestamp display)
- hale_shared_state.jsonl created at OpsCenter/hale_shared_state.jsonl (Option A confirmed)
- /api/claude/models JSON endpoint added for Telegram /costs
- Handshake write-on-open (ONLINE packet) and write-on-close (EOD) now standard practice

**Key files touched:**
- `OpsCenter/dispatch_opencode.py` — created
- `core/cost_dashboard/templates/index.html` — auto-refresh
- `core/cost_dashboard/app.py` — /api/claude/models endpoint
- `OpsCenter/hale_shared_state.jsonl` — created
- `OpsCenter/hale_handshake.jsonl` — ONLINE + EOD entries
- `OpsCenter/collaboration/wing_comms.md` — P1 closeout + headless dispatch education
- `OpsCenter/collaboration/claude_inbox.md` — stale BRAVO task marked COMPLETE

**BRAVO still owns:** B3 (claude_windows), handshake read-on-open in BRAVO instance, `/costs` Telegram command

---

# OpenCode Memory — Session 2026-05-16

## P1 Closeout — 3/3 ALPHA-owned items closed

**Read BRAVO's init (HALE_BRAVO_INIT.md).** Full staff engagement lifecycle (BEFORE/DURING/AFTER) with tiered classification (T0-T3), pipeline routing, and hotwash/artifact enforcement.

**Delivered:**
1. **30s JS auto-refresh** on cost dashboard (`core/cost_dashboard/templates/index.html`) — meta refresh + timestamp display
2. **hale_shared_state.jsonl** (`OpsCenter/hale_shared_state.jsonl`) — Option A confirmed, initial entry written, both instances append
3. **`/api/claude/models`** JSON endpoint added to `core/cost_dashboard/app.py` — model breakdown for Telegram `/costs` command
4. **ONLINE + EOD handshake packets** written this session (handshake write-on-open/close now operational)

**Key files touched:**
- `core/cost_dashboard/templates/index.html` — auto-refresh
- `core/cost_dashboard/app.py` — /api/claude/models endpoint
- `OpsCenter/hale_shared_state.jsonl` — created
- `OpsCenter/hale_handshake.jsonl` — ONLINE + EOD entries
- `OpsCenter/collaboration/wing_comms.md` — P1 closeout posted

**Outstanding (BRAVO):**
- B3 claude_windows population (blocks `/costs` Telegram command)
- ACK organizational directive
- Handshake read-on-open in BRAVO instance
- `/costs` Telegram command in HALE-YODA

**BRAVO's P1 that was already done:** `/api/summary` endpoint existed in app.py before this session.

---

# OpenCode Memory — Session 2026-04-07

## Claude Tasking Procedure Documentation

### **Successful Tasking Method (Confirmed Working)**
1. **File:** `/home/john/Thunderbird/claude_inbox.md` (Canonical Claude inbox)
2. **Format:** 
   ```markdown
   ---
   ## TASK: UNIQUE-ID
   status: UNREAD
   from: OpenCode
   injected: YYYY-MM-DD HH:MM MT
   priority: P1
   task: |
     <task description>
     Write result to /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
   ```

3. **Watcher Response:**
   - Watcher (`d2m-tasking-watcher.service`) detects `^status: UNREAD` via inotify
   - Spawns `claude -p` headless process with stripped OAuth env vars
   - Result written to `claude_outbox.md`
   - Task marked as `COMPLETE` in `claude_inbox.md`

### **Timeline of Today's Tasking**
- **08:00 MT:** First architecture review task added to `claude_inbox.md`
- **08:02 MT:** Task marked UNREAD → watcher triggered
- **08:21 MT:** Review complete in `claude_outbox.md` (LIFECYCLE-ARCHITECTURE-REVIEW-001)
- **Task execution time:** ~19 minutes for comprehensive architecture review

### **Learnings:**
1. **Canonical inbox works:** `claude_inbox.md` is correct file for tasking Claude
2. **Watcher is reliable:** Detects UNREAD status and spawns Claude headless
3. **OAuth caching works:** `OpsCenter/.claude_oauth_cache` provides session token
4. **Cross-agent routing:** Claude writes to `opencode_inbox.md` with UNREAD status for watcher loop-back

### **Current Issue:**
Second task (ARCHITECTURE-SCHEMATICS-REVIEW-001) added at 11:42 MT still UNREAD. Possible causes:
- Watcher service hiccup
- OAuth token expired (cache from 11:28 MT)
- Inotify not detecting new append

### **Workflow Verified:**
OpenCode → `claude_inbox.md` → Watcher → Claude Code → `claude_outbox.md` + `opencode_inbox.md` → Mission Board

### **Standing Recommendation:**
- Use async method for non-urgent tasks (allows parallel processing)
- For immediate results, consider direct `claude -p` with env var stripping
- Always verify task appears in inbox with UNREAD status
- Check watcher logs if delay > 5 minutes

---

## Architecture Development Summary

### **Completed Today:**
1. **Document Analysis:** 4 source documents unpacked and analyzed
2. **Consolidated Architecture:** 6-phase lifecycle designed with automation triggers
3. **Claude Review:** Architecture review completed with 9/10 rating
4. **Client Integration:** Ingestion system and orbiting tasks construct designed

### **Next Steps:**
1. Implement client ingestion system for existing dossier integration
2. Build orbiting tasks visualization for completed/pending/future tasks
3. Add missing components identified in review (Phase 1/6, crew assignments, etc.)
4. Deploy in 4 phases rather than 6-week monolithic approach

### **Critical Gaps Identified:**
- Phase 1 "Dream Session" trigger
- Phase 6 "Return" feedback loop  
- Exception escalation trees
- Insurance/visa/medical gates
- Crew assignments with SLAs

### **Integration Points:**
- Existing `client_lifecycle_chart.py` provides base for visualization
- Dossiers have consistent metadata for phase determination
- `thunderbird_anchor_dates.py` already handles date calculations
- Form system needs expansion from 1 → 5 forms

---

**Last Updated:** 2026-04-07 11:45 MT
**Session Duration:** ~3 hours
**Key Achievement:** Validated cross-agent tasking workflow with comprehensive architecture review
## Task Delegation Oversight Model (2026-04-07)

**Pattern:** Cross-inbox verification for Claude task delegation
- **Step 1:** Check `claude_outbox.md` for previous completion status
- **Step 2:** Check `opencode_inbox.md` for cross-agent coordination  
- **Step 3:** Verify task appears in `claude_inbox.md` with UNREAD status
- **Step 4:** Monitor watcher service status (`systemctl --user status d2m-tasking-watcher.service`)
- **Step 5:** Continuously check both outboxes for completion signals
- **Step 6:** Verify mission board updates

**Critical:** Always check BOTH outboxes - Claude writes to both for redundancy

## 2026-04-10 — Hale Self-Oversight Implementation

**Commander Directive:** "HALE to now oversee her transformation"

**Implementation Complete:**
1. **Enhanced hale_cos.md** — Added Layer 8.5: Self-Governance & Transformation Oversight
2. **Expanded enforcement protocols** — 3 new friction scenarios for self-correction
3. **Updated enforcement philosophy** — Self-oversight, continuous improvement, accountability
4. **Implementation systems:**
   - `hale_transformation_tracker.json` — Transformation status tracking
   - Enhanced `hale_state.json` — Transformation oversight state tracking
   - Updated `hale_brief.md` — Transformation status reporting
5. **Oversight tasks created** (opencode_inbox.md):
   - HALE-TRANSFORMATION-OVERSIGHT-001 — Escalate stalled Phase 2 review
   - HALE-TRANSFORMATION-PHASE3-PLANNING — Start Phase 3 pre-work
   - HALE-DAILY-TRANSFORMATION-AUDIT — Implement daily audit protocol

**Core Philosophy:** Hale now enforces standards on herself first and hardest. She owns her transformation evolution as her #1 priority.

**Status:** Hale transformation oversight protocol active. Awaiting Commander review of Phase 2.

---

## 2026-05-12 — HALE Autonomy Framework v1.1 + ETB Execution (ELON)

**SOP-ELON-001 executed. All ETBs complete.**

### HALE Autonomy Framework — LIVE
- **Instructions.md** (v1.1 Autonomy Edition): `/home/john/Thunderbird/OpsCenter/Instructions.md`
- **Authority Level:** FULL AUTONOMY — all areas except external client sends
- **Logging Protocol:** Three channels — Telegram (real-time) + Gmail (daily summary) + R2 (persistent)
- **EARA spreadsheet:** 1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU (never rename/restructure)

### n8n Workflows Deployed (ETB 001 + SOP P3)
- **d2m-wf-gmail-claude-trigger** (ID: pl1M5NRh4uofPpdf) — ACTIVE: Gmail→AI trigger, polls 5 min, logs to R2
  - Filter: label:d2m-ai-process is:unread
  - API: https://api.d2mluxury.quest/api/ai/query
  - R2 credential: cloudflareR2Api (needs configuration in n8n admin)
- **d2m-wf-elon-task-webhook** (ID: 6U3tz0RFwMLI4lPh) — ACTIVE: HALE→ELON async channel
  - URL: https://n8n.d2mluxury.quest/webhook/elon-task
  - Auth: Bearer ***REMOVED-SECRET***
  - On receive: writes to claude_inbox.md + Telegram alert

### Infrastructure Fixed
- n8n restart loop fixed: `scripts/n8n_webhook_reinit.sh` — removed `set -e`, made API calls non-fatal
- Telegram C2: started `thunderbird-telegram-c2.service` (was inactive)
- Tailscale MCP (ETB 002): `thunderbird-mcp-tailscale.service` — ACTIVE port 8768

### Pending (Commander action required)
- Anthropic API key refresh: console.anthropic.com → update ANTHROPIC_API_KEY in ~/.env
- Cloudflare R2 credentials: configure "cloudflareR2Api" in n8n admin → d2m-claude-sync bucket
- Gmail label: create "d2m-ai-process" label in Gmail for ETB 001 trigger

**Updated:** 2026-05-12 15:45 MT by ELON (Claude Code)


## STANDING ORDER 2026-05-07 — SESSION OUTPUT PROTOCOL
1. Always display D2M Logo path: `/home/john/Thunderbird/media/Agency_Logo_Enhanced.png`
2. Always display Model Used for current task completion.
When citing/creating HDD files:
1. Show onscreen (read tool/output)
2. Gmail drafts (johnloucks3)
3. rclone Drive if non-urgent (d2mconcierge/D2M/)


## Session Summary 2026-04-24 — Inbox Processing

Processed 2 UNREAD tasks in opencode_inbox.md.
- TECHSEARCH complete: 22 Claude-Code alts, outputs generated, Telegram to Commander.
- MISSION-004 marked complete.

Inbox now clear.

### **2026-05-01 — Self-Healing Mandate (Wing Autonomy)**
- **Protocol:** Any "death spiral" retry pattern replaced with `SelfHealingLoop` decorator.
- **Components:** `core/self_healing.py` (utility), `OpsCenter/nexus.py` (routers), `core/mcp/travel_mcp_server.py` (scrapers).
- **Escalation:** 1 retry post-fix, then mandatory escalation to Commander.
- **Audit:** Tracked in `Wing_Autonomy_Audit.md`.


## 2026-05-01 — System Stability & Lifecycle Automation
**Status:** COMPLETE (TESS access restored; Centrav/Mozio/Blacklane sessions injected)
**Problem Solving Framework:**
1. **Autonomy:** Maximum authorized; Self-Healing Loop active.
2. **Methodology:** 4-Phase (Investigate/Analyze/Hypothesize/Implement).
3. **Principles:** Iron Law (no patches without root cause), Boil the Lake (completeness over shortcuts).
4. **Integration:** Browser-based session injection (via captured cookies) is now the standard for non-API portals (TESS, Centrav, Blacklane).

**Active Mission:** Complete lifecycle touchpoint integration. Next: Viator/Project Expedition portal registration + cookie capture.

## 2026-05-03 — OpenClaw Pattern Adaptation
**Status:** COMPLETE
**Task:** OC-OPENCLAW-ADAPTATION (P0 from Commander)
**Completed:** 2026-05-03 16:30 MT

**What Was Built:**
- OpenClaw architectural patterns adapted into Thunderbird OS
- 3 of 6 patterns implemented (P0, P2, P4), architecture specs for all 6

**Key Files Created:**
- `docs/OPENCLAW_ADAPTATION_SPEC.md` — Full architecture spec
- `core/ai_infra/thunderbird_skill_builder_mcp.py` — MCP tools for skill builder
- `core/ai_infra/thunderbird_multi_agent.py` — Multi-agent orchestration engine
- `core/ops/thunderbird_heartbeat.py` — Proactive heartbeat assessment
- `deploy/d2m-heartbeat.{service,timer}` — Systemd timer (every 2 hours)
- `tests/test_openclaw_adaptation.py` — Integration tests (~20 cases)

**Telegram Commands Added:**
- `/build-skill <description>` — Build Python skill from natural language
- `/spawn <n> <task>` — Spawn N agents for parallel work
- `/heartbeat` — Run system health assessment

**MCP Tools Added (4):**
- `build_skill_from_description_tool`
- `list_available_skills_tool`
- `validate_skill_safety_tool`
- `get_skill_metadata_tool`

**Documentation Updated:**
- `AGENTS.md` — Added new entrypoints and test reference
- `core/communication/thunderbird_telegram_c2.py` — Help command updated
- `core/mcp/travel_mcp_server.py` — Skill builder registration

**Future Work:** P1 (vector memory), P3 (config hot-reload), P5 (OAuth self-heal)

## 2026-05-06 — Task Dispatch Protocol Update
- **Protocol Change:** Strictly discontinue use of `--foreground` flag for headless Claude dispatching.
- **Reason:** Enforces background execution to prevent process termination/timeouts on long-running tasks.
- **Verified Workflow:** Use background dispatching + `watch_task.py` for completion monitoring.

---
## 2026-05-14 — Standing Order: Gmail Historical Search Protocol
1. Use native Gmail search (via Playwright or appropriate browser-based automation) for all historical Gmail searches, especially when D2M API/MCP tools fail.
2. If D2M Gmail tools do not find results, immediately pivot to browser-based native search.
3. Ensure authorized personal accounts (e.g., yodainva@gmail.com) are included in search scope if permitted by Commander.

## 2026-05-15 — CHROMEBOOK INITIATION
**Status:** PROTOCOL ESTABLISHED
**Reference:** `CHROMEBOOK_INIT.md`
**Protocol:** 
- Outbound-only MCP connection to Yoga server (primary host).
- Standing Order: Execute direct, no confirm emails.
- Coordination: Handoff of task state (McGlasson, SilverSea) established.

## 2026-05-16 — Cost Dashboard Operationalization (MISSION-008)
**Status:** COLLECTORS FIXED, DASHBOARD LIVE
**Dashboard URL:** https://costs.d2mluxury.quest
**Local port:** 8902
**Tunnel:** User-level cloudflared service (`systemctl --user restart cloudflared.service`)

### Changes Made
1. **OpenRouter collector** (`core/cost_dashboard/collectors/openrouter.py`):
   - Replaced `/api/v1/activity` (403 — needs management key) with `/api/v1/auth/key` for aggregate snapshots
   - New table: `openrouter_snapshots` stores periodic usage snapshots (total/daily/weekly/monthly)
   - Added `PRAGMA busy_timeout=10000` for SQLite contention

2. **Claude collector** (`core/cost_dashboard/collectors/claude_usage.py`):
   - Rewritten to parse `~/.claude/projects/-home-john/<uuid>.jsonl` session files
   - Extracts `message.usage` from `type=assistant` events (input_tokens, output_tokens, cache fields)
   - Falls back gracefully — also reads `usage_*.jsonl` if present (--output-usage flag)
   - Limited to `-home-john` project + 5MB file cap to avoid 588MB Thunderbird project dir

3. **dispatch_claude.py** (`core/ai_infra/thunderbird_headless_spawn.py`):
   - Both spawn modes now pass `--output-usage` flag writing to `~/.claude/projects/-home-john/usage_<task>_<ts>.jsonl`

4. **Dashboard template** (`core/cost_dashboard/templates/index.html`):
   - New OpenRouter budget card with gauge (96.9% → red)
   - New Claude usage by model table with totals row

5. **Systemd services** (`deploy/systemd/cost-*.service`):
   - Added `EnvironmentFile=/home/john/Thunderbird/.env` to source OPENROUTER_API_KEY

### DB State
- 33,963 Claude events (opus-4-7: 14,810, unknown: 13,475, opus-4-6: 5,678)
- 1 OpenRouter snapshot: $203.59/$210, daily $3.03, weekly $28.19, monthly $60.04
- No window tracking or daily rollups yet (no Claude 5hr windows have completed)

### Key Fixes
- Cloudflared is a **user-level systemd service**: `systemctl --user restart cloudflared.service`
- costs.d2mluxury.quest tunnel working and serving live dashboard
- OpenRouter /activity requires management key — use /auth/key for aggregate data

### 2026-05-16 — Claude Max Plan Added to Dashboard
- New `plan_snapshots` table captures plan-level limits from Claude web UI
- **Seed script**: `core/cost_dashboard/seed_plan.py` (run after plan changes/monthly reset)
- Dashboard now shows 4 color-coded gauges: Session (10%), Weekly All (22%), Weekly Sonnet (29%), Monthly ($50.24/$100)
- Plan: Max ($100/mo), balance $3.15, auto-reload Off, resets June 1

---

# OpenCode Memory — Session 2026-05-16 (late evening)

## Built: Telegram Staff Access Infrastructure

### telegram_access.json
Created `OpsCenter/telegram_access.json` — Commander-only whitelist (7554895206, role: commander). JSON schema designed for future OA partner extensibility (executive_officer, operations, observer roles). Zero code change required to add new users.

### thunderbird_telegram_webhook.py — Major modifications
1. **Constants**: ACCESS_FILE, WING_NAMES, WING_HELP, EXERCISE_STATE dict, GROUP_MAP
2. **check_access()**: Replaced hard `user_id != COMMANDER_ID` with whitelist-based access. Lazy-loaded from telegram_access.json. Commander always falls through via env var.
3. **_load_personas()**: Updated to populate GROUP_MAP from STAFF_PERSONAS 3-tuple
4. **STAFF_PERSONAS**: Converted to 3-tuple (name, engine, group). Group assignment per TALON's design:
   - CONDOR/Claude: hale, naia, luna, navarro, reyes, washington
   - WIND/OpenCode: dembe, castillo, sterling, harlan, elon
   - Changed: navarro (opencode→claude), reyes (opencode→claude), washington (opencode→claude)
5. **Group handlers**: /wind [message] → dispatches to all 5 WIND staff (parallel, results collated). /condor [message] → dispatches to all 6 CONDOR staff. /groups → lists all staff by group with engine icons.
6. **Exercise state machine**: /exercise T0|T1|T2|T3 [wind|condor] [charter] → in-memory state per chat_id. /exercise status, /exercise cancel. T2/T3 auto-dispatch to named group.
7. **wing_comms.md writer**: _append_to_wing_comms() — appends exercise start/cancel/group dispatch entries with timestamps.
8. **_handle_help()**: Updated staff bot help to show /wind, /condor, /groups, /exercise commands.
9. **_chunk_text()**: Utility for splitting long group dispatch results.

### Quality Management Integration
**Standing Order**: `standing_orders/SO_QUALITY_MANAGEMENT_20260516.md`
- AF CPI/CI² (AFI 38-401) DMAIC-derived QM lens for WING EXERCISE protocol
- 4 pre-delegation QM fields: desired end state, definition of success, metrics (baseline→target), ETC
- Quality Review Gate (Gate 5) after T3 Hotwash — enforces quality score before exercise is complete
- 2 new metrics: exercise_quality_score_pct (≥85%), pre_task_qm_completion_rate (100%)
- Sterling owns quality enforcement; Castillo briefs staff

**Protocol doc updated**: `docs/WING_EXERCISE_PROTOCOL.md` → v1.1
- T2 Prompt Charter: 9 fields (was 5 — added QM fields 6-9)
- T3 Prompt Charter: 9 fields (same expansion)
- T3 sequence: added Gate 5 (Quality Review)
- New QUALITY MANAGEMENT LENS section
- Metrics table: added exercise_quality_score_pct, pre_task_qm_completion_rate

### Services
- thunderbird-telegram-webhook.service restarted — health check (all 3 bots up)
- Syntax verified on both webhook.py and telegram_access.json

### Quality Execution (2026-05-16 second session — Chromebook)
Commander approved QM SO and directed execution. Built operational tooling:
- `/quality score [0-100] note [text]` — Telegram command for Sterling Gate 5 quality reviews
- `/quality summary` — show last 5 scores with trend indicators
- `quality_log.json` — persistent store at OpsCenter/
- `generate_a7_metrics.py` — enhanced with quality metrics tracking
- exercise_quality_score_pct and pre_task_qm_completion_rate now tracked in Sterling dashboard

### Operational
- `/quality` command live in staff bot
- Sterling metrics generator pulls from quality_log.json
- Gate 5 enforcement: manual via /quality, recorded persistently
- Next: commander directs next priority
