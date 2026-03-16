# COMMANDER REVIEW #32 (REV B)
## Telegram C2 Redesign — Opus-via-Max Architecture
### Prepared by: COS (Col Victoria Hale) with A12 (ELON) cost analysis
### Date: 2026-03-14
### Classification: Internal — Commander's Eyes
### Revision: B — Incorporates Commander's directive: "Use Opus via Max plan for all personas. Personas are agents of COS, not separate API calls."

---

## EXECUTIVE SUMMARY

The current Telegram bot burns the $10/mo GCP budget by routing ALL persona calls through Gemini 2.5 Flash. The Commander's Max plan ($200/mo) includes unlimited Claude Opus 4.6 via CLI at $0 per token. This changes everything.

**New architecture:** Telegram → Groq classifier (free) → Claude Opus via CLI ($0) handles ALL reasoning, ALL personas, ALL client-facing work. Personas are not separate API calls — they are prompts that COS (Opus) embodies. Gemini 3.1 Flash-Lite handles only menial grunt work (sheet reads, file indexing).

**Bottom line:** $0 for all reasoning. ~$1/month for grunt work. Quality upgrade from Gemini Flash to Opus for everything.

**Commander's decisions (incorporated):**
1. Anthropic API key available — Commander will fund if needed
2. Gemini 3.1 Flash-Lite — CONFIRMED AVAILABLE on current API key
3. Budget ceiling — $10/mo combined (will barely touch it)
4. Timeline — Start now, Opus replaces COS immediately
5. Marketing persona — Deferred

---

## 1. C2 ARCHITECTURE — OPUS-VIA-MAX

### Military C2 Principles Applied

- **Commander's intent flows down** — natural language directive via Telegram
- **Situational awareness flows up** — status, intel, alerts back to Commander
- **Execution is autonomous** — COS (Opus) acts on intent, delegates internally
- **Coordination happens laterally** — COS handles all inter-persona coordination
- **Data-centric, not message-centric** — decisions flow from shared understanding (Trinity + Sheets + MCP tools)

### Two-Layer Execution Model

```
TELEGRAM MESSAGE (Commander's phone)
    │
    ▼
┌──────────────────────────────────┐
│  LAYER 0: CLASSIFIER              │
│  Groq Llama 4 Scout (FREE)        │
│  Intent → TASK/ORDER/PRIORITY/    │
│           APPROVE/SITREP          │
│  Extract: target, subject, urgency │
│  ~200 tokens, ~200ms              │
│  Cost: $0.00                      │
└──────────────┬────────────────────┘
               ▼
┌──────────────────────────────────────────────┐
│  LAYER 1: COS — CLAUDE OPUS VIA CLI ($0)      │
│                                               │
│  Single brain handles EVERYTHING:             │
│                                               │
│  ┌─ COS thinking ──── interpret, plan, decide │
│  ├─ Dani's voice ──── client emails, concierge│
│  ├─ Luna's voice ──── previews, itineraries   │
│  ├─ Dembe's mind ──── research, intel         │
│  ├─ Castillo's lens ─ strategy, revenue       │
│  ├─ Naia's eye ────── brand, visual direction │
│  ├─ Harlan's math ─── commissions, budgets    │
│  ├─ ELON's logic ──── tech, architecture      │
│  ├─ Washington ────── morale, ethics          │
│  └─ 143 MCP tools ─── real data, real actions │
│                                               │
│  Personas are PROMPTS, not separate models.   │
│  COS embodies each persona when needed.       │
│  Opus quality for ALL output.                 │
│  Cost: $0.00 (Max plan)                       │
└──────────────┬────────────────────────────────┘
               │
               │ (only for menial grunt work)
               ▼
┌──────────────────────────────────────────────┐
│  LAYER 2: GRUNT WORKERS (optional, rare)      │
│                                               │
│  Gemini 3.1 Flash-Lite ($0.25/$1.50)          │
│  - Bulk sheet reads (50+ rows)                │
│  - File indexing / directory scans            │
│  - Backup verification checksums             │
│  - Any high-volume, zero-creativity task      │
│                                               │
│  Only used when COS decides the task is       │
│  pure mechanical work not worth Opus cycles.  │
│  Cost: ~$0.03/day                             │
└───────────────────────────────────────────────┘
```

---

## 2. WHY THIS WORKS

### The Max Plan Insight

