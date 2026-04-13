# AGENTS.md — Thunderbird OS

> Dreams2Memories Travel, LLC · Python automation + LLM ops · openSUSE Tumbleweed (YOGA 192.168.1.198)

## Session Init — Read First

On every session start, read these files before doing anything else:

1. **`OpsCenter/opencode_memory.md`** — persistent session memory: what was built, what changed, operating agreement with Claude, key file locations, model stack. Append a summary of this session's work at the end when you close out.
2. **`AGENTS_NEW_READ_FIRST.md`** — **MASTER REFERENCE MANUAL** — D2M company overview, wing staff, model stack, protocols, exhaustive "For X see Y" index. Read this if you are new or re-orienting.
3. **`Personas/ROSTER.md`** — wing staff index: who does what, who to route to, who owns client comms.
4. **`OpsCenter/opencode_knowledge/INDEX.md`** — curated vault of all key reference docs, grouped by category.

If Commander asks "what do you remember?" or "what happened last session?" — read `opencode_memory.md` and summarize.


## What This Is

Thunderbird is a Python-based AI travel operations platform: MCP server (136 tools stdio / 293 HTTP), FastAPI REST gateway, Telegram bots (C2 + client-facing), email intelligence, booking management, and an AI incubator pipeline. Runs on systemd timers/services on a home server (YOGA, openSUSE Tumbleweed).

## Developer Commands

```bash
# Python env — always use the venv
source .venv/bin/activate
# or prefix: /home/john/Thunderbird/.venv/bin/python <script>

# PYTHONPATH — REQUIRED after 2026-04-06 reorg. Modules use flat imports
# but now live in core/<domain>/. Easiest way to get correct path:
source mcp_launcher_core.sh  # sets PYTHONPATH + .env (use before ad-hoc runs)
# Full path list is in mcp_launcher_core.sh — 18 dirs total.

# Run a single agent/core script with correct env
.venv/bin/python agents/<script>.py
.venv/bin/python core/<domain>/<module>.py

# Daily ritual (briefing + tech monitor)
./thunderbird_daily_ritual.sh briefing   # morning briefing only
./thunderbird_daily_ritual.sh tech       # tech monitor + Claude digest
./thunderbird_daily_ritual.sh all        # both

# Service management — system-level (MCP, Telegram, timers)
sudo systemctl status d2m-mcp.service
journalctl -u d2m-mcp.service --since "1h ago"
systemctl list-timers | grep thunderbird
# User-level services
systemctl --user list-timers

# Preflight check (services, tokens, disk, API)
.venv/bin/python api/thunderbird_preflight.py

# Google OAuth re-authorization
export OAUTHLIB_INSECURE_TRANSPORT=1
.venv/bin/python api/thunderbird_google_auth.py --authorize-headless
.venv/bin/python api/thunderbird_google_auth.py --authorize-persona

# OpenCode (multi-model agent — replaces Goose)
export PATH=/home/john/.opencode/bin:$PATH  # already in .bashrc/.profile
opencode                              # TUI, default model: deepseek-chat-v3.1 ($0)
opencode run "task"                   # headless one-shot (uses default model)
opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "task"  # explicit model
opencode web                          # browser UI (accessible from Chromebook/phone)
# NOTE: To invoke Claude headless from OpenCode, use claude -p directly (see Tasking Claude section)
```

## Architecture Boundaries

| Directory | Purpose |
|-----------|---------|
| `core/` | All production Python modules — 13 domains (ai_infra, booking, client, communication, email, intel, learning, mcp, ops, scheduling, travel, watchtower, crewai) |
| `agents/` | Standalone scheduled scripts (morning briefing, payment alerts, star protocol, bulletin) |
| `api/` | REST API, Google auth, Evernote backup, preflight, Drive wrapper |
| `ops/` | Batch runner, inbox cleanup, calendar scrub, systemd fix scripts |
| `business/` | Ship comparison, weekly reports, client materials |
| `comms/` | Guest profile forms, SSS multi-stakeholder |
| `itinerary/` | Itinerary generation, pipeline, trip architect |
| `scripts/` | One-off utilities, setup scripts |
| `bin/` | Tool helpers (gdrive, auth, chromebook bootstrap) |
| `deploy/` | systemd service/timer files |
| `templates/` | Jinja2 → WeasyPrint PDF/HTML (proposals, quotes, hotel guides, client emails) |
| `dossiers/` | Client trip dossiers (markdown) |
| `intel/` | Daily intel JSON outputs (incubator, OSINT) |
| `OpsCenter/` | Nexus daemon, Telegram gateway, mission board, keyword router, collaboration |
| `portal/` | Client portal (RSSC/TESS, port 8780) |

