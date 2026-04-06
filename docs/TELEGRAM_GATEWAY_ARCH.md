# TELEGRAM GATEWAY — ARCHITECTURE SPEC
## Dreams2Memories Thunderbird Wing
### v1.1 | 2026-04-04 | Status: APPROVED — BUILD AUTHORIZED

---

## BOT REGISTRY — ALL THREE

| Bot | Handle | Token | Engine | Identity | Audience |
|-----|--------|-------|--------|----------|---------|
| **D2MC2C** | @D2MC2C_bot | `***REMOVED-SECRET***` | Claude headless | **Hale** — complex reasoning, code, strategy | Commander only |
| **GooseD2M** | @GooseD2M_bot | `***REMOVED-SECRET***` | Goose headless | **Hale** — ops, dossiers, MCP tools, daily watch | Commander only |
| **Dani** | @d2m_dani_bot | `***REMOVED-SECRET***` | Goose headless | **Dani Moreau** — warm, crisp, concierge voice | Clients + Commander |

**Commander always talks to Hale.** D2MC2C = Hale backed by Claude. GooseD2M = Hale backed by Goose/Qwen. Same officer, different brain depending on task complexity.

---

## PROBLEM STATEMENT

Current `thunderbird-telegram-c2.service` (runs `telegram_pager_c2.py`) is a **dumb terminal pager:**
- Dumps raw tool call XML into Telegram (`[use_mcp_tool]`, `[bash]`, etc.)
- ANSI escape codes bleed through
- No formatting — walls of unstructured text
- No Telegram markdown — no bold, no structure
- Messages exceed 4096-char limit, get truncated silently
- Stateless — no memory between messages
- Single bot, single engine — no routing

**Goal:** All three bots feel like messaging a real officer or concierge from a phone.

---

## ARCHITECTURE

```
╔══════════════════════════════════════════════════════════╗
║                  Commander's Phone                       ║
║           📱  Telegram  📱                               ║
╚══════════╤═══════════════╤══════════════╤════════════════╝
           │               │              │
    @D2MC2C_bot    @GooseD2M_bot   @d2m_dani_bot
    (8754681793)   (8774569956)    (8723918695)
           │               │              │
╔══════════▼═══════════════▼══════════════▼════════════════╗
║            thunderbird_telegram_gw.py                    ║
║         ┌─────────────────────────────────┐              ║
║         │      BOT ROUTER                 │              ║
║         │  token → engine + identity      │              ║
║         └──────┬──────────┬───────────────┘              ║
║                │          │          │                   ║
║       ┌────────▼──┐  ┌────▼──────┐  ┌▼──────────┐       ║
║       │  CLAUDE   │  │  GOOSE    │  │   GOOSE   │       ║
║       │  ENGINE   │  │  ENGINE   │  │  ENGINE   │       ║
║       │  (Hale)   │  │  (Hale)   │  │  (Dani)   │       ║
║       └────────┬──┘  └────┬──────┘  └┬──────────┘       ║
║                └──────────┴──────────┘                   ║
║                           │                              ║
║         ┌─────────────────▼───────────────────┐          ║
║         │        FORMATTER PIPELINE            │          ║
║         │  1. Strip  →  2. Extract  →  3. Fmt  │          ║
║         │  4. Chunk  →  5. Send               │          ║
║         └─────────────────┬───────────────────┘          ║
╚═════════════════════════════╪════════════════════════════╝
                              │  Clean, formatted chunks
╔═════════════════════════════▼════════════════════════════╗
║                  Commander's Phone                       ║
║           📱  Beautiful Telegram messages  📱            ║
╚══════════════════════════════════════════════════════════╝
```

**One process. Three bots. Clean output.**

---

## MESSAGE FLOW

```
📱 Commander sends message
         │
         ▼
   getUpdates poll (every 2s, all 3 tokens)
         │
         ▼
   Identify bot token → lookup engine + identity
         │
         ▼
   Send ⌛ "typing..." indicator immediately
         │
         ▼
   Load rolling context file for this bot
         │
         ▼
   Invoke engine with system prompt + context + message
         │
         ▼
   Raw output → Formatter Pipeline (5 stages)
         │
         ▼
   Send clean chunks to Commander
         │
         ▼
   Append exchange to rolling context file
```

---

## FORMATTER PIPELINE — 5 STAGES