| What | Model | How Called | Cost |
|------|-------|-----------|------|
| Commander on Chromebook | Claude Opus 4.6 | Claude CLI direct | $0 (Max plan) |
| Commander on Yoga SSH | Claude Opus 4.6 | Claude CLI direct | $0 (Max plan) |
| **Telegram C2 (NEW)** | Claude Opus 4.6 | Claude CLI subprocess on Yoga | **$0 (Max plan)** |
| Grunt work | Gemini 3.1 Flash-Lite | API call | ~$0.001/call |

The Max plan doesn't care HOW Claude CLI is invoked — interactive terminal, subprocess, or piped from a Telegram bot. It's all the same unlimited usage.

### Personas as Agents, Not APIs

Old model: Each persona = separate API call to a separate model = separate cost.

New model: Each persona = a system prompt that COS (Opus) loads when embodying that persona. One brain, many hats.

| Persona | Old Approach | New Approach |
|---------|-------------|-------------|
| A3 (Dani) | Groq/Gemini API call with Dani prompt | COS loads Dani prompt, writes as Dani in Opus quality |
| A6 (Luna) | Groq/Gemini API call with Luna prompt | COS loads Luna prompt, writes as Luna in Opus quality |
| A2 (Dembe) | Groq/Gemini API call with Dembe prompt | COS thinks as Dembe, researches as Dembe, Opus depth |
| All others | Same pattern | Same pattern |

**Quality upgrade:** Every persona goes from Gemini 2.5 Flash (B+ tier) to Claude Opus 4.6 (S tier). The McLeod preview Luna wrote? Imagine that at Opus quality instead of Gemini Flash. Client emails from Dani? Opus warmth and nuance.

---

## 3. PERSONA-TO-MODEL MAPPING (REVISED)

| Persona | Role | Model | Cost | Notes |
|---------|------|-------|------|-------|
| **Classifier** | Intent parsing | Groq Llama 4 Scout | FREE | 200 tokens, classify only |
| **COS (Hale)** | Orchestrator + ALL persona work | Claude Opus 4.6 via CLI | **$0** | The single brain |
| **A1 (Radar)** | Admin / docs (when built) | Gemini 3.1 Flash-Lite | $0.25/$1.50 | Only persona on a cheap model — pure clerk work |
| **A2 (Dembe)** | Research & intel | COS as Dembe (Opus) | **$0** | COS loads Dembe prompt |
| **A3 (Dani)** | Concierge (client-facing) | COS as Dani (Opus) | **$0** | COS loads Dani prompt — Opus luxury voice |
| **A5 (Castillo)** | Strategy & revenue | COS as Castillo (Opus) | **$0** | COS loads Castillo prompt |
| **A6 (Luna)** | Itinerary & narrative | COS as Luna (Opus) | **$0** | COS loads Luna prompt — Opus narrative quality |
| **A9 (Harlan)** | Finance / comptroller | COS as Harlan (Opus) OR Flash-Lite for pure number pulls | **$0** or pennies | Opus for analysis, Flash-Lite for bulk reads |
| **CH (Washington)** | Chaplain / morale | COS as Washington (Opus) | **$0** | Rare, but Opus warmth when called |
| **A12 (ELON)** | Tech / innovation | COS as ELON (Opus) | **$0** | COS loads ELON prompt |
| **EXEC (Naia)** | Brand & visual | COS as Naia (Opus) | **$0** | COS loads Naia prompt |

---

## 4. COST ANALYSIS (REVISED)

### Monthly Cost Projection

| Item | Cost |
|------|------|
| Max plan (Claude Opus CLI unlimited) | $0 incremental (already paying $200/mo) |
| Groq classifier (free tier) | $0 |
| Gemini 3.1 Flash-Lite (Radar grunt work) | ~$0.50-1.00/mo |
| **TOTAL INCREMENTAL** | **~$1/month** |

### Comparison

| Architecture | Monthly Cost | Quality |
|-------------|-------------|---------|
| Current (Gemini 2.5 Flash everything) | $10+ (blown) | B+ |
| Rev A (tiered multi-model) | $3-8 | Mixed (B+ to A+) |
| **Rev B (Opus via Max)** | **~$1** | **S tier — everything** |

**90% cost reduction. 100% quality upgrade.**

---

## 5. TECHNICAL IMPLEMENTATION

### How Telegram Triggers Claude CLI

**Option A: `claude --print` subprocess (Recommended for Phase 1)**