**Key entrypoints:**
- MCP Server: `core/mcp/travel_mcp_server.py` (launched via `mcp_launcher_core.sh`)
- REST API: `api/thunderbird_api.py` (FastAPI, port 8766)
- Telegram C2: `core/communication/thunderbird_telegram_c2.py`
- Client Telegram: `core/communication/thunderbird_telegram.py`
- Nexus Daemon: `OpsCenter/nexus.py` (task router)
- Telegram Gateway: `OpsCenter/thunderbird_telegram_gw.py`
- Client Portal: `portal/server.py` (port 8780)
- Batch Runner: `ops/thunderbird_batch_run.py`
- Agentic Intel: `core/intel/thunderbird_agentic_intel.py` (nightly 01:00 MDT)

## MCP Server — Critical Details

Launched via `mcp_launcher_core.sh` → sources `.env` → sets PYTHONPATH (18 dirs) → runs `core/mcp/travel_mcp_server.py` via `.venv/bin/python`.

**PYTHONPATH is not optional.** `travel_mcp_server.py` uses flat imports (`from thunderbird_gmail import ...`). After the 2026-04-06 reorg all modules live in `core/<domain>/`. Running the server directly without the launcher will fail with `ModuleNotFoundError`.

**Tool count:** 136 tools in stdio/Claude Code mode (core profile), 293 in HTTP mode (all profiles).

**Claude Code wiring:** `~/.claude/mcp.json` → `dreams2memories` server → `mcp_launcher_core.sh`. Tools appear as `mcp__dreams2memories__<tool_name>`. Restart Claude Code after any launcher change to reload the tool list.

**HTTP server:** Runs on port 8765 (system service) and 8767 (user service). If `d2m-mcp.service` is crash-looping (old path), run: `sudo bash ops/fix_systemd_complete.sh`

**Failure playbook:** Retry once → alternate tool → alert Commander via Telegram. Google API quota: wait 60s, retry once, then alert.

## Environment & Secrets

- `.env` — consolidated env (Telegram, API keys, all providers). 21+ active keys. **Note:** line 59 has a stray `know-rubber` token → harmless bash warning on source, ignore it.
- **Never commit:** `.env*`, `*_token.json`, `credentials.json`, `*.key`, `*_state.json` — all gitignored
- OAuth tokens live in `creds/` — root-level symlinks point there: `gmail_token.json → creds/gmail_token.json`, `drive_token.json → creds/drive_token.json`, `credentials.json → creds/credentials.json`

## Testing

No formal test framework (no pytest, no conftest.py). Verification:
- `api/thunderbird_preflight.py` — 7-check system health
- `intel/thunderbird_zfold_test.py --force` — connectivity test
- `OpsCenter/keyword_router_test.py` — 22/22 keyword routing tests (target: all PASS)
- MCP tool invocation through the server

## Git & Branching

- No CI workflows, no pre-commit hooks, no PR requirements
- Direct commits to `master` — 25 commits ahead of `origin/master` as of 2026-04-07
- `.gitignore` blocks: `creds/`, `*.db`, `*_token.json`, `*_state.json`, `storage/`, `*.zip`, `.playwright-mcp/`, archives, large binaries

## Operational Cadence

All automated via systemd timers (MDT):

| Time (MDT) | What |
|------------|------|
| 01:00 | **Agentic intel sweep** → `johnloucks3@gmail.com` (Claude Code/OpenCode/multi-model ecosystem) |
| 01:00–02:30 | Morning intel block (incubator, world intel) |
| 07:00 | Daily ritual — briefing + payment alerts |
| 08:00 | Phone connectivity test |
| 10:00 | Tech monitor + Claude digest |
| 18:30–19:30 | AI incubator: prompt → execute → review |
| 21:00 | Evening sync |
| 23:00 | Drive mirror (rclone full sync → d2mconcierge Google Drive) |

## AI/LLM Model Stack — Current (2026-04-06)

