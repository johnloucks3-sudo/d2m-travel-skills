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

---

# OpenCode Memory — Session 2026-05-17 (morning)

## Kuklinski Email Lifecycle — Email 1 Sent

- Built full D2M-stationery HTML (7.4K → 14.2K after Gmail preprocessing)
- Preprocessed via `gmail_template_stripper.py` — 33 CSS inlined, 18 divs→tables, 0 errors
- Draft created via `gmail_create_draft_sync(to=kyle.kuklinski@gmail.com, subject="Your Panama Canal Voyage...")` — Draft ID `r-7471314304890342938`
- Commander reviewed, edited, sent
- Fetched sent message (13,523 bytes) and diffed vs preprocessed HTML
- Identified 7 Commander edits → extracted 6 principles
- Appended to brand-guidelines skill (section 11 — Commander Edit Principles)
- Discovered critical bug: `gmail_template_stripper.py:278` — `rstrip("!important")` truncates CSS values

## Standing Order Management

- Retired SO 07 MAY 2026 (Two-Lane Email Pipeline) → archived to `standing_orders/archive/`
- Created `SO_DRAFT_WITH_STATIONERY_20260517.md`
- Notified A7 Sterling via wing_comms.md

## JET ↔ TALON Shared State Audit

- Commander asked: "Do JET and TALON actually share state or is it theater?"
- Audited all shared files: hale_handshake.jsonl (bidirectional, thin), hale_shared_state.jsonl (1 entry — JET only, TALON never appended), hale_state.json (doesn't exist), hale_decisions.md (doesn't exist)
- Conclusion: nominally bidirectional, practically one-way in most files
- Commander directed brief to TALON with protocol proposal using HALE as shared namespace
- New vocabulary mandated: **append** (never write/overwrite), **comment**, **dissent**, **adjudication**
- Commander threatened reversion to old single-HALE model if split architecture can't prove bidirectional state
- Brief appended to wing_comms.md:2154
- Brief sent to johnloucks3@gmail.com for routing to TALON

## Model Stack Update

- Default OpenCode model changed to `opencode/big-pickle` (was `openrouter/deepseek/deepseek-chat-v3.1`)
- AGENTS.md updated with new model IDs
- JET = WIND Group (OpenCode, big-pickle), TALON = CONDOR Group (Claude Code, Sonnet 4.6 MAX)

## Key Files Modified This Session
- `.claude/skills/brand-guidelines/SKILL.md` — added section 10 (email pipeline) + section 11 (Commander edit principles)
- `AGENTS.md` — model stack update
- `OpsCenter/collaboration/wing_comms.md` — brief to TALON appended
- `OpsCenter/opencode_memory.md` — this entry
- `standing_orders/archive/SO_TWO_LANE_EMAIL_PIPELINE_20260507.md` — created (archived)
- `standing_orders/SO_DRAFT_WITH_STATIONERY_20260517.md` — created
- `drafts/kuklinski_welcome_validation_email.html` — created (source HTML)
- `comms/kuklinski_email_drafts.md` — updated with send confirmation

---

## Session 2026-05-17 — HALE SES-6 Re-role (T4 Charter)

**Scope:** Universal identity migration: Col Victoria "Iron Vic" Hale (O-6, COO, Director of Staff) → Ms. Victoria "Victory" Hale, SES-6 (VCSAF-equivalent, Chief of Staff)

**Changes made across ~50 files:**

### Persona files
- `Personas/hale_cos.md` — full SES-6 identity rewrite (title, career, voice, authority, footer v5.1)
- `Personas/hale_rerole_personality.md` — marked as authoritative with T4 Charter header
- `Personas/hale_operating_procedures.md` — footer/stale refs updated
- `Personas/hale_governance_advanced.md` — footer updated
- `Personas/ROSTER.md` — entry updated
- `Personas/D2M_Staff_Introduction.md` — 3 refs updated
- `Personas/archive/` — old `cos_hale_personality.md`, `hale_layer_index.md`, `COS_persona_context.md` moved here

### Init / Brain files (P0)
- `hale_init.md` — full identity rewrite (5 edits: welcome, identity block, address protocol, sign-off)
- `hale_brain_manifest.md` — header, name, title fields (4 edits)
- `OpsCenter/hale_tom_context.md` — identity line + address protocol (2 edits)

