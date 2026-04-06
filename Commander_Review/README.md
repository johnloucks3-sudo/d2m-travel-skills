# OpsCenter — Thunderbird Wing C2 Architecture

**Status:** LIVE as of 29 MAR 2026
**Author:** COS (Hale) + Commander

---

## Architecture Overview

```
Commander's Phone (Telegram)
        │
        ▼
┌───────────────────┐
│ telegram_pager_c2  │  ← Dumb pager. Instant "Roger." Writes to queue.
│ (python-telegram)  │     NEVER calls an LLM. NEVER blocks.
└────────┬──────────┘
         │ writes JSON
         ▼
┌───────────────────┐
│ 01_TASK_QUEUE.json │  ← Shared file queue. Any producer can write.
└────────┬──────────┘
         │ polls every 5s
         ▼
┌───────────────────┐     ┌─────────────────┐
│ task_processor.py  │────▶│ Groq (free)     │  Operational, summaries, routing
│ (Hale-Loop daemon) │    │ Gemini (cheap)   │  Briefs, research, bulk text
│                    │    │ Local Python     │  Deadline checks, format checks
│                    │    └─────────────────┘
│                    │
│  client_facing? ───┼───▶ 03_CLAUDE_MAX_QUEUE.json  (picked up by Claude Code)
│                    │
│     result ────────┼───▶ Telegram C2 Bot → Commander's phone
└───────────────────┘
```

## Files

| File | Purpose | Status |
|------|---------|--------|
| `telegram_pager_c2.py` | Telegram bot — receives messages, writes queue | **LIVE** (systemd) |
| `task_processor.py` | Queue consumer — classifies, routes, responds | **LIVE** (systemd) |
| `01_TASK_QUEUE.json` | Shared task queue (any → Hale-Loop) | Active |
| `03_CLAUDE_MAX_QUEUE.json` | High-value tasks waiting for Claude Code | Active |
| `02_SCIF_PUZZLES.json` | Reserved for future SCIF use | Empty |
| `00_COMMAND_LOG.md` | Append-only command log | Active |
| `thunderbird_overwatch.sh` | Bash wrapper — sources env, launches Python | **LIVE** |
| `notify_commander.sh` | Terminal bell + goose ASCII art | Fun |
| `dani_engine.py` | DEPRECATED — logic moved to task_processor | Dead code |
| `naia_bridge.py` | DEPRECATED — logic moved to task_processor | Dead code |
| `switchblade_report.md` | Historical diagnostic — env isolation fix | Archive |

## Division of Labor — Engine Routing

**Principle:** Claude MAX tokens are scarce (5-hour rate window). Never burn them on routine work.

| Engine | Cost | Tasks | When Used |
|--------|------|-------|-----------|
| **Local Python** | $0 | Classification (keyword matcher), queue mechanics, deadline checks, format checks | Every task (classification step) |
| **Groq** (Llama 3.3 70B) | Free tier | Operational queries, summaries, research, data extraction | Most Telegram messages |
| **Gemini 2.5 Flash** | ~$0.30/1M tokens | Morning briefs, research synthesis, bulk text | Scheduled briefs |
| **Claude MAX** (OAuth) | $0 but rate-limited | Client emails, proposals, voice-matched copy, creative, strategic, crisis | QUEUED only — never called by daemon |
| **DeepSeek** | ~$0.14/1M tokens | Analytics, deep extraction (PII-fenced, never receives client PII) | Scalpel/SWITCHBLADE |

### Classification → Engine Map

```
commander_message arrives
    │
    ├── classify_task() → operational/classification/summarization/research/extraction
    │       └── Groq handles it (free, fast, ~1s response)
    │
    ├── classify_task() → morning_brief
    │       └── Gemini handles it (cheap, good at synthesis)
    │
    └── classify_task() → client_facing/creative/strategic/crisis/code/voice
            └── QUEUED to 03_CLAUDE_MAX_QUEUE.json
                Commander gets Telegram notice: "Queued for Claude Code session"
                Claude Code (or Goose) picks up the queue next session
```

## Systemd Services

| Service | Unit File | Status |
|---------|-----------|--------|
| `thunderbird-telegram-c2` | Dumb pager | **Running** |
| `thunderbird-overwatch` | Hale-Loop (Python processor) | **Running** |
| `d2m-telegram-c2` | OLD competing bot | **Disabled** (was fighting for token) |

## Goose Handoff — What Needs Work

### Ready for Goose (no Claude MAX needed):

1. **Wire `innovation_scan` handler** to call the actual `thunderbird_innovation_scanner.py` instead of a Gemini stub
2. **Wire `morning_briefing` handler** to call the real morning brief pipeline (MCP tools)
3. **Wire `fpd_alert` handler** to pull real dossier deadline data and format alerts
4. **Add new task types** to the handler dispatch table in `task_processor.py`:
   - `sentinel_sweep` → call `thunderbird_overwatch.run_sentinel_sweep()`
   - `dossier_check` → call overwatch dossier currency check
   - `commission_audit` → call overwatch commission math check
5. **Clean up dead code:** `dani_engine.py` and `naia_bridge.py` can be deleted (logic lives in task_processor now)
6. **Add Gemini error handling** in `_call_gemini` fallback path

### Needs Claude Code (MCP access required):

1. **Process `03_CLAUDE_MAX_QUEUE.json`** — draft client emails with voice matching via MCP gmail tools
2. **Process `send_draft` approvals** — use MCP `gmail_send_draft` to actually send approved drafts
3. **Naia bridge replacement** — format and send Telegram messages with inline keyboards (approve/reject buttons)

### Infrastructure:

1. **Log rotation** for `process.log` and `overwatch.log` — add to `thunderbird-logrotate`
2. **Health check** — add a `/health` endpoint or heartbeat timer that verifies the daemon is alive
3. **Queue persistence** — current JSON file approach is fine for low volume but consider SQLite if task volume grows
