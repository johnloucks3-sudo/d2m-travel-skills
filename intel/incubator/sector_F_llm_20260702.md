# Sector F — LLM Landscape · Incubator Research
*ELON (A12 — Technology Vanguard) · W7 · 2026-07-02*

## Bottom Line Up Front
The Wing's routing doctrine (Haiku default / Sonnet synthesis / Opus on-request) is still correct as of July 2026. Two live changes to fold in: (1) **Opus 4.8** dropped the manual thinking budget for an **effort parameter** + adaptive thinking — our dispatch code that sets `budget_tokens` will 400 on 4.8; (2) **Sonnet 5** shipped 2026-06-30 and should be evaluated as the new synthesis default. Haiku 4.5 remains the right file-read default — pricing unchanged, cheapest tier.

---

## 1. Current Anthropic Lineup (July 2026)

| Model | Input / Output ($/M tok) | Context | Notes |
|---|---|---|---|
| **Fable 5** (top tier) | $10 / $50 | 1M (128K out) | Reasoning model. Was suspended 2026-06-12 (US export-control directive), **redeployed 2026-07-01**. |
| **Opus 4.8** | $5 / $25 | 1M (128K out) | Most capable Opus tier; long-horizon agentic. |
| **Sonnet 4.6** | $3 / $15 | 1M | Near-Opus coding/doc comprehension; better computer-use + instruction-following. |
| **Sonnet 5** | (verify) | (verify) | **Released 2026-06-30** — newest Anthropic model. Not yet priced in our sources. |
| **Haiku 4.5** | $1 / $5 | 200K | Released 2025-10-15; pricing **stable through 2026**. Batch API −50%, cache −90%. |

## 2. Fable 5 vs Opus 4.8 vs Sonnet 4.6 — for our use case

- **Fable 5** — top reasoning tier at $10/$50. 5× the input cost of Opus, 2× the output. For a 1-person travel business this is **not justified** except on a rare architecture/high-stakes call, and even then Opus 4.8 covers it. Note the export-control volatility (suspended 12 days in June) — an operational reliability risk for anything we'd depend on. **Keep OFF the routing table.**
- **Opus 4.8** — $5/$25, 1M context, 128K output, long-horizon agentic. This is our "worker agent in a clear lane" tier (per SO agent-capability allocation: worker = Opus, orchestrator = Sonnet). Correct as-is.
- **Sonnet 4.6** — $3/$15, near-Opus coding + doc comprehension, improved computer-use. Our synthesis/client-voice workhorse. Still sound — **but Sonnet 5 (06-30) may supersede it**; evaluate.

## 3. New releases, last 30 days (June–July 2026)

Rapid cadence — 324+ tracked model releases across vendors. Relevant to us:
- **Claude Sonnet 5** — Anthropic, **2026-06-30**. Newest Anthropic model. **Action: benchmark vs Sonnet 4.6 for our synthesis/client-copy lane before switching the default.**
- **Claude Fable 5** preview (06-09) + **Mythos 5** GA — top tier; suspended 06-12, redeployed 07-01.
- **GPT-5.6** (OpenAI, June), **Gemini 3.2** (Google), **Gemini 3.1 Flash Lite Image** (06-23).
- Chinese frontier: Qwen 3.7, DeepSeek V4.1, GLM-6, Hunyuan, ERNIE, Doubao. *(Relevant to cc-fleet third-party worker routing — see Sector D.)*

## 4. Pricing shifts — is Haiku still the right file-read default?

**Yes.** Haiku 4.5 is $1/$5, 200K context, pricing stable all of 2026, cheapest tier. With Batch API (−50%) and prompt caching (−90% on cached input), it stays the cheapest path for file reads, classification, JSON extraction, status checks — exactly the SO-TOKEN-DISCIPLINE default list. No cheaper Anthropic tier exists. **No change.** (For truly zero-cost bulk work, cc-fleet routing to free third-party models is the lever — Sector D.)

## 5. Context / tool-use improvements relevant to Wing ops

**Opus 4.8 changes — these touch our dispatch code:**
- **Effort parameter replaces manual thinking budgets.** Opus 4.8 supports *adaptive thinking only*. Setting `thinking: {type:"enabled", budget_tokens:N}` returns **400**. Depth is controlled by the top-level `output_config` **effort** parameter. **⚠️ ACTION: audit `dispatch_claude.py` / headless spawn code for any hardcoded `budget_tokens` — it will break on Opus 4.8.**
- **Effort levels recalibrated** vs 4.7: `medium` = somewhat more thinking, `high` = somewhat less, `xhigh` = substantially more. Re-baseline cost/latency if we tuned against 4.7.
- **Better tool triggering** — less likely to skip a required tool call (a 4.7 complaint). Good for our tool-heavy agent lanes.
- **Better compaction + long-context** — long agentic traces stay on task after compaction. Directly benefits our long OODA sessions + hale_bus handoffs.
- **Lower cache floor** — min cacheable prompt 1,024 tokens (was 2,048). Shorter prompts now cache with no code change — small token-discipline win.
- **Unchanged constraints:** `temperature`/`top_p`/`top_k` non-default → 400 (same as 4.7). Guide behavior by prompting only.

*Confidence: HIGH on Opus 4.8 specifics (primary-source Anthropic docs). MEDIUM on Sonnet 5 details (release confirmed; pricing/context not yet in sources — verify at platform.claude.com).*

---

## Sources
- [Anthropic Platform Docs — What's new in Claude Opus 4.8](https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-8)
- [Anthropic — Introducing Claude Sonnet 5](https://www.anthropic.com/news/claude-sonnet-5)
- [Second Talent — Fable 5 vs Opus 4.8 vs Sonnet 4.6](https://www.secondtalent.com/resources/claude-fable-vs-opus-vs-sonnet/)
- [Anthropic — Introducing Claude Haiku 4.5](https://www.anthropic.com/news/claude-haiku-4-5)
- [llm-stats — AI Updates (July 2026)](https://llm-stats.com/llm-updates)
- [Presenc AI — June 2026 LLM Release Roundup](https://presenc.ai/research/june-2026-llm-release-roundup)