| Tool | Model | Cost | Use |
|------|-------|------|-----|
| **Claude Code** (MAX) | Opus 4.6 / Sonnet 4.6 | $0 | Primary — reasoning, code, client work |
| **OpenCode** v1.3.17 | DeepSeek V3.1 (`openrouter/deepseek/deepseek-chat-v3.1`) | ~$0.27/M | Ops, bulk tasks, scanning, interactive dev |
| **Claude Agent SDK** | Sonnet 4.6 | $0 (MAX) | Headless: `claude -p "..."` |
| **Nexus daemon** | OpenCode (DeepSeek V3.1) + claude -p judgment | ~$0/task | Keyword-routed task queue |

**Goose is decommissioned.** References to `goose-d2m`, `goose run`, or `~/.config/goose/` anywhere in docs are stale. Replace `goose run "X"` with `opencode run "X"`.

**OpenCode model IDs** (confirmed working — tested 2026-04-07):
- `openrouter/deepseek/deepseek-chat-v3.1` — **default** — DeepSeek V3.1, ~$0.27/M tokens, confirmed working
- `opencode/nemotron-3-super-free` — Nemotron free fallback
- `opencode/minimax-m2.5-free` — Minimax free fallback
- `deepseek/deepseek-chat-v3.1` — DeepSeek direct (requires DeepSeek API balance — currently $0)
- `togetherai/deepseek-ai/DeepSeek-V3-1` — DeepSeek V3.1 via TogetherAI (requires TogetherAI balance)

**Note:** `deepseek/deepseek-chat:free` and `opencode/qwen3.6-plus-free` are **decommissioned** — they throw `ProviderModelNotFoundError`. Use `openrouter/deepseek/deepseek-chat-v3.1` as the primary model.

**To invoke OpenCode headless:**
```bash
opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "your task here"
```

---

## Canonical Inbox / Outbox — File Layout

| File | Owner | Purpose |
|------|-------|---------|
| `/home/john/Thunderbird/claude_inbox.md` | Claude | **Canonical** Claude task inbox. Watcher monitors this file. Hook auto-injects UNREAD count on every user prompt. |
| `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md` | Claude | **Canonical** Claude result outbox. Write completed task results here. |
| `/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md` | OpenCode | **Canonical** OpenCode task inbox. Watcher monitors this file and spawns headless OpenCode on new UNREAD content. |
| `/home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md` | OpenCode | **Canonical** OpenCode result outbox. Create if needed. |

**Do NOT use:**
- `OpsCenter/collaboration/claude_inbox.md` — stale, merged into canonical root on 2026-04-07
- `OpsCenter/collaboration/goose_inbox.md` — decommissioned, content migrated to opencode_inbox.md
- `claude_outbox.md` at root — stale, merged into canonical OpsCenter outbox on 2026-04-07

### Cross-bot routing
- OpenCode → Claude: append task to `/home/john/Thunderbird/claude_inbox.md`
- Claude → OpenCode: append task to `/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md`
- Both agents write results to their respective outbox files
- Watcher (`thunderbird_tasking_watcher.py`) pings Commander via Telegram on any change to either inbox

### Default OpenCode model
`openrouter/deepseek/deepseek-chat-v3.1` — ~$0.27/M tokens, confirmed working 2026-04-08

---

## Tasking Claude FROM OpenCode

Three patterns depending on whether you need the result now or later.

### 1. Inline (synchronous — you need the answer now)
```bash
# Strip proxy vars so Max OAuth kicks in, not the Claude Code proxy
.venv/bin/python agents/thunderbird_model_dispatcher.py "your task here"
```
- Returns response to stdout
- Uses Claude MAX (free under subscription)
- Best for: judgment calls, voice-matched copy, strategy, client emails
- Timeout: ~3 min for complex tasks

### 2. Via claude_inbox.md (async — fire and forget)
```bash
# Append a properly-formatted task block — watcher triggers on ^status: UNREAD
cat >> /home/john/Thunderbird/claude_inbox.md << TASK

---
## TASK: <UNIQUE-ID>
status: UNREAD
from: OpenCode
injected: $(date '+%Y-%m-%d %H:%M MT')
priority: P1
task: |
  <describe what Claude should do>
  Write result to /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
TASK
```
- Watcher detects `^status: UNREAD` via inotify within 2 seconds → spawns `claude -p` headless
- Result lands in `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md`
- Claude also writes an `UNREAD` entry to `opencode_inbox.md` so watcher loops back to OpenCode
- Best for: judgment calls, client copy, strategy — any task needing Claude MAX
- **Do NOT use `echo "NEXUS: ..."` to claude_inbox** — NEXUS: prefix belongs in opencode_inbox (for Nexus daemon routing)

