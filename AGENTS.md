# AGENTS.md — Thunderbird OS

> Dreams2Memories Travel, LLC · Python automation + LLM ops · openSUSE Tumbleweed (YOGA 192.168.1.198)

## Session Init — Read First

On every session start, read these two files before doing anything else:

1. **`OpsCenter/opencode_memory.md`** — persistent session memory: what was built, what changed, operating agreement with Claude, key file locations, model stack. Append a summary of this session's work at the end when you close out.
2. **`Personas/ROSTER.md`** — wing staff index: who does what, who to route to, who owns client comms.

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
opencode                              # TUI, default model: qwen3.6-plus-free ($0)
opencode run "task"                   # headless one-shot
opencode run -m openrouter/anthropic/claude-sonnet-4.6 "task"  # Claude via OR
opencode web                          # browser UI (accessible from Chromebook/phone)
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
- Direct commits to `master` — 13 commits ahead of `origin/master` as of 2026-04-06
- `.gitignore` blocks: `creds/`, `*.db`, `*_token.json`, `*_state.json`, `storage/`, `*.zip`, `.playwright-mcp/`, archives, large binaries

## Operational Cadence

All automated via systemd timers (MDT):

| Time (MDT) | What |
|------------|------|
| 01:00 | **Agentic intel sweep** → `johnloucks3@gmail.com` (Claude Code/Goose/multi-model ecosystem) |
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
| **OpenCode** v1.3.17 | qwen3.6-plus-free (default) | $0 | Ops, bulk tasks, scanning |
| **OpenCode** + OpenRouter | claude-sonnet-4.6, grok-4, DeepSeek-R1 | pay/token | Heavy tasks, multi-model |
| **Claude Agent SDK** | Sonnet 4.6 | $0 (MAX) | Headless: `claude -p "..."` |
| **Nexus daemon** | Sonnet via API | ~$0.03/task | Keyword-routed task queue |

**Goose is decommissioned.** References to `goose-d2m`, `goose run`, or `~/.config/goose/` anywhere in docs are stale. Replace `goose run "X"` with `opencode run "X"`.

**OpenCode model IDs** (use with `-m`):
- `opencode/qwen3.6-plus-free` — free, good for ops/scanning
- `openrouter/anthropic/claude-sonnet-4.6` — Claude via OpenRouter
- `togetherai/deepseek-ai/DeepSeek-R1` — reasoning
- `xai/grok-4` — Grok

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
