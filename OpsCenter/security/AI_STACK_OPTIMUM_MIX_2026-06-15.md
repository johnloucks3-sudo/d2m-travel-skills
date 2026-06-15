# AI / API STACK — OPTIMUM MIX (STAFF PAPER)
**Date:** 2026-06-15 · **Prepared by:** Hale (COS) · **For:** Commander
**Companions:** `AI_BILLING_FACTS_2026-06-15.json/.md` (receipt-verified costs) · `GOOGLE_AI_PRO_INTEGRATION_SPSA_2026-06-15.md` (Gemini deep-dive)
**Source of truth:** Anthropic/Google/Perplexity/Poe receipts (johnloucks3) + RocketMoney digest corroboration + code inventory. Stale `api_cost_log.jsonl` (died March) was NOT relied on.

---

## BLUF

Your credit-card "AI bills" are **not** a hodge-podge of metered API charges — the stack runs almost entirely on **Claude MAX at $0 marginal** (the orchestrator literally drops the Anthropic API key to avoid metered billing). The bill went up because **you upgraded Claude MAX from 5x ($100) to 20x ($200) on May 23** — that single line is ~85% of the spend, and it's the *foundation*, not waste.

**Everything over-and-above MAX is small: ~$20.60/mo fixed (Google AI Pro) + ~$5/mo metered Gemini + occasional Perplexity top-ups. All-in ≈ $226–236/mo.**

The real problem isn't cost — it's **sprawl**: **9 LLM providers wired in, most dormant or redundant.** The fix is consolidation to a clean **5-provider role-map**, killing 4 providers that add nothing, and a lightweight monthly cost-review so this never drifts again.

---

## 1. WHAT WE HAVE (full inventory)

**Companies with keys in `.env`:** Anthropic, Google (×3 keys), OpenAI, OpenRouter, xAI, Groq, DeepSeek (via OpenRouter), Together, Poe, Perplexity, HuggingFace + utility APIs (Pinecone, Serper, Pexels, Unsplash, Twilio, Mapbox).

| Provider | Models used | Wired in | Status | Cost (receipt-verified) |
|---|---|---|---|---|
| **Anthropic Claude MAX 20x** | Opus/Sonnet/Haiku via OAuth | orchestrator default, everything | **ACTIVE — foundation** | **$200/mo** |
| **Google Gemini API** | 2.5 Flash/Flash-Lite/Pro | `gemini_client.py` (idle), 68 files | wired, barely used | **~$5/mo metered** (spiked $153 once in Apr) |
| **Google AI Pro (One 5TB)** | Gemini app, NotebookLM, Deep Research | consumer UI only — **no API** | sub active | **$20.60/mo** |
| **Perplexity Sonar** | sonar / sonar-pro | intel/monitors, 15 files | **NEW, useful** | **$10 one-time credits** (metered) |
| **xAI Grok** | grok-4.x | ZEN counter-voice | active, metered | pennies/mo |
| **Groq** | Llama-3.x | cheap/fast classification, 43 files | active | **$0 free tier** |
| **HuggingFace** | FLUX.1-schnell | image gen | active | **$0 free tier** |
| **OpenRouter** | DeepSeek/Grok/etc (aggregator) | 66 files | **redundant** | ~$0 (MAX is default) |
| **Poe** | multi-model UI + points | adapters, telegram | **LAPSED / dead** | $4.99 sub (gone) + $15 sunk points |
| **OpenAI** | — | 38 files (mostly dormant) | **no paid plan** | $0 |
| **DeepSeek / Together** | via OpenRouter / direct | fallback paths | redundant | ~$0 |
| **Pinecone** | vector DB | 4 files | **redundant** (Qdrant is live) | free tier |

**Vector store:** local **Qdrant** ($0) is the active memory; **Pinecone** is dead parallel wiring.
**Web search:** **Serper** + Google Custom Search (7 files) overlap the new **Perplexity** research slot.

---

## 2. THE COST STORY (receipt-verified)

