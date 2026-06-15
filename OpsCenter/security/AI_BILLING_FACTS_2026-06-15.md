# AI / API Recurring Spend — Billing Forensics
**Generated 2026-06-15 · Mailbox: johnloucks3 (+ yodainva surfaced) · 180-day lookback · Card on file: Visa ****6174**

Method: amounts pulled from actual receipt bodies (RECEIPT = confirmed). Web pricing cited for Part B.

---

## 1. Every confirmed recurring / metered AI charge

| Provider | $ | Cadence | What it's for | Account | Source | Confidence |
|---|---|---|---|---|---|---|
| **Anthropic Claude MAX 20x** | **$200.00** | monthly | Claude Code + Pro UI (foundation) | johnloucks3 | Receipt 2026-05-23 | RECEIPT |
| **Google AI Pro (Google One 5TB)** | **$20.60** ($19.99+$0.61 tax) | monthly (5th) | Consumer Gemini app/NotebookLM — **no API** | johnloucks3 (Google Play) | Receipt 2026-06-05 | RECEIPT |
| Google Cloud / Gemini **API** | **~$5/mo** metered (spiked $100+$53 in Apr) | metered | Gemini API usage; $10 budget cap | johnloucks3 | Receipt 2026-06-01 | RECEIPT |
| **Perplexity** | **$10.00** | one-time top-up | Sonar **API credits** (NOT Pro sub) | johnloucks3 | Receipt 2026-06-14 | RECEIPT |
| **Poe** | **$4.99** sub + **$15.00** points | sub likely LAPSED; points one-time | Multi-model UI sub + points top-ups | yodainva | Receipt 2026-02-15 | RECEIPT; sub inactive |
| OpenAI | **$0** | — | No active paid plan | — | none in 180d | NEGATIVE |
| xAI (Grok) | metered/unbilled | — | ZEN counter-voice API key; **no sub** | johnloucks3 | none in 180d | NEGATIVE on sub |
| Pinecone / Groq / Together / HuggingFace | **$0** | — | Free tier | — | none in 180d | NEGATIVE |
| _Google Workspace Business Plus_ | _(biz email, PDF invoice)_ | monthly | _Out of AI scope_ | johnloucks3 | Receipt 2026-06-02 | PARTIAL |

### Poe detail (receipt-confirmed)
Sub $4.99/mo (Feb 15, yodainva). Points top-ups: **333,333 pts = $10.00** (Feb 13) + **166,667 pts = $5.00** (Feb 28) = **$15.00 one-time**, expire Feb 2027. No Poe charge since Feb 15 and **Poe is absent from RocketMoney's tracked-sub list** → sub effectively lapsed.

### RocketMoney corroboration (Jun 5 "check-in" digest — 14 subscriptions tracked)
Only AI sub it lists is **"Claude Monthly $168.54"** — exactly matches the May upgrade-cycle net charge (independent confirmation of the Anthropic number). Poe / Google AI Pro / Perplexity / OpenAI / xAI do **not** appear as tracked subs (Google AI Pro bills via Google Play). Non-AI subs in the list: Anytime Fitness $20.69, SiriusXM $39.54, Walmart+ $13.61, Paramount+ $5.00, SimpliSafe $32.99, FOX Nation $9.73, etc.

### Anthropic progression (one line only — Pro was replaced, not stacked)
Feb 21 **Claude Pro $20** → Mar/Apr/early-May **Max 5x $100** → **May 23 upgraded to Max 20x $200** (that cycle $168.54 net after a $31.46 proration credit). No separate Console/API charge in any receipt. There is **no longer a standalone $20 Pro charge** — it folded into Max.

---

## 2. Monthly run-rate above Claude MAX

