# THUNDERBIRD — CANONICAL AI ROUTING POLICY
**Effective:** 2026-06-15 · **Owner:** Hale (COS) · **Authority:** Commander directive (optimum-mix consolidation)
**Basis:** `OpsCenter/security/AI_STACK_OPTIMUM_MIX_2026-06-15.md` + receipt-verified billing. **This file governs which AI provider serves which job. New code MUST follow it; legacy code migrates per MISSION-267.**

---

## THE MIX — one provider per job (5 providers, not 9)

| Role | Use | Model | Cost | Notes |
|---|---|---|---|---|
| **DEFAULT / primary** — synthesis, client copy, reasoning, orchestration, persona voice | **Claude MAX (OAuth)** | Opus / Sonnet / Haiku | **$0 marginal** | The foundation. Orchestrator pops `ANTHROPIC_API_KEY` to stay on OAuth. Never route client-facing work off MAX without reason. |
| **Counter-voice (ZEN)** — "challenge / devil's advocate / what could go wrong" | **xAI Grok (direct)** | grok-4.x | metered, pennies | Genuine diversity. **NOT via OpenRouter.** |
| **Web research + citations** — OSINT, intel, real-time, fare/destination context | **Perplexity Sonar** | sonar / sonar-pro | metered credits | The web-research lane. Absorbs Serper. Fund with credits, not Pro sub. |
| **Cheap/bulk** — classification, extraction, log scans, "is X present" | **Groq (Llama)** primary, **Gemini Flash-Lite** fallback | llama-3.x / 2.5-flash-lite | **$0 free tier** / pennies | Keep MAX budget for real work. |
| **Image generation** | **HuggingFace FLUX** | FLUX.1-schnell | **$0** | Already wired. |
| **Embeddings / vector memory** | **local Qdrant** + local embeddings | — | **$0** | On-box, PII-safe. NOT Pinecone. |

**Privacy gate:** free-tier Gemini trains on inputs → **non-PII only**. Any client-bearing data → Claude MAX or **paid** Gemini. PII never goes to a free metered tier.

### CONTINGENCY / STANDBY (keep wired, do NOT cut)
- **Poe** — **RETAINED as a contingency** (Commander directive 2026-06-15). Not in the active mix, but kept as a fallback multi-model path if Claude MAX / primary providers are unavailable. Sub is lapsed but ~500K points (expire Feb 2027) make it a **$0 emergency reserve**. Keep `POE_API_KEY` + the adapter; leave `poe-auth-check` running.

---

## DEPRECATED — do not use in new code (migration: MISSION-267)
| Provider | Why retired | Replacement |
|---|---|---|
| **OpenRouter** | Aggregator duplicating direct providers; Commander mandate "no OpenRouter" | Grok-direct / Gemini-direct |
| **Pinecone** | Qdrant is the live store | local Qdrant |
| **OpenAI** | No active paid plan; unused | Claude MAX / Gemini |
| **Together / DeepSeek-direct** | Redundant fallbacks | Groq / Gemini-Flash |
| **2 of 3 Google keys** | `GEMINI_API_KEY` is canonical | retire `GOOGLE_GENERATIVE_AI_API_KEY` (0 uses); migrate `GOOGLE_AI_API_KEY` (10 uses) → `GEMINI_API_KEY` |

⚠️ **These keys are still load-bearing in active systemd units** — they are retired by **refactor (MISSION-267), not by deleting the key**. Deleting a live key = outage. Keys stay until their callers are migrated.

---

## COST DISCIPLINE (MISSION-268)
1. **Default to MAX** ($0). Reach for metered only for the role it owns above.
2. **Hard caps** set in each metered dashboard (Gemini AI Studio $10 — confirm; Perplexity; xAI). The April 2026 Gemini **$153 one-day spike** must be impossible to repeat unseen.
3. **Per-call cost logging** re-armed in `multi_model_orchestrator.py` (schema: `state/api_cost_log.jsonl`; logger exists in `core/watchtower/`, `core/ops/thunderbird_nova.py`). It died March 2026 — that's why the spike was invisible.
4. **Monthly review** (1st): reconcile the 5 providers vs receipts; RocketMoney backstop.

---

## STANDING TOTALS (receipt + RocketMoney verified 2026-06-15)
- **Claude MAX 20x:** $168.54–200/mo (foundation) · **Google One/AI Pro:** $20.60 (use-or-cut) · **Google Workspace:** $26.12 (infra, keep) · metered Gemini/Perplexity/Grok: ~$5–15/mo.
- **AI is NOT the cost driver** — non-AI subscriptions + bills dwarf it. Keep the mix lean for *simplicity + security* (fewer keys to leak/rotate), not for dollars.