| Bucket | Item | $/mo | Verdict |
|---|---|---|---|
| **Foundation** | Claude MAX 20x | $200.00 | KEEP — powers the whole stack at $0 marginal |
| **Fixed sub, over MAX** | Google AI Pro (One 5TB) | $20.60 | CONDITIONAL — buys zero API; keep only if you use NotebookLM/Deep Research/Gemini-in-Gmail by hand |
| **Metered, tiny** | Gemini API | ~$5 | KEEP — watch the cap (it spiked $153 in April once) |
| **Metered, situational** | Perplexity Sonar credits | ~$10 top-ups | KEEP — real-time web + citations |
| **Metered, pennies** | xAI Grok (ZEN) | <$1 | KEEP — genuine counter-voice |
| **DEAD** | Poe sub + points | $0 (lapsed) | CONFIRM-CANCELLED — redundant w/ MAX 20x |
| **$0** | Groq, HF, OpenAI, Pinecone, Together, DeepSeek | $0 | free tier / unused |

**Above-MAX run-rate ≈ $25/mo.** The "bills" are the MAX upgrade, not sprawl. *Caveat: the April $153 Gemini spike shows metered APIs CAN bite — instrumentation matters (see §5).*

### 2a. RocketMoney "Recurring" — LIVE GROUND TRUTH (Commander pull, 2026-06-15)
The full recurring view **confirms the receipt audit and corrects two things.** Only **TWO** AI-relevant active subscriptions exist on the cards:

| RocketMoney line | $/mo | Card | Note |
|---|---|---|---|
| **Claude** | **$168.54** | Citibank ••3550 | MAX (this cycle prorated; full rate $200) — matches receipt |
| **Google One** | **$20.60** | Chase ••6174 | = Google AI Pro / 5TB (consumer, no API) |
| **GOOGLE \*Workspace_john** | **$26.12** | Chase ••6174 | **NEW — business Google Workspace** (runs d2mconcierge email/domain). Infrastructure, KEEP. The Gemini SPSA flagged this as un-extracted; now confirmed. |

**Confirmed NEGATIVES (no sub on any card):** Perplexity, Poe, OpenAI, xAI, Pinecone, Together — exactly as the audit said (metered / free / dead). An **INACTIVE** second "Claude — Citibank ••1964" appears in RocketMoney's inactive list = the **old $20 Claude Pro, now gone** — confirms Pro folded into MAX 20x.

**The honest headline:** the AI stack is **lean and cheap** — ~$215/mo (Claude $168–200 + Google One $20.60), plus $26.12 Workspace infra and metered pennies. The credit-card "bills" the Commander sees are **dominated by non-AI** (mortgage $2,135, USAA $288, T-Mobile $171, streaming/fitness/SiriusXM bundle, $119K/yr in card payments). **AI is not the cost problem.** The only AI lever is the $20.60 Google One use-or-cut; everything else worth cutting is already $0 — pure simplification + security (fewer keys).

---

## 3. THE OPTIMUM MIX — one provider per job

Instead of 9 overlapping providers, **5 with clear lanes:**

| Role | Provider (model) | Why | Cost |
|---|---|---|---|
| **Primary — synthesis, client copy, reasoning, orchestration** | **Claude MAX** (Opus/Sonnet/Haiku via OAuth) | Already paid; $0 marginal; best for client-facing voice + judgment | $0 marginal |
| **Counter-voice (ZEN)** | **xAI Grok direct** | Genuine model diversity for "challenge/devil's advocate" — NOT an aggregator reskin | metered, <$1 |
| **Web research + citations** | **Perplexity Sonar** | Real-time, sourced — Dembe OSINT / intel / fare-context. Absorbs Serper's job | metered |
| **Cheap/bulk — classification, extraction, log scans** | **Groq (Llama)** free tier, **Gemini Flash-Lite** fallback | Free, fast; keeps MAX budget for real work | $0 / pennies |
| **Image generation** | **HuggingFace FLUX** | Already wired, free | $0 |
| **Embeddings / vector memory** | **local Qdrant** + local embeddings | On-box, $0, PII-safe | $0 |