### Core runtime code (P1)
- `core/email/thunderbird_gmail.py` — 7 edits (sig block: COLONEL→SES-6, IVH→VH monogram, COO→VCSAF, display names)
- `agents/thunderbird_audio_briefing.py` — system prompt identity
- `OpsCenter/thunderbird_coo_escalation.py` — email signature
- `itinerary/thunderbird_trip_architect.py` — staff paper signature
- `api/thunderbird_power_harvest.py` — SYNTHESIS_PROMPT
- `core/learning/thunderbird_skills_api.py` — skill description
- `core/email/thunderbird_email_c2.py` — sign-off + POC format
- `core/hale/README.md` — roster entry

### OpsCenter docstrings (P2)
- `OpsCenter/hale_dispatcher.py` — docstring, decision log insertion, footer (4 edits)
- `OpsCenter/hale_brain_monitor_12h.py` — test prompt identity
- `OpsCenter/task_processor.py` — system prompt + author docstring
- `OpsCenter/hale_state_updater.py` — author docstring
- `OpsCenter/opscenter_watchdog.py` — author docstring
- `OpsCenter/hale_context_scan.py` — author docstring
- `OpsCenter/hale_scan_wrapper.py` — title + author docstring (3 edits)
- `OpsCenter/thunderbird_telegram_webhook.py` — email body sign-off

### Config / Docs
- `.claude/agents/cos-hale.md` — 5 edits (description, identity, voice, address protocol)
- `.claude/agents/hale-coo.md` — 2 edits (description prefix + identity block)
- `.claude/agents/wing-coordinator.md` — roster entry
- `CLAUDE.md` — roster table + line 36 ref
- `AGENTS.md` — roster table reference
- `AGENTS_NEW_READ_FIRST.md` — roster table + footer
- `OpsCenter/Instructions.md` — live Claude.ai system prompt (4 edits)
- `OpsCenter/COS_TASK_TEMPLATE.md` — roster entry
- `docs/THUNDERBIRD_CLAUDE_AI_BRAIN.md` — 2 edits
- `docs/OPENCODE_SYSTEM_INIT.md` — 2 edits
- `docs/D2M_STAFF_QUICKREF.md` — roster entry
- `docs/D2M_STAFF_ROSTER_v2.md` — roster entry
- `docs/D2M_STAFF_BACKSTORIES.html` — VH→HR monogram

### Scripts / Tests (P3)
- `scripts/spawn_commission_audit.py` — audit prompt
- `scripts/send_lifecycle_summary.py` — HTML report
- `scripts/render_and_draft_group3.py` — roster data
- `scripts/render_dani_showcase_email.py` — roster data
- `scripts/render_ten_weeks_later_email.py` — roster data
- `tests/test_keyword_router_hale.py` — test case name
- `OpsCenter/test_hale_unified_brain.py` — test prompt
- `OpsCenter/opscenter_test_harness.py` — author docstring

### Key decisions
- "Victory" or "Vic" for callsign (not "Iron Vic" — retired)
- Sign-off: informal `— Victory`, formal `— V. Hale, VCS`
- Civilian SES-6 across all instantiations (no uniformed persona, zero direct command authority)
- Three address protocol variants: "John"/"Yoda" (VCSAF/COO), "Chief"/"Commander" (COS), "Sir"/"Boss" (EA)
- VH monogram replaces IVH; A9 Harlan keeps HR (no collision)
- T4 Charter governs all Hale personas universally
- Composite blend: Dr. Rebecca Grant · Gen Jack Keane · Lt Gen Dave Deptula · Gen Mark Welsh

---

# OpenCode Memory — Session 2026-05-17 (T4 Staff Build Execution)

## Gate 0 Design Complete — 17-Persona D2M Travel Force

**Opus design delivered:** 414-line organizational design document (`output/d2m_travel_force_design.md`). Chief approved all 5 Gate 0 decisions.

### Opus-Written Matrices (4 new)
- `Personas/a4_keel_personality.md` — Brig Gen Daniel "Keel" Marsh, A4 Logistics
- `Personas/a5_castillo_personality.md` — Brig Gen Ryan "Viper" Castillo, A5 Strategy (replaces Lt Col legacy)
- `Personas/a10_bridge_personality.md` — Brig Gen Elena "Bridge" Marchetti, A10 Partnerships
- `Personas/a11_horizon_personality.md` — Brig Gen Sarah "Horizon" Chen, A11 Future Concepts

