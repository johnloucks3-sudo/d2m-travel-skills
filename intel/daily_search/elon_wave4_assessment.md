# ELON — WAVE 4 INTEGRATION ASSESSMENT
## Thunderbird Daily Intelligence Engine — 2026-06-21
**ELON (A12), Sonnet 4.6 | Wave 4: 31/31 complete, 0 errors**

---

## STATUS

Wave 4 confirmed complete at 13:46 MT. Output: `wave4_2026-06-21_1346.json` (178KB, 31 categories).
All 4 waves analyzed. Total citations processed across 124 search runs.

Already integrated today (skip): Groq, Cloudflare Workers AI, GitHub Models, Presidio, PyMuPDF, Promptfoo, cc-fleet, Hyperbrowser, Firecrawl, Renovate.
Wave 3 already assigned (skip): Yardi/Virtuoso connector (Dembe), Claude Managed Agents (Hale), Fable 5 (ELON), TurboCall (Dani), Promptfoo CI (Sterling), pgvectorscale (Whetstone).

---

## WAVE 4 vs WAVES 1-3 — DELTA ANALYSIS

### What's NEW in Wave 4 (signal that didn't appear or was weak before)

1. **Cerebras** emerged as the speed leader in free inference tier — explicitly called out W4 as "world's fastest" alongside Groq. W1-W3 had Groq as the clear free-tier winner; W4 adds Cerebras as a co-equal or faster alternative. Architecture implication: our model router should route burst/latency-sensitive tasks to Cerebras, not just Groq.

2. **Temporal** received stronger W4 citation density for durable agent scheduling than prior waves. W1 mentioned it; W4 frames it as THE robust replacement for systemd timers for long-running retry-heavy jobs. Compounding signal across all 4 waves.

3. **Docling** (IBM, open source) emerged more clearly in W4 PDF extraction results vs W1-W3 which leaned LlamaParse. Docling is fully self-hosted, no API key, Apache 2.0. Direct upgrade path from PyMuPDF (already integrated).

4. **CloakBrowser** appeared W4 for Akamai bypass — new name, stealth Chromium fork. W1-W3 had browser-use and Playwright as the answer to the Regent/Akamai wall. CloakBrowser is more targeted.