- **Confirmed fixed recurring above MAX: ~$20.60/mo** (Google AI Pro only).
- **+ ~$5/mo** metered Gemini API (variable; capped at $10).
- **+ occasional** Perplexity top-ups ($10 as-needed, not recurring).
- **+ $4.99/mo** *if* the Poe sub is still live (no evidence of a charge since Feb 15 — likely lapsed).
- **All-in estimated run rate: ~$226–236/mo** (MAX $200 + AI Pro $20.60 + ~$5 Gemini API; Perplexity/Poe situational).

---

## 3. Redundant / overlapping

- **Poe ($4.99 + points) — REDUNDANT.** Its only value is multi-model UI access; Claude MAX 20x + the Google AI Pro Gemini app already cover frontier models. **Cancel if still recurring;** points already bought are sunk cost.
- **Google AI Pro $20.60 — conditional.** Adds **zero** programmatic capability (consumer UI only). Worth it only if NotebookLM / Deep Research / Gemini-in-Gmail are actually used by hand; otherwise cut.
- **Perplexity — correctly metered.** Commander bought $10 API credits, NOT the $20 Pro sub. Stay metered (Pro's bundled API credit is only ~$5/mo and reportedly removed in 2026).
- **OpenAI / ChatGPT Plus — not subscribed** (good; would duplicate MAX/Poe). The "Application of Taxes" email is a generic policy blast, **not** proof of billing.
- **xAI — no sub** (good; metered API is right for low-volume ZEN counter-voice).

**Net rationalization move: confirm + kill the Poe $4.99 sub; decide AI Pro on actual app usage. That's the only fat in the stack.**

---

## 4. Part B — current pricing (web, cited)
_Gemini API + Google AI Pro pricing already in `GOOGLE_AI_PRO_INTEGRATION_SPSA_2026-06-15.md` — not repeated._

**Perplexity Sonar API** — Sonar: $1.00/1M in, $1.00/1M out + $5–12 per 1k search req (context-tiered). Sonar Pro: $3.00/1M in, $15.00/1M out + $6–14 per 1k req. Deep Research ≈ $0.41+/query; simple query ≈ $0.006.
**Perplexity Pro $20/mo** — unlimited Pro Search + 20 Deep Research/day; historically $5/mo Sonar API credit (reportedly removed ~Mar 2026, status in flux). Consumer sub — the consumer-vs-API trap: for API use, metered beats the $20 sub.
**xAI Grok API** — Grok 4.3 (flagship): $1.25/1M in, $2.50/1M out, cached $0.20. Grok 4.1 Fast: $0.20/$0.50, cached $0.05. Grok 4.20 long-ctx: $2.00/$6.00. No SuperGrok sub needed for ZEN.
**Groq free tier** — 30 RPM / 6K–30K TPM / 1K–14.4K req/day, no card; Whisper 2k audio/day. Developer tier: 25% cheaper + up to 10× limits.
**Poe** — standard $19.99/mo = 1M points, multi-provider UI (Commander on $4.99 tier). Redundant given MAX 20x + AI Pro.

**Sources:** [cloudzero](https://www.cloudzero.com/blog/perplexity-pricing/) · [screenapp](https://screenapp.io/blog/perplexity-pricing) · [goosed](https://goosed.ie/news/perplexity-pro-quietly-removes-free-api-credits/) · [eesel-xai](https://www.eesel.ai/blog/xai-pricing) · [mem0-grok](https://mem0.ai/blog/xai-grok-api-pricing) · [eesel-groq](https://www.eesel.ai/blog/groq-pricing) · [tokenmix-groq](https://tokenmix.ai/blog/groq-free-tier-limits-2026) · [poe plans](https://poe.com/subscription_plans) · [costbench-poe](https://costbench.com/software/ai-chatbots/poe/)

---
*Honesty notes: Poe renewal status and exact points-purchase dollar amounts are NOT receipt-confirmed (points confirmations omit $). Google Workspace $ not extracted (PDF invoice, out of AI scope). Everything else in the table is receipt-confirmed or a confirmed negative.*