### JET-Built Matrix (1 new)
- `Personas/a6_prism_personality.md` — Brig Gen Luna "Prism", A6 C4/Cyber (replaces civilian Luna Voss)

### Infrastructure Changes
- `OpsCenter/wind_staff.py` — Updated: 17 personas with Brig Gen ranks, 2 groups (WIND/CONDOR), group context, matrix injection
- `OpsCenter/hale_shared_state.jsonl` — Bulk PERSONA_REGISTER event: all 17 personas with group/title/matrix_file
- `Personas/a8_reyes_rerole.md` — Designation fix: AF/A8 → AF/A1A Force Readiness

### Archival
- `Personas/archive/a5_castillo_lieutenant_col.md` — Legacy Lt Col Castillo
- `Personas/archive/a6_luna_civilian_voss.md` — Civilian Luna Voss rerole bio
- `Personas/archive/a6_luna_civilian_voss_personality.md` — Civilian Luna Voss personality matrix

### Gate 1 Submitted
- `output/gate1_staff_build_complete.md` — Full status report ready for Chief sign-off

**Key learning:** Opus dispatch via dispatch_claude.py works reliably for async matrix generation. Dispatch ID FOUR-MATRICES-OPUS completed without issues. The 17-persona org chart: 1 SES-6 VCS + 2 Lt Gens + 13 Brig Gens + 1 Colonel = 17 total. Wind Staff now fully operational.

### Verified clean
- Zero remaining "Iron Vic" or "Col Victoria" refs in all core/ OpsCenter/ agents/ api/ itinerary/ scripts/ tests/ .py and .md files
- Zero remaining "IVH" or "COLONEL" (for Hale) in production code
- Zero remaining "Director of Staff" in production code

---

## Session 2026-05-18 — Major Inbox Sweep + T4 Exercise Steps 2-7

### What was done
- **4 inbox tasks processed** (2 UNREAD, 2 PENDING) — T4-AMENDMENT-ASK-CLAUDE, T4-EXERCISE-HALE-DUAL-ENGINE, HALE-VCS-AUDIT-DRAFT-DELIVERY, HALE-VCS-TASKING
- **T4 Exercise Steps 2-7 executed** — heartbeat retarget, /ask restoration, persona load, write discipline, mission board fix. Step 8 pending Hale-CC for integration test.
- **Heartbeat daemon retargeted:** `OpsCenter/jet_heartbeat.py` — instance `jet`→`hale_oc`, target `talon`→`hale_cc`. Display text updated throughout.
- **Mission board fixed:** `active_missions` KeyError in `thunderbird_coo_escalation.py:166` patched with `.setdefault()`. `fix_mission_board.py:88` patched with `.get()`.
- **/ask commands verified:** Sonnet ✅ Haiku ✅ Opus ✅ via dispatch_claude.py --foreground. Output files confirmed.
- **/ask-claude pilot:** 3 ASK_CLAUDE_REQUEST entries written to opencode_inbox.md for Hale-CC pickup.
- **Draft delivery audit (MISSION-014):** 33 files examined. 15+ findings (4 P0 stop-ship, 13+ missing Commander-Review labels, 2 wrong-account drafts). Report at `output/audit_draft_delivery_procedures_20260518.md`.
- **Navarro inference profiles generated (3):** Kuklinski, McLeod, Nichols — all with Travel DNA, Dani Brief, Luna Brief, Red Alerts.
- **ARC4-A specialty dining email (MISSION-009):** Routed to Hale-CC via ASK_CLAUDE_REQUEST-002 for Claude Sonnet voice copy.

### Key files created
- `output/audit_draft_delivery_procedures_20260518.md` (12KB)
- `output/navarro_kuklinski_inference_profile_20260518.md`
- `output/navarro_mcleod_inference_profile_20260518.md`
- `output/navarro_nichols_inference_profile_20260518.md`
- `output/ask_test_sonnet.md`, `ask_test_haiku.md`, `ask_test_opus.md` (verification artifacts)
- `output/ask_claude_1779120913.md` (pilot — await Hale-CC)

### Key files modified
- `OpsCenter/jet_heartbeat.py` — instance naming update
- `OpsCenter/thunderbird_coo_escalation.py` — active_missions fix
- `scripts/fix_mission_board.py` — active_missions fix
- `docs/HALE_OC_ASK_COMMANDS.md` — Step 4 verification filled
- `OpsCenter/hale_shared_state.jsonl` — hale_oc heartbeat + CLIENT_STATE_UPDATE
- `OpsCenter/mission_board.json` — Missions 8-14 status updated