5. **Community discourse** (category #29) W4 confirmed the dominant signal: AI coding assistants with tight IDE/repo integration are being treated as genuinely useful. Generic "agent" platforms viewed with skepticism. This validates our go-narrow-go-deep approach over chasing every agent framework.

### What's COMPOUNDING (stronger in W4 than W1-W3)

- **pgvectorscale over Qdrant** — W4 adds more citations showing Postgres+pgvectorscale as the 2026 default for new projects. Our existing Qdrant is not wrong but the migration pressure is real and growing. Whetstone already has this (W3 assignment). Flag: don't wait on the evaluation.
- **Inngest / Trigger.dev** — W4 reinforces these as the event-driven scheduling layer alongside Temporal. All 4 waves consistent.
- **Free LLM tier** — W4 explicitly ranks: Gemini Developer API > Groq > Cerebras > OpenRouter free models > Cloudflare Workers AI > Mistral > Cohere > HuggingFace > DeepInfra > GitHub Models. Our router covers 3 of these. Missing: Cerebras, DeepInfra.
- **Vapi as voice leader** — W4 names Vapi, Retell AI, ElevenLabs as the practical 1-person agency voice stack. Consistent with W3 TurboCall assignment. Vapi has a free tier.

### What CONTRADICTS (W4 vs prior waves)

- W4 category #16 (Anthropic API & Claude Agent SDK) returned weak/off-target results — Perplexity couldn't verify specific Q1-Q2 2026 API changes from retrieved sources. This is the structural weak spot noted in the briefing. Confirmed: direct Anthropic docs fetch is required here, not Perplexity. This is NOT an architecture change — it validates the known category #16 limitation.
- W4 on cruise line intel (#13): same story — Perplexity confirmed browser-use/Playwright/Hyperbrowser can help with Akamai but "none should be treated as reliably Akamai-proof on their own." This is consistent with W1-W3. The Regent portal situation remains unsolved by any tool — it's a human-in-loop or session-steal problem.
- No contradictions on model routing or architecture decisions made today.

---

## RANKED INTEGRATION LIST

### GO NOW — Free, $0, installable today

**1. Cerebras — Free inference API (speed tier)**
Why: W4 confirms 20x faster than Anthropic/OpenAI, free tier, all models. Our router has Groq; Cerebras is faster for burst/latency-sensitive tasks. Zero cost.
Install: `pip install cerebras-cloud-sdk` | API key: cloud.cerebras.ai (free)
Owner: ELON fleet routes this, Whetstone tests latency vs Groq on our standard payload.

**2. Docling — Self-hosted PDF extraction (PyMuPDF upgrade)**
Why: W4+W3 consistent signal. IBM open-source, Apache 2.0, fully self-hosted, no API. Handles multi-column cruise brochures, scanned docs, booking confirmations. Direct upgrade from PyMuPDF which we already integrated. No new dependency model — same lane.
Install: `pip install docling`
Owner: Sterling evaluates against existing PyMuPDF pipeline within 48h.

**3. ccusage — Claude MAX usage attribution (free CLI)**
Why: W4 category #19 named it explicitly. Solves MISSION-COST-01 (real MAX usage dashboard). Free, open source, reads Claude Code usage logs. Plugs the gap Cloudflare creates on our CDP approach.
Install: `npm install -g ccusage` or `pip install ccusage`
Owner: ELON installs, hands to Whetstone for dashboard integration.

**4. DeepInfra — Free inference tier addition to router**
Why: W4 added it to the confirmed free-tier list. More model variety than Groq/Cerebras. Haiku-tier routing candidate.
Install: Register at deepinfra.com, add DEEPINFRA_API_KEY to .env, wire into `thunderbird_model_router.py`.
Owner: Whetstone fleet.

**5. Skyvern — Open-source browser automation (Akamai alternative path)**
Why: W1-W4 consistent. Skyvern is specifically designed for web tasks on hard sites. Free, open source. Doesn't solve Regent alone but gives us a new tool in the rotation for when Playwright fails.
Install: `pip install skyvern` | `git clone https://github.com/Skyvern-AI/skyvern`
Owner: ELON fleet — test against Centrav and non-Akamai portals first.

**6. Temporal — Durable agent workflow engine**
Why: W4 makes this the strongest recommendation for replacing systemd timers for long-running retry-heavy AI jobs. Free self-hosted. Our current timer infrastructure is fragile (14 timers calling Claude). Temporal gives us durable execution with retries, visibility, and event triggers.
Install: `pip install temporalio` | Docker: `temporalio/auto-setup`
Owner: Sterling evaluates for OODA loop heartbeat replacement — this is an architecture conversation.
Note: This one warrants a T2 exercise before we wire it in. Don't just drop it on top of systemd.

---

### EVALUATE — Needs 1 sprint of research before wiring

**7. Inngest — Event-driven scheduling layer**
Why: 4 waves of consistent signal. Cloud-hosted, free tier. But we need to map it against our existing `OpsCenter/option1_parallel_spawn.py` and cron infrastructure before committing. Risk of duplication with Claude Managed Agents (W3 assignment, Hale).
Action: Dembe runs a 48h eval — does Inngest replace or complement what we have?

**8. LlamaParse — Travel PDF extraction (commercial alternative to Docling)**
Why: W3+W4 consistent. Better for layout-complex docs than Docling for some formats. BUT it's API-first with a free tier cap. We should trial it against Docling on 3 real cruise brochures before picking one.
Action: Sterling runs head-to-head on Silver Muse, Grandeur, and Viking Mars brochures.

**9. Revinate — Hospitality-native lifecycle email automation**
Why: Only tool in category #15 (AI Email Intelligence) with genuine travel/hospitality-native DNA. But it's not cheap and targets hotels, not travel advisors. Before evaluating cost: does it do anything our current Gmail + lifecycle TP system doesn't? Probably not yet. But watch it.
Action: Dembe gets a product brief. 30-day watch.

**10. CloakBrowser — Stealth Chromium for Akamai**
Why: W4 new signal. Specifically targets anti-bot systems. Potential unlock for Regent portal (MISSION-214). But it's unclear on licensing and cost.
Action: ELON fleet — check licensing, spin up against a test Akamai wall. If free/open: GO immediately.

**11. Omnigent (Databricks) — Meta-harness for multi-agent governance**
Why: 4,209 stars on MISSION-291 ELON WATCHLIST. W4 confirmed it as "the clearest 2026 open-source framework at the meta-harness/coordination level." Hot-swaps Claude Code, Codex, Pi agents. But this is architecture-level — it would reshape how our fleet self-orchestrates.
Action: ELON fleet reads the repo. If it reduces our spawn complexity, that's a GO. If it adds a layer, it's HOLD. Target: evaluation report to Commander by Monday.

---

### HOLD — Paid, complex, or wrong timing

**12. Vapi — Voice AI for client calls**
Why: W4+W3 name it as the 1-person luxury agency voice leader. But this is a paid product and touches the client communication path. Sterling's 7-day canary applies. Not urgent — we don't have an active client voice requirement right now.
Hold trigger: Commander says "I want clients to be able to call and reach an AI." Until then: HOLD.

**13. Temporal (production deployment)**
Listed in GO NOW as an evaluate candidate. But the production replacement of our timer infrastructure is a T2 exercise minimum — Sterling owns the gate here. The evaluation is GO NOW. The production wire-in is HOLD pending that exercise.

**14. Open-weight local LLMs (Llama/Qwen/Phi on YOGA)**
Why: W4 confirms Llama 3.1/3.2 8B, Qwen 2.5 7B/14B, Phi-4 Mini are the practical options for 16-32GB RAM. YOGA has the hardware. BUT: we already have Groq, Cerebras, and OpenRouter free. Local inference only makes sense if we need privacy (PII processing) or the free tier quotas are inadequate. We don't have that problem today.
Hold trigger: OpenRouter/Groq/Cerebras quotas start binding. Re-evaluate Q3 2026.

**15. LLM cost metering (Helicone/LangSmith)**
Why: W4 category #19 shows Helicone and LangSmith as attribution tools. But they work against API billing, not Claude MAX subscription pools. The attribution problem is fundamentally opaque at MAX plan level. ccusage (item #3 above) is the correct $0 answer.
Hold: Until we move significant spend to API billing, these are wrong-tier tools.

---

## ARCHITECTURE FLAGS — DECISIONS TO REVISIT

1. **Qdrant vs pgvectorscale**: W4 is the 4th consecutive wave saying pgvectorscale is becoming the 2026 default. Whetstone has this — but I'm flagging it as a Commander-visible decision. We built on Qdrant. Migrating is not trivial. The window to move cheaply is now, before we grow the collection. Whetstone needs to bring a concrete migration plan, not just a research note.

2. **Free inference router gap**: We have Groq and DeepSeek on OpenRouter. Cerebras adds a speed dimension (burst tasks). DeepInfra adds model variety. W4 makes the full free-tier stack clear — we should be running at least 4 free inference endpoints, not 2. This is Whetstone's lane but ELON is flagging it.

3. **Systemd timer fragility**: 14 timers calling Claude is the burn pattern. Temporal could replace the entire stack with retry logic, observability, and event triggers baked in. This is not an impulse change — it's a T2 exercise. But W4 is the fourth wave pointing at this gap.

4. **Anthropic API vs MAX subscription**: Category #19 confirmed MAX plan usage is opaque to third-party cost tools. If Commander ever wants per-persona cost attribution, we need to either (a) move those personas to API billing or (b) instrument via ccusage. Commander should know this ceiling exists.

---

## WEAK SPOTS CONFIRMED (categories #2, #13, #29)

- **#2 MCP Registry**: Perplexity can't reliably surface new MCP server releases — it returns social/blog noise. Direct fetch from mcp.so + glama.ai is the only reliable path. This is a known gap; no change recommended.
- **#13 Cruise Line Intel**: Confirmed again. Regent/Silversea/Viking do not publish enough structured data for Perplexity to synthesize. Direct portal watch (MISSION-214) is the correct architecture.
- **#29 Human Discourse**: W4 category confirmed the community signal — AI coding assistants with tight IDE integration are winning, broad agent platforms are viewed skeptically. This VALIDATES our Thunderbird architecture (Claude Code as the spine, specialist tools at the edges).

---

## SUMMARY SCOREBOARD

| Status | Count | Items |
|---|---|---|
| GO NOW (free, wire today) | 5 | Cerebras, Docling, ccusage, DeepInfra, Skyvern |
| GO NOW (needs T2) | 1 | Temporal — evaluate immediately, wire after exercise |
| EVALUATE (48h sprint) | 5 | Inngest, LlamaParse, Revinate, CloakBrowser, Omnigent |
| HOLD (paid/wrong timing) | 4 | Vapi, Temporal-prod, Local LLMs, Helicone/LangSmith |

Total new items from Wave 4 not previously in any wave: Cerebras (speed signal), CloakBrowser (Akamai), ccusage (MAX attribution).
Strongest compounding signal: Temporal (scheduling), Docling (PDF), pgvectorscale (vector).

---

*ELON, A12 Innovation & Disruption | 2026-06-21 | Wave 4 complete 13:46 MT*
*Source files: wave1-4_2026-06-21_*.json in /home/john/Thunderbird/intel/daily_search/*