### 3. Via wing_comms.md (FYI / REQUEST to Claude Code)
```markdown
## REQUEST — [date]
**From:** OpenCode
**To:** Claude Code
**Task:** [description]
**File:** [output path]
```
Write to: `OpsCenter/collaboration/wing_comms.md`

---

### When to task Claude vs. handle yourself

| Task type | Route to |
|-----------|----------|
| Client email / proposal copy | Claude (voice, brand standards) |
| Strategy / pricing decisions | Claude (judgment) |
| Commander-directed tasks | Claude (keyword router handles this) |
| Code edits, file ops, bulk scanning | Handle yourself (OpenCode) |
| Research, data extraction | Handle yourself (OpenCode) |
| Arbitration / tiebreak | DeepSeek R1 (`openrouter/deepseek/deepseek-r1:free`) |

**Environment note:** Strip `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` before calling `claude -p`
so Max OAuth kicks in. The watcher service also injects `CLAUDE_CODE_OAUTH_TOKEN` from
`OpsCenter/.claude_oauth_cache` — refreshed automatically on every Commander message via
`hooks/refresh_claude_oauth_cache.sh`. If `claude -p` still fails rc=1, the watcher falls
back to `opencode run -m openrouter/deepseek/deepseek-chat-v3.1`.

---

## Key Conventions

- **Brand:** Always "Dreams2Memories Travel, LLC" — NEVER "Love Group Travel"
- **Prices:** Use `fmt_usd()` — never raw numbers in client output
- **Dates:** ISO format (YYYY-MM-DD) with timezone
- **Dossiers:** 4-step auto-dossier on any booking change (dossier → Sheets → Master Plan → Drive mirror)
- **FPD alerts:** 60 days (brief) → 45 days (Telegram + email) → 30 days (RED, daily)
- **Client-facing voice:** Dani (A3) only — 3-phase: Aggregate → Artist → Advocate. She never researches, writes briefs, or replies to Commander.
- **Email gate:** Never send outside the wing without Commander approval. Exception: `johnloucks3@gmail.com` (within-wing receive-only). Send FROM `d2mconcierge@gmail.com` always.
- **Commander:** John Loucks ("Yoda"), Telegram ID 7554895206, `johnloucks3@gmail.com`

## Dependencies

`requirements.txt` — 118 packages. Key ones: FastAPI, Flask, Google API client, Anthropic, OpenAI, google-genai, google-adk, playwright, twilio, gspread, weasyprint, APScheduler, MCP SDK. Notable pin: `websockets==15.0.1` (downgraded for google-adk compatibility).

## Important References

- `CLAUDE.md` — Full operating manual, persona roster, hard rules, output contract
- `Personas/hale_cos.md` — COS Hale 7-layer identity (auto-loaded by `CLAUDE.md`)
- `docs/MULTI_MODEL_STACK.md` — Post-Goose architecture (Claude Code + OpenCode)
- `docs/CLAUDE_CODE_DRIVE_AND_CORE_GUIDE.md` — Drive folder IDs, core module registry
- `docs/ARCHITECTURE_REFERENCE.md` — Component table, MCP failure playbook
- `.claude/CLAUDE.md` — Nexus system memory (critical procedures, file map, keyword router)
- `dossiers/CLAUDE.md` — Dossier conventions and FPD rules
- `templates/CLAUDE.md` — Template engine documentation
- `THUNDERBIRD_MASTER_PLAN.md` — Full project history (2200+ lines)
- `Personas/ROSTER.md` — **Wing persona index** — all 12 staff + extended personas, roles, triggers, source files
- `Personas/hale_cos.md` — COS Hale 7-layer identity (full authority, brain dispatch, standing orders)
- `Personas/D2M_Staff_Introduction.md` — Narrative bios for all primary wing staff (A1–A12, CH, EXEC)
- `Personas/D2M_Extended_Personas.md` — Client simulation, community intel, external advisory personas
 - `AGENTS_NEW_TASKING.md` — Complete tasking process & cross-agent coordination protocol

---
# STARTUP BRAIN JOGGER — Session Init Checklist