**Privacy gate (from the Gemini SPSA):** free-tier Gemini trains on inputs → **non-PII work only**; anything client-bearing stays on Claude MAX or paid Gemini.

---

## 4. KEEP / CUT / CONSOLIDATE

| Action | Provider | Rationale | Saves |
|---|---|---|---|
| ✂️ **CUT** | **OpenRouter** | Aggregator duplicating Grok/Gemini/DeepSeek-direct; you mandated "no OpenRouter." Remove the key + the 66-file dependency over time | complexity + 1 key |
| ✂️ **CUT / confirm-cancelled** | **Poe** | Sub lapsed; redundant with MAX 20x + Gemini app. Stop the adapters | dead spend |
| ✂️ **CUT** | **Pinecone** | Qdrant is the live store; Pinecone is dead parallel wiring | 1 key, free-tier clutter |
| ✂️ **CUT** | **OpenAI, Together, DeepSeek-direct** | No paid plan / redundant fallbacks | 3 keys |
| 🔁 **CONSOLIDATE** | **3 Google keys → 1** | `GEMINI_API_KEY` (28×) is primary; `GOOGLE_AI_API_KEY` (10×) + `GOOGLE_GENERATIVE_AI_API_KEY` (0×) are dupes | clarity |
| 🤔 **REVIEW** | **Serper / Google Custom Search** | Perplexity Sonar covers research; keep Serper only if a workflow needs cheap structured SERP JSON | maybe 1 sub |
| 🤔 **DECIDE** | **Google AI Pro $20.60** | Keep ONLY if you personally use NotebookLM/Deep Research/Gemini-in-Gmail. It gives the stack nothing | maybe $20.60/mo |
| ✅ **KEEP** | MAX, Grok, Perplexity, Groq, HF, Qdrant | the 5-provider mix above | — |

**Net:** from 9 LLM providers → 5; from ~14 keys → ~7. Cost barely moves (already ~$25 over MAX) — the win is **simplicity, security (fewer keys to rotate/leak — ties to the secrets audit), and no surprise spikes.**

---

## 5. FIX THE BLIND SPOT — cost instrumentation

You're getting bills you can't see because **`state/api_cost_log.jsonl` stopped logging in March** and the "cost report" is just a Claude-MAX usage gauge. Recommendations:
1. **Re-arm per-call cost logging** in `multi_model_orchestrator.py` (the schema exists) so every metered call (Gemini, Perplexity, Grok) appends `cost_usd` — catches the next April-style $153 spike at $5.
2. **Hard caps**: set spend limits in Google AI Studio + Perplexity dashboards (you already cap Gemini at $10 — confirm it).
3. **Monthly 5-minute subscription review** (1st of month): reconcile the 5 providers against receipts. Since spend is mostly flat subs, this beats heavy token metering.
4. **RocketMoney as backstop** — it already tracks the recurring charges; one glance/month confirms nothing crept back.

---

## 6. RECOMMENDATION

1. **Keep Claude MAX 20x** — it's the foundation and the reason everything else is cheap. Not a cut target.
2. **Adopt the 5-provider role-map** (§3). Kill OpenRouter, Poe, Pinecone, OpenAI, Together, DeepSeek-direct; consolidate Google keys.
3. **Decide Google AI Pro $20.60** — use-it-or-cut-it based on your hand-use of NotebookLM/Deep Research.
4. **Perplexity = the web-research lane** — fund it with metered credits, not a Pro sub (the $20 Pro's bundled API credit was removed ~Mar 2026; metered is cheaper for our use).
5. **Re-instrument cost logging + set hard caps** so the April spike can't recur unseen.
6. **Security tie-in:** every cut key is one fewer to rotate/leak — fold the removed keys into the secrets-manager migration (MISSION-260).

*Honesty notes: above-MAX spend is small and partly metered (varies with use); Poe-lapsed is inferred from two converging negatives (no charge + absent from RocketMoney), not a cancellation receipt — confirm in your Poe account. Google Workspace $ not in scope here.*

*— V. Hale, VCS*
