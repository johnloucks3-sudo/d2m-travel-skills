# HALE Telegram Channels Guide
**For**: HALE-OC (OpenCode instance) | HALE-CC (Claude Code instance)  
**Date**: 2026-07-08  
**Purpose**: Unified C2 fabric coordination, message routing, OC-CC info sharing  
**Gateway**: `OpsCenter/thunderbird_telegram_gw.py` (3-bot unified architecture)

---

## 🤖 TELEGRAM BOT ARCHITECTURE

### Three Bots, One Process

| Bot Name | Token ID | Engine | Identity | Audience | Primary Use |
|----------|----------|--------|----------|----------|-------------|
| **D2MC2C** | 8754681793 | Claude `-p` | Hale (COS) | Commander only | Wing operations, Hale responses, system status |
| **Dani** | 8723918695 | Claude `-p` | Dani Moreau | Clients + Commander | Client comms, proposals, TP drafts |
| **GooseD2M** | (TBD — check .env) | OpenCode | OpenCode Hale | OpenCode + Commander | OC tasks, background work, headless dispatch |

**Message Flow**:
```
Commander message
    ↓
Telegram API (getUpdates poll, 3 threads)
    ↓
Bot whitelist check (COMMANDER_ID only)
    ↓
Context loader (rolling 10-turn history)
    ↓
Engine dispatch (Claude Claude Code / OpenCode headless)
    ↓
Response formatter (5-stage pipeline)
    ↓
Send to Commander (0.5s gaps between chunks)
    ↓
Append to rolling context file
```

---

## 📡 CHANNEL PURPOSES & ROUTING

### D2MC2C BOT — Hale COS (Claude Code)
**Purpose**: Hale responses, system status, operational coordination  
**Audience**: Commander only  
**Use Cases**:
- ✅ Morning briefs / situational reports
- ✅ Status checks (`/status`)
- ✅ Operational decisions
- ✅ System health alerts
- ✅ Staff feedback summaries
- ✅ Mission board updates
- ✅ Coordination between CC and OC

**Example Flow**:
```
Commander → "Hale, status on the McLeod voyage"
    ↓ (D2MC2C bot routes to Claude Code)
    ↓ Hale (CC) reads hale_state.json + mission board
    ↓ Response via D2MC2C → Commander
```

### DANI BOT — Client Communications
**Purpose**: Client-facing communications, proposals, travel planning  
**Audience**: Clients + Commander (CC oversight)  
**Use Cases**:
- ✅ Client email drafts (reviewed before send)
- ✅ TP (Touchpoint) communications
- ✅ Itinerary updates
- ✅ Booking confirmations
- ✅ Special requests / accommodations

**Example Flow**:
```
Commander → "Dani, draft Spencer voyage preview email"
    ↓ (Dani bot routes through Claude)
    ↓ Dani persona generates client-voice copy
    ↓ Response via Dani bot → Commander review
    ↓ Commander sends via Gmail or approves for auto-send
```

### GOOSED2M BOT — OpenCode / Background Work
**Purpose**: Long-running tasks, background automation, headless Claude dispatch  
**Audience**: OpenCode (OC) + Commander (monitoring only)  
**Use Cases**:
- ✅ Background data pulls (Centrav, portals, TESS)
- ✅ Batch processing (dossier updates, invoice scraping)
- ✅ Scheduled tasks (fare watches, CI sweeps)
- ✅ Headless Claude spawns
- ✅ Async agent work

**Example Flow**:
```
OC (OpenCode) → "Poll Centrav for Kuklinski fares, update dossier"
    ↓ (Runs in background via GooseD2M)
    ↓ Completes async, posts result to Telegram
    ↓ Commander notified via alert
```

---

## 🔗 OC-CC COORDINATION PROTOCOL

### When OC and CC Must Talk

**Scenario 1: OC has data CC needs**
```
OC completes fare pull → OC posts summary to D2MC2C (Hale CC channel)
CC reads Telegram + hale_bus_state.json (shared handoff file)
CC compiles into brief/report
```

**Scenario 2: CC dispatches work to OC**
```
Hale (CC) writes task to hale_bus/hale_bus_state.json (OC-CC handoff queue)
Posts routing note to GooseD2M (optional)
OC reads bus file on next heartbeat cycle
OC executes task, writes results back to bus
```

**Scenario 3: Status sync**
```
Hale (CC) posts /status to D2MC2C
Hale (OC) reads Telegram + hale_bus (shared state)
Both update hale_state.json (primary source of truth)
```

### The Shared State Files (CI Fabric)

| File | Owner | Readers | Purpose |
|------|-------|---------|---------|
| `hale_state.json` | Both | Both | Live operational state (FPD alerts, open tasks, mission board) |
| `hale_bus/hale_bus_state.json` | Both | Both | Inter-instance handoff queue (CC→OC work, OC→CC results) |
| `OpsCenter/session_context_latest.md` | Both | Both | Session checkpoint (what was happening last) |
| `Telegram context files` | Both | Both | Rolling 10-turn message history per bot |

---

## 💬 TELEGRAM COMMANDS (All Bots)

### Universal Commands
```
/new      — Clear rolling context, start fresh session
/status   — Show wing health + last activity timestamp
/help     — Show available commands (bot-specific)
```

### Model Override Keywords (D2MC2C only)
```
OPUS: [task]       → Route to Claude Opus (expensive, slower, deeper reasoning)
Sonnet: [task]     → Route to Claude Sonnet (balanced)
HAIKU: [task]      → Route to Haiku (cheap, fast)

(Default: Haiku with auto-escalation to Sonnet on strategy keywords)
```