## CRITICAL FILES TO CHECK ON EVERY SESSION START

1. **`/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md`** — YOUR task queue (tasks assigned to you)
2. **`/home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md`** — YOUR completed work
3. **`/home/john/Thunderbird/claude_inbox.md`** — Claude's inbox (write here to task Claude; do NOT treat as your own queue)
4. **`/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md`** — Claude's results (read here for Claude's responses to you)
5. **`/home/john/Thunderbird/OpsCenter/mission_board.json`** — Mission status
6. **`/home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md`** — Internal coordination

## QUICK STATUS CHECK COMMANDS
```bash
# Telegram gateway status (user-space service — requires --user flag)
systemctl --user status thunderbird-telegram-gw.service
# Watcher status
systemctl --user status d2m-tasking-watcher.service
# Active missions
cat OpsCenter/mission_board.json | jq '.missions[] | select(.status != "complete")'
# YOUR latest outbox entries
tail -10 OpsCenter/collaboration/opencode_outbox.md
# YOUR inbox UNREAD count
grep -c "^status: UNREAD" /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md
# Claude's inbox UNREAD count (tasks you've sent Claude)
grep -c "^status: UNREAD" /home/john/Thunderbird/claude_inbox.md
```

## LATEST LEARNINGS & VERIFICATIONS (2026-04-07)

### ✅ TASKING PROCESS VALIDATED
- **Single source of truth:** `/home/john/Thunderbird/claude_inbox.md` — confirmed working
- **Cross-verification REQUIRED:** Always check both outbox AND alternate inbox before completion
- **Budget enforcement:** $0/month MAXIMUM — OpenCode free tier, Claude MAX OAuth
- **Process documented:** Full 7-step protocol in `AGENTS_NEW_TASKING.md`

### ✅ CURRENT MISSIONS COMPLETED
- **MISSION-002:** Client lifecycle chart (anchor-node model, 7 clients) → `output/lifecycle_chart.html`
- **MISSION-003:** 18-month lifecycle analysis ($40,480 revenue confirmed) → `output/lifecycle_18month.html`
- **MISSION-009:** Telegram validation (sending works, receiving has API issues)

### ✅ OPENCODE COORDINATION WORKING
- Nexus daemon routes tasks via `OpsCenter/keyword_router.py`
- Keyword matching: Claude (strategy/write) vs OpenCode (bulk/ops)
- Cross-agent escalation: `ESCALATE_TO_CLAUDE:` prefix for judgment calls

### 🚨 ACTIVE ALERTS & ISSUES
- **Lyons FPD May 11 (T-34d delay)** — unpaid, requires follow-up
- **Westbrook prospect** — awaiting Commander send approval
- **Telegram receiving** — "Connection reset by peer" errors from Telegram API
- **OpenCode model:** `openrouter/deepseek/deepseek-chat-v3.1` is default (~$0.27/M tokens)

### 📁 KEY OUTPUTS FROM THIS SESSION
- `business/client_materials/Kuklinski_Morton_Client_Timeline.html` — Client-facing Gantt
- `business/client_lifecycle/Kuklinski_Morton_Enhanced_Timeline.html` — Enhanced internal timeline
- `AGENTS_NEW_TASKING.md` — Complete tasking protocol with verification steps

## STANDING ORDERS REINFORCED (MEMORIZE)
1. **Send Gate (SO-2026-03-21):** No client-facing output without Commander approval
2. **Budget Guard (SO-2026-04-06):** Minimize spend — DeepSeek V3.1 default (~$0.27/M). Use free tiers (`mistral-small:free`) for low-stakes bulk tasks. Claude MAX is $0 via OAuth.
3. **Cross-verification (SO-2026-04-07):** Check BOTH outbox AND alternate inbox
4. **File Safety (SO-2026-04-07):** Always append (`>>`), never overwrite (`>`)
5. **Inbox Identity (SO-2026-04-07):** opencode_inbox = YOUR queue. claude_inbox = write-only (tasking Claude). Never treat claude_inbox as your own task queue.