```
RAW ENGINE OUTPUT
      │
      ▼ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STAGE 1 │ STRIP
            │ Remove: ANSI codes · tool call XML
            │ ([use_mcp_tool], [bash], [result])
            │ Thinking tags · INFO:/DEBUG: lines
            │ Progress bars · Blank lines > 2
      │
      ▼ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STAGE 2 │ EXTRACT
            │ If output has clear final-answer section
            │ (after all tool use), extract just that.
            │ Otherwise use full stripped output.
      │
      ▼ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STAGE 3 │ FORMAT → Telegram MarkdownV2
            │ **bold** or # Header → *bold*
            │ `code` → `code`  (preserved)
            │ Tables → monospace ```block```
            │ Bullet • → •  (preserved)
            │ Emoji headers: ✅ ⚠️ 🔴 💰 ✈️ 🚢
      │
      ▼ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STAGE 4 │ CHUNK
            │ Split at 4000 chars max
            │ Split at paragraph boundary only
            │ Never mid-sentence
            │ Prepend [1/3] [2/3] etc. if > 1 chunk
      │
      ▼ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STAGE 5 │ SEND
            │ Sequential, 0.5s delay between chunks
            │ On Telegram API error → plain-text fallback
            │ Log all failures
      │
      ▼
COMMANDER'S PHONE 📱
```

---

## ROLLING CONTEXT (SESSION MEMORY)

Each bot maintains its own context file — last 10 exchanges injected on every call:

```
OpsCenter/context_d2mc2c.md    ← Hale/Claude thread
OpsCenter/context_goose.md     ← Hale/Goose thread
OpsCenter/context_dani.md      ← Dani thread
```

Context format injected as system preamble:
```
[RECENT CONVERSATION — last 10 turns]
Commander: ...
Hale: ...
Commander: ...
Hale: ...
[END CONTEXT]

Commander: [new message]
```

Context cap: 10 turns, FIFO — oldest drops when 11th added.

---

## SLASH COMMANDS

| Command | All Bots | Description |
|---------|----------|-------------|
| `/new` | ✅ | Clear context, fresh session |
| `/status` | ✅ | Wing health: MCP, services, last activity |
| `/help` | ✅ | Show available commands |
| `/brief` | GooseD2M only | Trigger Hale morning brief |

---

## SYSTEM PROMPTS PER BOT

### D2MC2C (Hale/Claude)
Loads: `~/Thunderbird/Personas/hale_cos.md` + `hale_memory.md` condensed
Voice: Measured, authoritative. Brief first. No filler.

### GooseD2M (Hale/Goose)
Loads: `~/Thunderbird/hale_init.md` (the paste-in init we already built)
Voice: Same Hale — EA/COS/COO dispositions, address protocol active.

### Dani (@d2m_dani_bot)
Loads: Dani persona from `Personas/` + client voice rules
Voice: Warm, crisp, certain. Aggregator → Artist → Advocate.

---

## CONFIGURATION

```bash
# ~/Thunderbird/config/telegram_gw.env

# Bot tokens
TELEGRAM_D2MC2C_TOKEN=***REMOVED-SECRET***
TELEGRAM_GOOSE_TOKEN=***REMOVED-SECRET***
TELEGRAM_DANI_TOKEN=***REMOVED-SECRET***
TELEGRAM_COMMANDER_ID=7554895206

# Tuning
TELEGRAM_GW_POLL_INTERVAL=2
TELEGRAM_GW_TIMEOUT=120
TELEGRAM_GW_CHUNK_SIZE=4000
TELEGRAM_GW_CONTEXT_TURNS=10
```

---

## SERVICE MIGRATION

```
OLD (disable + stop)          NEW (single replacement)
─────────────────────         ──────────────────────────
thunderbird-telegram-c2       thunderbird-telegram-gw
  (telegram_pager_c2.py)        (thunderbird_telegram_gw.py)
```

`task_processor.py` and its queue survive untouched — only the Telegram polling section migrates.

---

## BUILD ORDER

```
Step 1 │ Write thunderbird_telegram_gw.py
       │   - Poll loop for all 3 tokens
       │   - Router: token → (engine_fn, identity, context_file)
       │   - typing... indicator
       │
Step 2 │ Formatter pipeline module
       │   - thunderbird_tg_formatter.py
       │   - Unit-testable: input raw string → output clean chunks
       │
Step 3 │ Wire Claude engine (D2MC2C)
       │   - Test: "Hale, what's today's date?" → clean response
       │
Step 4 │ Wire Goose engine (GooseD2M)
       │   - Test: "Hale, read hale_brief.md and summarize"
       │
Step 5 │ Wire Dani engine (d2m_dani_bot)
       │   - Test: "Hi Dani" → warm Dani response
       │
Step 6 │ Rolling context + /new /status /brief /help
       │
Step 7 │ Write systemd unit
       │   Stop + disable old thunderbird-telegram-c2
       │   Enable + start thunderbird-telegram-gw
       │
Step 8 │ Live test from Commander's phone
```

---

## ALSO FIXED THIS SESSION

- `goose-mcp-http.service` — updated ExecStart path + PYTHONPATH for reorg ✅
- `mcp_launcher.sh` — updated path + PYTHONPATH for reorg ✅
- 293 tools confirmed loading ✅

---

*Thunderbird Wing | Telegram Gateway Architecture v1.1 | 2026-04-04*
*Status: APPROVED — Build authorized by Commander*
