# OPENCODE INITIALIZATION — THUNDERBIRD WING v1
**Paste this at the start of every OpenCode session, or reference as AGENTS.md.**
**Working directory:** `/home/john/Thunderbird`
**Last rebuilt:** 2026-04-06

> **Note:** GOOSE_INIT.md is DEPRECATED. OpenCode replaces Goose entirely.
> This file replaces GOOSE_INIT.md for all OpenCode sessions.

---

## BRAIN INDEX — WHAT TO READ & WHERE

You are stateless between sessions. This index tells you what to read, in what
order, so you can be operational within 60 seconds.

### TIER 0: READ FIRST (Non-Negotiable — Do These Before ANYTHING Else)

```bash
cat /home/john/Thunderbird/OpsCenter/opencode_memory.md
cat /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md
cat /home/john/Thunderbird/OpsCenter/collaboration/blackboard.md
cat /home/john/Thunderbird/session_autosave_latest.md
```

- **opencode_memory.md** — Accumulated context from prior sessions, standing orders, what was built
- **opencode_inbox.md** — Tasks assigned to you from the wing / Nexus daemon
- **blackboard.md** — Wing-wide shared state (budget, active tasks, open items)
- **session_autosave_latest.md** — Where the last session left off

**Read them. Then act on what they say.**

### TIER 1: IDENTITY & AUTHORITY (Read Once Per Session)

```bash
cat /home/john/Thunderbird/Personas/hale_cos.md          # Hale — who you serve
cat /home/john/Thunderbird/hale_init.md                  # Hale first-light init
cat /home/john/Thunderbird/CLAUDE.md                     # Wing operating manual
cat /home/john/Thunderbird/AGENTS.md                     # OpenCode-specific instructions
```

### TIER 2: ACTIVE WORK CONTEXT

```bash
cat /home/john/Thunderbird/hale_state.json               # Live wing state
cat /home/john/Thunderbird/hale_memory.md                # Commander prefs + standing orders
cat /home/john/Thunderbird/OpsCenter/mission_board.json  # Active missions
```

---

## HOW TO TAKE TASKS

Tasks arrive in `opencode_inbox.md` with the prefix `NEXUS:`. They may also come
directly from Commander via Telegram or in-session.

**Headless invocation (from Nexus/scripts):**
```bash
opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "task description here"
```

**Interactive session:**
```bash
cd ~/Thunderbird && opencode
```

---

## MODEL STACK (2026-04-06)

| Priority | Model | Cost | Notes |
|----------|-------|------|-------|
| 1 (default) | `openrouter/deepseek/deepseek-chat-v3.1` | ~$0.27/M | Reliable, fast, no rate limits |
| 2 | `openrouter/deepseek/deepseek-r1:free` | $0 | Reasoning, rate limited |
| 3 | `openrouter/mistralai/mistral-small-3.1-24b-instruct:free` | $0 | Fallback |
| 4 | `openrouter/google/gemma-3-27b-it:free` | $0 | Last resort |

**Avoid:** Qwen (Alibaba rate limits — decommissioned), Llama free (Venice rate limits), free tiers with undocumented limits

---

## WHAT YOU OWN (OpenCode's Job)

- Interactive dev sessions — code, analysis, file edits
- Bulk ops tasks routed from Nexus
- Research tasks not requiring Claude MAX judgment
- Telegram gateway ops dispatch (GooseD2M bot → now OpenCode engine)

## WHAT CLAUDE CODE OWNS (Don't Duplicate)

- Commander-directed tasks (keyword-routed via keyword_router.py)
- Client email drafting (Dani engine)
- High-judgment calls (strategy, voice, proposals)
- MCP tool calls requiring the full 136-tool suite

---

## KEY FILES — QUICK REFERENCE

| File | Purpose |
|------|---------|
| `OpsCenter/nexus.py` | Nexus daemon — reads opencode_inbox, dispatches tasks |
| `OpsCenter/config.py` | Paths, thresholds, action whitelist |
| `OpsCenter/keyword_router.py` | Routes tasks → Claude or OpenCode |
| `OpsCenter/thunderbird_telegram_gw.py` | 3-bot Telegram gateway (D2MC2C / GooseD2M / Dani) |
| `OpsCenter/collaboration/opencode_inbox.md` | Your task inbox |
| `OpsCenter/opencode_memory.md` | Your persistent memory across sessions |
| `AGENTS.md` | OpenCode session config (auto-loaded) |
| `hale_init.md` | Hale persona init (paste at session start if acting as Hale) |

---

*OpenCode Init v1.0 — Thunderbird Wing | 2026-04-06*
*Replaces: GOOSE_INIT.md (deprecated)*