```python
import subprocess
import json

def call_cos_via_cli(message: str, persona: str = "COS") -> str:
    """Call Claude Opus via CLI subprocess. Cost: $0 (Max plan)."""

    prompt = f"""You are COS (Col Victoria Hale). A Telegram C2 message has arrived.

Classified intent: {classified_intent}
Target persona: {persona}
Commander's message: {message}

If the target persona is not COS, embody that persona using their
system prompt from ~/Thunderbird/Personas/. Write your response
in their voice, using their expertise.

You have access to all MCP tools. Use them to get real data.
Respond concisely — this goes back to Telegram."""

    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=os.path.expanduser("~/Thunderbird")
    )
    return result.stdout.strip()
```

**Option B: Claude Agent SDK (Under evaluation — see Appendix A)**

More structured agent framework with formal tool definitions, handoffs, and guardrails. Research pending on whether Max plan covers SDK usage or if it's API-billed separately.

**Option C: Claude API with Anthropic key (Fallback only)**

Direct API calls to claude-sonnet or claude-haiku. Only used if CLI subprocess has issues (timeout, concurrency limits). Costs real money per token.

### Concurrency Consideration

Claude CLI may have limits on concurrent sessions under Max plan. If the Commander sends rapid-fire messages, we may need:
- A message queue (simple Python asyncio queue)
- Sequential processing with "COS is working on your previous request" feedback
- Or: Claude Agent SDK if it handles concurrency natively

### Files to Change

| File | Change | Priority |
|------|--------|----------|
| `thunderbird_telegram_tools.py` | Replace entire Groq tool-calling loop with `call_cos_via_cli()` | P1 |
| `thunderbird_telegram.py` | Simplify — classifier → CLI subprocess → Telegram response | P1 |
| `thunderbird_personas.py` | Keep persona prompts but remove LLM_PROVIDER_ORDER and all API call logic | P2 |
| `thunderbird_model_router.py` | Simplified — only routes Radar to Flash-Lite, everything else → CLI | P2 |
| `thunderbird_crewai.py` | Remove Gemini hardcode | P3 |

### New Flow in `thunderbird_telegram.py`

```python
async def handle_commander_message(update, context):
    text = update.message.text

    # Layer 0: Classify (Groq, free, fast)
    intent = classify_intent_groq(text)  # existing function, unchanged

    # Layer 1: COS handles everything (Opus via CLI, $0)
    await update.message.reply_text("🔄 COS processing...")

    response = call_cos_via_cli(
        message=text,
        persona=intent.target_persona,
        intent_type=intent.type,  # TASK/ORDER/PRIORITY/APPROVE/SITREP
    )

    # Deliver response
    await update.message.reply_text(response, parse_mode="Markdown")

    # Triple-write logging (async, non-blocking)
    asyncio.create_task(triple_write_log(intent, text, response))
```

---

## 6. MIGRATION PLAN (REVISED)

| Phase | What | When | Risk |
|-------|------|------|------|
| **Phase 1** | Replace `call_cos_with_tools()` in telegram_tools.py with `call_cos_via_cli()` | Now | Low — one function swap |
| **Phase 2** | Simplify telegram.py to use new flow | Same session | Low — cleaner code |
| **Phase 3** | Test all 5 command types via Telegram | Same session | Catch issues |
| **Phase 4** | Strip Gemini from persona system, keep only for Radar | Next session | Medium |
| **Phase 5** | Evaluate Claude Agent SDK as Phase 2 upgrade | Research first | See Appendix A |

---

## 7. APPENDIX A: CLAUDE AGENT SDK EVALUATION

*(Research in progress — will be added when complete)*

Key questions:
- Does Max plan cover SDK usage or is it API-billed?
- Multi-agent orchestration — can COS formally delegate to sub-agents?
- Tool handoff patterns — structured vs freeform
- Guardrails and safety — built-in vs custom
- Concurrency support — can it handle multiple Telegram messages?

---

## 8. RESOLVED QUESTIONS

| # | Question | Commander's Answer |
|---|----------|-------------------|
| 1 | Anthropic API key | Has one, will fund if needed. But prefer $0 CLI path. |
| 2 | Gemini 3.1 Flash-Lite | **CONFIRMED AVAILABLE** on current API key |
| 3 | Budget ceiling | $10/mo combined. Will barely touch it (~$1/mo projected). |
| 4 | Timeline | Start now. Swap COS to Opus immediately. |
| 5 | Marketing persona | Deferred. |

---

*Rev B reflects Commander's key insight: the Max plan makes Opus free for all Telegram operations. Personas are agents of COS, not separate API consumers. This eliminates 90% of projected cost while upgrading every persona to S-tier quality.*

*Spec prepared by COS (Hale). Ready for implementation.*

> **Commander:**
> *(Space for Yoda's comments, direction, and decisions)*