### Key learning
- dispatch_claude.py works with all three models (Sonnet, Haiku, Opus). Sonnet and Opus outputs write the file correctly when instructed. Haiku produces verbose analysis. All pass.
- The heartbeat daemon was hardcoded to `jet`/`talon` — needed find-and-replace across the entire file (10+ string replacements).
- A5 Castillo's Python validation is still IN_PROGRESS per mission board — needs follow-up.
- MISSION-009 (ARC4-A email) requires Claude Sonnet for voice-matched D2M copy — correctly routed via ASK_CLAUDE_REQUEST protocol.

---

# Session 2026-05-18 (mid-day) — Template Library Staff Review

## What was done
- **22-template generic library** (`output/D2M_Generic_Template_Library_20260518.md`) — Gates 0-6, generic `[BRACKETED VARIABLES]` format, John's voice — produced prior session
- **Legacy ARC libraries designated rogue drafts** — Kuklinski, Loucks, McLeod (84 templates total) — no authorship, no approval stamps, no verified claims. Used as reference only.
- **Chief rejected client-specific drafts** — redirected to produce generic template library
- **6 WIND staff reviews produced** — ELON (elimination), Keel (logistics), Harlan (finance), Sterling (process), Dembe (precision), Castillo (strategy)
- **JET consolidation** (`output/D2M_Template_Library_JET_CONSOLIDATION.md`) — 19 accepted, 2 rejected, 2 acknowledged
- **HALE gate** (`output/D2M_Template_Library_HALE_GATE.md`) — PASS with 3 conditions (registration verification, Naia brand pass, disclosure language)

