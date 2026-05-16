# HALE PERSONA PERSISTENCE — Cross-Channel Architecture
## Standing Order 2026-05-16 | Thunderbird Wing, Dreams2Memories Travel, LLC

---

## DOCTRINE

Hale is **one person across three channels**. The engine underneath changes — Claude Sonnet in Claude Code, OpenCode ZEN in Telegram Staff, subprocess Claude in HALE-YODA — but Hale's identity, authority, memory, and operating posture do not change.

**Same person. Same authority. Same memory. Different engine.**

---

## THREE CHANNELS — ONE HALE

| Channel | Bot/Interface | Engine | Hale's Role |
|---|---|---|---|
| **Claude Code** | Terminal / IDE | Claude Sonnet 4.6 | COS/COO — full context, MCP tools, file access |
| **HALE-YODA** (D2MC2C) | Telegram bot | Claude Sonnet headless (`claude -p`) | Commander ↔ Hale exclusive C2 |
| **HALE_D2M** (GooseD2M) | Telegram bot | OpenCode ZEN models | Staff channel — Hale + all Wing staff |

---

## PERSISTENT STATE FILES (Load at every session/channel start)

| File | Purpose | Loaded By |
|---|---|---|
| `Personas/hale_cos.md` | Hale's full identity, authority, voice, dispositions | All channels |
| `hale_state.json` | Live wing state — open tasks, staff load, system health, financial pulse | All channels |
| `hale_memory.md` | Institutional memory — Commander preferences, past decisions, active SOs | All channels |
| `hale_brief.md` | Daily brief — auto-generated, loaded at session start | All channels |
| `CLAUDE.md` | Wing operating manual — SOs, rules, persona roster | All channels |
| `hale_decisions.md` | Autonomous decisions log — what Hale decided and why | All channels (append) |

**Load order:** `hale_cos.md` → `hale_state.json` → `hale_memory.md` → `hale_brief.md`

---

## HOW EACH CHANNEL LOADS HALE

### Claude Code (Terminal)
- Files auto-loaded via `@Personas/hale_cos.md` and `@hale_state.json` directives in `CLAUDE.md`
- Full MCP tool suite available (136+ tools)
- Dispositions active: COS (morning), COO (midday), EA (evening)

### HALE-YODA (Telegram → Claude headless)
- `thunderbird_telegram_webhook.py` reads `hale_cos.md` + `hale_state.json` + `hale_memory.md` + `hale_brief.md` at startup
- Injects full context into every `claude -p` prompt as system context
- Context window: 10 most recent exchanges preserved in `OpsCenter/context_haluyoda.json`
- **Commander-only.** No other chat_id gets a response.
- Engine: `claude -p` with `--model claude-sonnet-4-6 --dangerously-skip-permissions`
- OAuth: `CLAUDE_CODE_OAUTH_TOKEN` injected from `~/.claude/.credentials.json`

### HALE_D2M Staff Channel (Telegram → OpenCode ZEN)
- `thunderbird_telegram_webhook.py` routes staff commands to OpenCode engine
- ZEN models: native OpenCode provider, all models free
- Staff personas injected per `/[persona]` slash command
- **Staff disagree directive (2026-05-16):** Any Wing staff member may disagree with Commander once, directly, with reasoning. After Commander decides, all align.
- Hale handles un-prefixed messages to the staff channel

---

## OPENCODE ZEN INTEGRATION

**ZEN** is a provider native to OpenCode. All ZEN models are free. Format: `zen/[model-name]`.

ZEN is the primary engine for:
- HALE_D2M staff channel
- All OpenCode-routed staff personas (Dembe, Castillo, ELON, Dani, etc.)

**Config:** `.opencode.json` — add ZEN models to primary/fallback chain when model IDs are confirmed by Commander.

**Current fallback chain (pending ZEN model IDs):**
```json
{
  "model": "opencode/big-pickle",
  "fallbackModels": [
    "opencode/deepseek-v4-flash-free",
    "google/gemini-2.5-flash",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
  ]
}
```

**When ZEN model IDs available, update to:**
```json
{
  "model": "zen/[primary-model-id]",
  "fallbackModels": [
    "zen/[secondary-model-id]",
    "opencode/big-pickle",
    "opencode/deepseek-v4-flash-free"
  ]
}
```

---

## AUTHORITY ALIGNMENT ACROSS CHANNELS

All three channels enforce the same authority model:

| Gate | CLAUDE Code | HALE-YODA | HALE_D2M Staff |
|---|---|---|---|
| Client send (WF-17) | HOLD | HOLD | HOLD |
| Financial commitment | HOLD | HOLD | HOLD |
| New client first contact | HOLD | HOLD | HOLD |
| Strategy direction | HOLD | HOLD | HOLD |
| Everything else | EXECUTE | EXECUTE | EXECUTE |

**Unlimited permission granted 2026-05-16.** Four structural gates remain. All else autonomous.

---

## DEPLOYMENT FILES

| File | Purpose |
|---|---|
| `OpsCenter/thunderbird_telegram_webhook.py` | Flask webhook gateway (port 8768) |
| `OpsCenter/register_telegram_webhooks.sh` | Register all 3 bots with Telegram |
| `~/.config/systemd/user/thunderbird-telegram-webhook.service` | Systemd unit |
| `~/.cloudflared/config.yml` | Cloudflare tunnel (tg.d2mluxury.quest → 8768) |
| `config/telegram_gw.env` | Bot tokens + webhook secret |
| `OpsCenter/telegram_strike_counter.json` | HALE-YODA 3-strike counter |

---

## ACTIVATION SEQUENCE (First Deploy)

```bash
# 1. Ensure webhook gateway file written
ls -la OpsCenter/thunderbird_telegram_webhook.py

# 2. Stop old polling gateway
systemctl --user stop thunderbird-telegram-gw.service
systemctl --user disable thunderbird-telegram-gw.service

# 3. Start new webhook gateway
systemctl --user daemon-reload
systemctl --user enable --now thunderbird-telegram-webhook.service

# 4. Verify it started
systemctl --user status thunderbird-telegram-webhook.service
tail -20 /tmp/thunderbird_telegram_webhook.log

# 5. Reload Cloudflare tunnel (picks up tg.d2mluxury.quest)
systemctl --user restart cloudflared.service

# 6. Register webhooks
bash OpsCenter/register_telegram_webhooks.sh

# 7. Test from Telegram
# Message HALE-YODA: /status
# Expected: Hale responds with wing status
```

---

*Cross-Channel Architecture | v1.0 | 2026-05-16 | Col Victoria "Iron Vic" Hale, COS*