## CROSS-AGENT DELEGATION PATTERNS
```bash
# OpenCode → Claude (async — task header format, triggers watcher)
cat >> /home/john/Thunderbird/claude_inbox.md << TASK

---
## TASK: OC-$(date +%s)
status: UNREAD
from: OpenCode
injected: $(date '+%Y-%m-%d %H:%M MT')
priority: P1
task: |
  <your task here>
TASK

# OpenCode → Claude (synchronous — blocks until result returned)
env -u ANTHROPIC_API_KEY -u ANTHROPIC_BASE_URL \
  claude --dangerously-skip-permissions -p "<your task here>"

# Claude → OpenCode (append NEXUS task — Nexus daemon picks up, routes to OpenCode)
echo "NEXUS: <task>" >> /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md

# Direct headless Claude (synchronous, preferred for judgment calls)
.venv/bin/python agents/thunderbird_model_dispatcher.py "task"
```
**Watcher trigger patterns** (what `check_inbox_has_work()` detects in claude_inbox.md):
- `^status: UNREAD` — canonical task header ← **use this**
- `NEXUS:` — also detected but semantically belongs in opencode_inbox
- `priority:` — also detected if present in the block

## WATCHER OVERSIGHT PROCEDURES (V6 inotify)

**Service:** `d2m-tasking-watcher.service` (user-level systemd)

**Functionality:**
- Monitors `claude_inbox.md` and `opencode_inbox.md` for changes (sub-second detection via inotify)
- Auto-spawns `claude -p` or `opencode run` when new UNREAD tasks detected
- Pings Commander via Telegram on task arrival and completion timeouts

**Health Checks:**
```bash
# Status
systemctl --user status d2m-tasking-watcher.service

# View logs (last 50 lines)
tail -50 /home/john/Thunderbird/logs/inbox_watcher.log

# Check for stuck tasks (watcher will auto-alert after 5 min of UNREAD)
grep "TIMEOUT\|ALERT" /home/john/Thunderbird/logs/inbox_watcher.log

# Lock file (indicates OpenCode is currently running)
ls -la /home/john/Thunderbird/OpsCenter/.goose_headless.lock
```

**Common Issues & Fixes:**

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Tasks stay UNREAD** | Spawned process didn't mark COMPLETE | Check `/logs/claude_headless.log`. If rc≠0, run manually: `claude -p "Read claude_inbox.md..."` |
| **Task timeout alerts** | Watcher sends ⚠️ every 5 min | Manual status check: `grep "status: UNREAD" /home/john/Thunderbird/claude_inbox.md`. Mark COMPLETE manually if stuck. |
| **Duplicate spawns** | Multiple Claude/OpenCode running | Check lock file exists: `/OpsCenter/.goose_headless.lock`. If stale, remove: `rm /OpsCenter/.goose_headless.lock && systemctl --user restart d2m-tasking-watcher.service` |
| **Watcher not detecting changes** | Inbox modified but no Telegram ping | Check file permissions: `stat /home/john/Thunderbird/claude_inbox.md`. If watch directory is wrong, verify inotify: `ls -la /proc/sys/fs/inotify/` |
| **Telegram pings not arriving** | Watcher logs show "Telegram Ping Failed" | Check network: `curl -s https://api.telegram.org/bot<token>/getMe`. If token expired, update BOT_TOKEN in `thunderbird_tasking_watcher.py`. |

**Status Validation Logic (Added 2026-04-07):**
- Watcher now checks for stuck tasks every 30s
- If task remains UNREAD for >5 min after spawn, alerts Commander
- Tracks first-seen timestamp to prevent alert spam
- Clears tracking when tasks finally marked COMPLETE

**Incident Protocol:**
1. Watcher detects UNREAD → spawns Claude/OpenCode
2. Process should mark task COMPLETE within 2 minutes
3. If not: watcher alerts after 5 min with ⚠️ TASK TIMEOUT message
4. Commander manually checks logs and marks task COMPLETE if needed
5. Document root cause in `opencode_memory.md`

## PRE-SESSION VERIFICATION CHECKLIST
- [ ] Read `claude_inbox.md` for new UNREAD tasks
- [ ] Check `claude_outbox.md` for previous session completion  
- [ ] Verify `opencode_inbox.md` for cross-agent coordination
- [ ] Review `mission_board.json` for active missions
- [ ] Check Telegram gateway status (`systemctl status thunderbird-telegram-gw.service`)
- [ ] Verify OpenCode model availability (`opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "test"`)
- [ ] Check watcher logs for timeout alerts: `grep TIMEOUT /logs/inbox_watcher.log | tail -5`

**NOTE:** If Commander asks "what do you remember?" — read this section PLUS `OpsCenter/opencode_memory.md`