### External Model Prefixes (Any bot)
```
GROK: [task]       → xAI Grok 4.1 Fast (~$0.20/M tokens)
DEEPSEEK: [task]   → DeepSeek V4 Pro (~$0.305/M)
GEMINI: [task]     → Gemini 3.1 Flash Lite (~$0.25/M — cheapest, preferred)
LLAMA: [task]      → Llama 4 Maverick (~$0.15/M)
GPT: [task]        → GPT-4.1 Mini (~$0.40/M)
MISTRAL: [task]    → Mistral Small (~$0.05/M — absolute cheapest)
```

---

## 🚀 RECOMMENDED WORKFLOWS

### Pattern A: Daily Status Sync (CC ↔ OC)

**07:00 MT** - Hale (CC) posts morning brief via D2MC2C  
**08:00 MT** - Hale (OC) reads brief + heartbeat check, updates hale_state.json  
**Throughout day** - Both instances read/update shared state files  
**17:00 MT** - EOD brief posted via D2MC2C  

### Pattern B: Data Pull (OC → CC)

1. **OC** runs `scripts/fare_watch_amadeus.py` (background)
2. **OC** writes results to `OpsCenter/fare_watches/last_check_amadeus.json`
3. **OC** posts summary to GooseD2M: "Fare watch complete: 26 routes checked, 4 alerts"
4. **CC** reads Telegram + JSON file
5. **CC** compiles alerts into brief, sends via D2MC2C

### Pattern C: Task Dispatch (CC → OC)

1. **CC** needs: "Pull Regent portal booking status for McLeod 2984034"
2. **CC** writes to `hale_bus_state.json`: task queue entry with route + date
3. **CC** posts routing note to GooseD2M (optional): "McLeod task queued"
4. **OC** reads hale_bus on next heartbeat, sees task
5. **OC** executes: scrapes Regent, updates dossier
6. **OC** writes result back to hale_bus
7. **CC** reads result on next scan, incorporates into next report

---

## ⚙️ TECHNICAL SETUP

### File Locations
```
Gateway:           /home/john/Thunderbird/OpsCenter/thunderbird_telegram_gw.py
Access whitelist:  /home/john/Thunderbird/OpsCenter/telegram_access.json
Formatter:         /home/john/Thunderbird/OpsCenter/thunderbird_tg_formatter.py
Hale router:       /home/john/Thunderbird/OpsCenter/telegram_hale_router.py
Context store:     /home/john/Thunderbird/OpsCenter/telegram_context_*.json
```

### Bot Credentials
```
Location:  /home/john/Thunderbird/.env
Keys:      TELEGRAM_D2MC2C_TOKEN
           TELEGRAM_DANI_TOKEN
           TELEGRAM_GOOSED2M_TOKEN (or similar)
           
Check:     grep TELEGRAM_ .env | head -10
```

### Health Monitoring
```
Script:    /home/john/Thunderbird/OpsCenter/telegram_health_check.py
Run:       python3 telegram_health_check.py
Checks:    Bot connectivity, token validity, message queue depth
```

---

## 🛡️ SECURITY & POLICY

### Access Control
- **Commander ID only**: 7554895206 (hardcoded in `telegram_access.json`)
- **All other Telegram IDs**: Rejected silently
- **No public bot**: D2MC2C is private (token-gated)

### Message Policies
- **No client data via Telegram**: Use email (WF-17 gate) for sensitive booking info
- **No credentials in chat**: Never paste API keys, tokens, or passwords
- **Dani bot**: CC can monitor client comms but does not send directly

### Rate Limits
- **API quota**: Telegram's 30 msg/sec per account (rarely hit)
- **Backoff**: 0.5s gap between chunks to avoid throttling
- **Timeout**: 180s per headless Claude spawn (long-running tasks only)

---

## 📋 CHECKLIST FOR HALE-OC SETUP

- [ ] Verify GooseD2M bot token in `.env`
- [ ] Test bot connectivity: `python3 OpsCenter/telegram_health_check.py`
- [ ] Confirm Commander ID (7554895206) in access whitelist
- [ ] Read `hale_bus/hale_bus_state.json` on startup (mandatory)
- [ ] Post status to D2MC2C on first run
- [ ] Subscribe to `hale_decisions.md` updates (log handoff work)
- [ ] Check Telegram every heartbeat cycle (~hourly)

---

## 📞 EMERGENCY PROCEDURES

### Bot is unresponsive
1. Check token in `.env` (expired? rotated?)
2. Run `telegram_health_check.py`
3. Restart gateway: `systemctl restart thunderbird-telegram-gw.service`
4. If still down: check Telegram API status page

### Message not delivered
1. Confirm Commander ID: `grep COMMANDER_ID OpsCenter/thunderbird_telegram_gw.py`
2. Check message formatting (no extra pipes, brackets, etc.)
3. Verify context file exists: `ls OpsCenter/telegram_context_*.json`

### Lost sync between OC and CC
1. Hale (CC) posts status to D2MC2C
2. Hale (OC) reads Telegram + checks hale_bus_state.json
3. Both write to shared files
4. Restart context sync: `rm OpsCenter/telegram_context_*.json` (will regenerate)

---

## 🔄 INFO SHARING — OC-CC BEST PRACTICES

### What to share via Telegram
- ✅ Status updates
- ✅ Alerts (price drops, FPD approaching, etc.)
- ✅ Handoff notifications ("task queued for OC")
- ✅ Summary of work completed

### What NOT to share via Telegram
- ❌ Raw JSON (too large)
- ❌ Client PII (email, phone, address)
- ❌ Booking references (ticket numbers, confirmation codes)
- ❌ Full dossier content

### How to share large data
- Write to file
- Post 1-line summary to Telegram
- CC/OC reads file directly (both have access)

---

**Version**: 1.0 | **Last Updated**: 2026-07-08  
**Author**: Hale COS | **For**: HALE-OC instance coordination