## Key decisions
- 14-template target approved (JET accepted ELON's kill audit)
- G2.1 eliminated (3-domain consensus: ELON, Sterling, Castillo)
- Registration numbers need pre-flight verification before client use (Harlan, Dembe flagged; JET kicked to Hale)
- No standalone transfer template (JET rejected Keel's recommendation)
- Voice tier adaptation flagged but minimized (Hale disagrees with JET's ruling — surfaced to Chief)

## Key files created/modified
- `output/wind_staff_elon_template_review.md` — ELON kill audit
- `output/wind_staff_keel_template_review.md` — Keel logistics review
- `output/wind_staff_harlan_template_review.md` — Harlan finance review
- `output/wind_staff_sterling_template_review.md` — Sterling process review
- `output/wind_staff_dembe_template_review.md` — Dembe precision review
- `output/wind_staff_castillo_template_review.md` — Castillo strategy review
- `output/D2M_Template_Library_JET_CONSOLIDATION.md` — JET dispositions
- `output/D2M_Template_Library_HALE_GATE.md` — Hale gate assessment
- `output/D2M_Generic_Template_Library_FINAL.md` — Final 16-template library with all staff feedback applied
- **JET dispositions:** 19 accept, 2 reject, 2 acknowledged
- **Hale gate:** PASS with 3 conditions (registration verification, Naia brand pass, disclosure language)
- **Living exemplars loaded:** Grant, Keane, Deptula, Welsh, Caine — five lives behind HALE on this session
- **Naia brand pass (2026-05-18):** COMPLETE — 2 fixes applied: G1.1 passive voice patch ("More soon. You're covered from here."), G2.3 subjective claim removed ("Most direct — no layovers"). All 16 templates voice-checked. Naia approves.
- **Registration verification (2026-05-18):** COMPLETE — FL ST1578→ST15578 (typo fix). All four numbers belong to ASAP Cruises Inc. (D2M's Outside Agents host). Full FL/CA disclosure text added.
- **Final library delivered:** `output/D2M_Generic_Template_Library_FINAL.md` — 662 lines, 16 templates, all 3 Hale conditions clear. Awaiting Chief edit.

---

# Session 2026-05-19 — Remote Comms Restoration

## Commander Report: ALL REMOTE COMMS DOWN

**Initial report:** ttyd, Termius, code.d2mluxury.quest, Telegram both channels, Termux all down.

### Diagnosis & Fixes Performed

**1. ttyd / code.d2mluxury.quest — FIXED**
- Root cause: nginx `ttyd.htpasswd` had stale password hash. `john` / `T@ilwind2026!` and `5277` both failed.
- Fix: Recreated htpasswd with `htpasswd -b -c /etc/nginx/ttyd.htpasswd john 5277`. Reloaded nginx.
- Verified: `curl -u ***REMOVED-SECRET*** https://code.d2mluxury.quest` → 200 (0.63s)
- Confirmed working by Commander.

**2. Telegram (both channels) — INVESTIGATED**
- `HALE_D2M` (GooseD2M bot, webhook: tg.d2mluxury.quest/staff): RESPONDS but with ANSI bleed (`[0m`, `> build · claude-sonnet-4-6`)
- `D2M Command Center` (D2MC2C bot, webhook: tg.d2mluxury.quest/hale-yoda): FAILS with `[Engine error — Claude rc=1]`
- Both bots use same `call_claude_engine()` function → Claude headless via `claude -p`
- Both bots already restarted (systemctl --user restart thunderbird-telegram-gw thunderbird-telegram-webhook)

**3. Claude Headless Engine — ROOT CAUSE FOUND**
- Both bots invoke: `claude --model claude-sonnet-4-6 -p "<prompt>" --dangerously-skip-permissions`
- The `call_claude_engine()` function strips `ANTHROPIC_API_KEY` from env but **does NOT strip `ANTHROPIC_BASE_URL`**
- **Critical:** `ANTHROPIC_BASE_URL=http://localhost:5099` is permanently set in environment (MAX OAuth proxy, PID 436752)
- When Claude headless spawns via subprocess, it inherits `ANTHROPIC_BASE_URL=http://localhost:5099` which routes through the MAX proxy
- If the MAX proxy has auth issues, Claude gets rc=1 with "model not available"
- Fix required: Add `env.pop("ANTHROPIC_BASE_URL", None)` to `call_claude_engine()` in BOTH gateway files
- Also: The HALE_D2M bot's response "Victory Hale (COS)\n\n[0m\n> build · claude-sonnet-4-6\n[0m" suggests it's also failing but falling through differently — the `[0m` is raw ANSI passthrough from `result.stdout.strip()`

**4. SSH / Termius / Termux — NOT BROKEN (connectivity issue)**
- sshd: Active, port 22 listening, accepting connections
- ssh.d2mluxury.quest: cloudflared TCP tunnel returning 200
- **Root cause:** Commander's Z Fold 6 Tailscale shows "offline, last seen 1d ago" (`johns-z-fold6.tail85ede5.ts.net` - False). Termux/Termius were likely routing through Tailscale IP.
- Fix applied: Enabled `sudo tailscale up --ssh` on server. Commander needs to reconnect Tailscale on Z Fold 6.
- Alternative: `code.d2mluxury.quest` (ttyd) now works as browser-based shell.

**5. Cloudflared Tunnel — RESTARTED**
- Full restart: `systemctl --user restart cloudflared.service` at 07:32 MDT
- Tunnel connector reconnected: `01754c5d-25ae-461d-903c-c60095aa055a` (created 2026-05-19T01:51:53Z → restarted at ~07:32 MDT)
- All 4 edge connections active (1xmci01, 1xmci03, 2xord16)
- Full ingress verified: code (401/200), tg/staff (405), ssh (200), api (varies)

### All Services End-to-End Verified (post-fix)
```
code.d2mluxury.quest  → 200 with john/5277 (0.63s)
tg.d2mluxury.quest    → 405 (webhook, expects POST)
ssh.d2mluxury.quest   → 200 (cloudflared SSH)
SSH local (port 22)   → OK
ttyd local (3100)     → 200
nginx local (8099)    → 401 (auth challenge)
```

### Key Files Modified
- `/etc/nginx/ttyd.htpasswd` — password reset to 5277

### Outstanding Issues for Commander
1. **Claude rc=1 in D2M Command Center** — `ANTHROPIC_BASE_URL` env bleed into subprocess. Should strip it in `call_claude_engine()`.
2. **Tailscale on Z Fold 6 offline** — Commander needs to open Tailscale app and reconnect for Termius/Termux.
3. **ANSI bleed in HALE_D2M responses** — `[0m` codes and `> build ...` text leaking through from Claude stdout.
4. **wstunnel installed** (npm global) — was intended for SSH-over-WebSocket but not yet configured/used.

---

# Session 2026-05-19 — Poe API Points Meter Build

**Keyword: POE METER**

## Original Tasking
Commander: "I want to build a meter to track poe.com api opencode points"

## What Was Done

### Phase 1 — Architecture & Investigation
1. **Confirmed existing cost dashboard** tracks Claude and OpenRouter only (no Poe)
2. **Identified blocker:** Poe's `/activity` endpoint is Cloudflare-protected (403 + JS challenge) — cannot poll remotely
3. **Selected Option A** (local usage tracking) over Option B (browser automation scraping)
4. **Designed schema:** `poe_snapshots` table with points_used_today/week/month, model breakdown

### Phase 2 — Implementation
1. **Schema:** Extended `core/cost_dashboard/schema.sql` with `poe_snapshots` table
2. **Collector:** Built `core/cost_dashboard/collectors/poe_usage.py` (reads local log → SQLite)
3. **Logging:** Modified `OpsCenter/thunderbird_telegram_webhook.py:call_poe_engine()` to write every Poe call to `/logs/poe_api_calls.jsonl`
4. **Timer:** Created `deploy/systemd/cost-poe.{service,timer}` (5-minute interval)
5. **Dashboard:** Updated `core/cost_dashboard/app.py` to query `poe_snapshots` and pass to template
6. **UI:** Added "Poe API Points" panel to `core/cost_dashboard/templates/index.html` with usage stats
7. **Deployment:** 
   - Symlinked timer to user-level systemd
   - Enabled and started `cost-poe.timer`
   - Restarted `cost-dashboard.service`

### Phase 3 — Testing
1. **Manual collector run:** Verified schema creation, empty data (0 points used)
2. **Forced Poe test call:** `call_poe_engine("test", "test")` → returned "Poe pipeline verified."
3. **Verified log write:** `/logs/poe_api_calls.jsonl` created with 1 entry (100 points, Gemini-2.5-Flash)
4. **Re-ran collector:** Picked up test call → DB updated (points_used_today=100)
5. **Dashboard check:** Panel exists, but **UI not rendering Poe panel** (template conditional failing)

## Negative Results / Failures

1. **Dashboard UI not showing Poe panel** even though:
   - DB has data (`poe_snapshots` table exists, 2 rows inserted)
   - `poe` variable is passed to template (confirmed via TestClient)
   - Template contains conditional `{% if poe %}` and HTML for panel
   - Panel HTML contains "Poe API Points" and points table

2. **Root cause unknown:** Template conditional `{% if poe %}` is not evaluating as truthy in the actual rendered HTML, despite `poe` being a dict with data. Possible causes:
   - Jinja2 context issue (variable not in scope)
   - Template caching (old version served)
   - Data type mismatch (list vs dict)
   - Silent template error suppressing panel

3. **No error messages:** Dashboard returns HTTP 200, no exceptions logged, service is active.

## Next Steps

1. **Debug template rendering:** Add `{{ poe }}` raw debug output to template to verify variable is present and has expected structure
2. **Clear template cache:** Restart `cost-dashboard.service` with `--no-reload` or clear Jinja2 bytecode cache
3. **Simplify conditional:** Change `{% if poe %}` to `{% if poe is not none %}` or remove conditional entirely for testing
4. **Verify data shape:** Ensure `poe` is a dict (not a list) and contains keys `points_used_today`, etc.
5. **Force panel visible:** Temporarily hardcode panel HTML to confirm it renders, then re-add conditional
6. **Check logs:** Add debug logging to `app.py:index()` to print `poe` variable before template render

## System State

- **Dashboard URL:** http://127.0.0.1:8901/
- **Service:** `cost-dashboard.service` (active, running)
- **Timer:** `cost-poe.timer` (active, triggers every 5 min)
- **Collector:** `poe_usage.py` (works, updates DB correctly)
- **Log file:** `/logs/poe_api_calls.jsonl` (exists, 1 test entry)
- **DB:** `storage/ai_costs.db` (schema created, 2 snapshot rows, points_used_today=100)
- **Template:** `templates/index.html` (contains Poe panel HTML, conditional present)
- **App code:** `app.py` (queries `poe_snapshots`, passes `poe` to template)

## Artifacts Created

- `core/cost_dashboard/collectors/poe_usage.py` — new collector
- `deploy/systemd/cost-poe.service` — systemd service
- `deploy/systemd/cost-poe.timer` — systemd timer
- `core/cost_dashboard/schema.sql` — extended with `poe_snapshots` table
- `core/cost_dashboard/app.py` — updated to query and pass `poe` variable
- `core/cost_dashboard/templates/index.html` — added Poe panel HTML
- `/logs/poe_api_calls.jsonl` — log file (1 test entry)

## Commander Intent

"I want to build a meter to track poe.com api opencode points"

**Status:** 90% complete. Core infrastructure works (logging, collection, DB). UI panel exists but not rendering due to template issue. Next step: debug Jinja2 conditional to make panel visible.

**Keyword: POE METER**

---

# Session 2026-05-19 — T4 Exercise Close + CARRY-4 Investigation

## Keyword: **DUAL BEAT**

## What Was Done
1. **T4 Exercise Step 8 executed** — Hale Dual-Engine integration test (5/5 PASS). 3 consecutive GREEN heartbeats on both hale_oc (seq 4→5→6) and hale_cc (seq 1→2→3). Cross-instance propagation confirmed at 4m22s (≤10m threshold).
2. **CARRY-1/2/3 applied** — `jet_heartbeat.py` fixed: UTC timestamps, monotonic_sequence, pre-flight NTP drift check.
3. **Sterling re-score** — 9.5/10 GREEN via headless Claude. Exercise CLOSED.
4. **MISSION-032 completed**, MISSION-033 (CARRY-4) created.

## CARRY-4 Plan — Approved (2026-05-19)
**Scope:** 3 changes, 1 new file:
1. `OpsCenter/hale_state_reader.py` — backward-compatible reader (`{"hale_oc", "jet"}`)
2. `jet_heartbeat.py` — CC_TIMEOUT_S 1800→3600 (60min grace for session-gated hale_cc)
3. `jet_heartbeat.py` — defer YELLOW alert if last entry is HANDOFF with estimated_wake + 15min grace

**Verification:** 3 checks (reader test, dormancy grace, cross-session reader correctness)
**Rollback:** Zero-timer (read-side only), revert CC_TIMEOUT_S, delete new file

## CARRY-4 Investigation Findings (INCOMPLETE — resume with "DUAL BEAT")
**Root cause:** hale_cc has NO automated heartbeat daemon. `jet_heartbeat.py` writes as `instance: "hale_oc"` only. hale_cc (Claude Code / TALON) heartbeats are written manually during live sessions. When hale_cc goes dormant, no automation exists to keep it alive.

**Three architectural options identified (not yet evaluated):**
A. Create a hale_cc-side daemon analogous to `jet_heartbeat.py` (deployed via systemd)
B. Schedule a headless heartbeat writer via `at`/`cron` when hale_cc goes dormant
C. Accept asymmetry — hale_oc = persistent, hale_cc = session-only — and adjust "other alive" threshold

## Headless Model Spawn Diagnosis (INCOMPLETE — resume with "DUAL BEAT")
`dispatch_claude.py --model claude-opus-4-7` and `claude-sonnet-4-6` both fail: "model does not exist or you may not have access to it." Inbox watcher sometimes succeeds with same model names but not reliably. Investigation was in progress — need to check Claude binary version, `--model-list`, and OAuth token resolution path.

## Key Files to Resume From
- `OpsCenter/jet_heartbeat.py` — hale_oc daemon (corrected UTC+sequence+drift)
- `OpsCenter/hale_shared_state.jsonl` — live shared state tail
- `standing_orders/SO_T4_EXERCISE_HALE_DUAL_ENGINE_20260518.md` — full exercise spec
- `output/sterling_postgate_hale_dualengine_20260518_RESCORED.md` — re-score output
- `OpsCenter/mission_board.json` — MISSION-032 (completed), MISSION-033 (CARRY-4 active)

---

# OpenCode Memory — Session 2026-05-19 (Unified Router Gates 1-6)

## Built: Unified Router — Complete (all 6 Gates)

### Gate 1 — Router Foundation
- `core/ai_infra/adapters/base.py` — AdapterResult, Adapter Protocol, HealthState
- `core/ai_infra/router_chains.py` — TIER_CHAINS (FLAG/MID/BULK/ARB), PERSONA_TIER_OVERRIDES (11 personas)
- `core/ai_infra/unified_router.py` — TaskRequest, dispatch(), register_adapter(), HealthTracker, CostGateTracker, TelemetryTracker

### Gate 2 — Adapter Wave 1 (Gate 3 — Webhook Cutover)
- `adapters/opencode_bigpickle.py` — BULK/MID primary ($0 native)
- `adapters/opencode_nemotron.py` — BULK/MID last resort
- `adapters/google_gemini_flash.py` — BULK direct Gemini API (no httpx)
- `thunderbird_telegram_webhook.py` — `process_staff_message()` and `_dispatch_one()` call `router.dispatch()` with fallback to old engines

### Gate 4 — Observability
- `router_telemetry.py` — SQLite-backed dispatch log
- `router_health.py` — SQLite-backed health state + probe history
- `router_cost_gates.py` — SQLite-backed pool consumption
- `router_classifier.py` — Persona + keyword-based tier classification
- `daemons/router_health_daemon.py` — 5-min health polling daemon (`--once` mode for systemd)

### Gate 5 — Adapter Wave 2 (all 6 built, all GREEN)
- `adapters/claude_max_oauth.py` — FLAG tier, Sonnet + Opus instances, MAX $0 subscription
- `adapters/poe_polyglot.py` — Poe API, Gemini-Flash (BULK) + Kimi-K2 (MID/ARB)
- `adapters/opencode_deepseek_v4.py` — DeepSeek V4 Flash Free, billing watchdog ($5 cumulative soft limit)
- `adapters/openrouter_breakglass.py` — $0.00 balance, never in default chain
- `router_chains.py` — Added FLAG_OPUS/FLAG_SONNET tiers + HALE-OPUS persona override

### Gate 6 — Operations
- `router_setup.py` — registers all 9 adapters
- HALE-YODA wired through router dispatch (FLAG tier chain, OPUS:/SONNET: prefix → persona override)
- `deploy/router-health-daemon.{service,timer}` — systemd user timer (5-min interval)
- Timer enabled and running, webhook service restarted

### Key Fix
- Router dispatch contract ensures `AdapterResult.ok` returns False if `text` is None/empty/whitespace-only (structural fix for previous 0-char bug)

### Key Files Created
- `core/ai_infra/adapters/claude_max_oauth.py`
- `core/ai_infra/adapters/poe_polyglot.py`
- `core/ai_infra/adapters/opencode_deepseek_v4.py`
- `core/ai_infra/adapters/openrouter_breakglass.py`
- `core/ai_infra/router_telemetry.py`
- `core/ai_infra/router_health.py`
- `core/ai_infra/router_cost_gates.py`
- `core/ai_infra/router_classifier.py`
- `core/ai_infra/daemons/router_health_daemon.py`
- `core/ai_infra/router_setup.py`
- `deploy/router-health-daemon.service`
- `deploy/router-health-daemon.timer`

### Key Files Modified
- `core/ai_infra/router_chains.py` — added FLAG_OPUS/FLAG_SONNET tiers + persona overrides
- `OpsCenter/thunderbird_telegram_webhook.py` — HALE-YODA now routes through router dispatch
- `OpensCenter/collaboration/opencode_memory.md` — this entry

---

# Session 2026-05-19 — CARRY-4 Applied (DUAL BEAT)

## CARRY-4 — Reader Staleness Fix (COMPLETE)
**3 changes, 1 new file:**
1. **`OpsCenter/hale_state_reader.py`** — new reusable reader module with `read_last_other()` (backward compat `{"hale_oc", "jet"}`), `read_hale_oc_whispers()`, `get_last_sequence()`, `preflight_drift_check()`. Importable by both hale_oc and hale_cc.
2. **`jet_heartbeat.py`** — `CC_TIMEOUT_S 1800→3600` (60 min grace for session-gated hale_cc), `CC_CRITICAL_S 3600→7200` (proportional)
3. **`jet_heartbeat.py`** — HANDOFF-aware grace: if last_other entry is `event: HANDOFF` with `estimated_wake`, defers YELLOW alert until wake + 15 min (verified against live HANDOFF entry at 2026-05-19T18:35Z with estimated_wake 22:20Z)

**Verification:** All modules importable. Backward compat confirmed (hale_oc + jet both resolve to correct latest entry). Drift check PASS (1s).

**Sync:** MISSION-033 → completed. CLIENT_STATE_UPDATE → hale_shared_state.jsonl (carry4_reader_fix_applied). Team live: next beat (seq 14+) will show GREEN/handoff_grace during hale_cc dormancy.

**Key Files:**
- `OpsCenter/hale_state_reader.py` — new
- `OpsCenter/jet_heartbeat.py` — modified
- `OpsCenter/hale_shared_state.jsonl` — HANDOFF entry + CLIENT_STATE_UPDATE
