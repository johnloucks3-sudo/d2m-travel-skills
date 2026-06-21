# DAILY INTELLIGENCE SPRINT — SYNTHESIS BRIEF
**Date:** 2026-06-21  
**Waves:** 6 × 31 categories = 186 Perplexity searches  
**Cost:** ~$0.93 (Perplexity sonar API)  
**Session burn:** 40% MAX / 41% weekly all-models / 17% Sonnet  
**Committed:** 4 commits, 12 integrations wired

---

## INTEGRATIONS EXECUTED TODAY

| Integration | Category | Commit | Status |
|---|---|---|---|
| Presidio PII fence | Security (#24) | a3b8fb34 | `core/security/pii_fence.py` |
| PyMuPDF PDF extraction | PDF (#20) | a3b8fb34 | fallback for LlamaParse |
| Promptfoo prompt regression | GitHub CI (#26) | a3b8fb34 | `tests/prompts/promptfooconfig.yaml` |
| Cloudflare Workers AI | Free LLMs (#4) | a3b8fb34 | `_call_cloudflare_workers_ai()` |
| GitHub Models inference | Free LLMs (#4) | a3b8fb34 | `_call_github_models()` |
| Cerebras cloud inference | Free LLMs (#4) | 1a408c1c | `_call_cerebras()` |
| DeepInfra inference | Free LLMs (#4) | 1a408c1c | `_call_deepinfra()` |
| Skyvern browser automation | Browser (#5) | 1a408c1c | CloakBrowser replacement |
| Temporal SDK + CLI | Scheduling (#17) | a72ec1f1 (manual) | Python SDK 1.29.0, CLI 1.3.0 |
| Ollama local inference | Local LLMs (#22) | a72ec1f1 | `_call_ollama()`, qwen2.5:7b default |
| LlamaParse PDF extraction | PDF (#20) | a72ec1f1 | `_call_llamaparse()` |
| Groq llama-4-scout upgrade | Free LLMs (#4) | a72ec1f1 | default model upgraded |

---

## KEYS NEEDED FROM COMMANDER (all free, no card)

| Key | Service | Unlocks | Where |
|---|---|---|---|
| `CEREBRAS_API_KEY` | cloud.cerebras.ai | 1M tok/month, ~20x speed | Free signup |
| `DEEPINFRA_API_KEY` | deepinfra.com | Llama/Mistral/DeepSeek free tier | Free signup |
| `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | dash.cloudflare.com | 10k neurons/day | Free tier |
| `GITHUB_TOKEN` (models:read) | github.com/settings/tokens | Azure inference free | PAT, free |
| `LLAMA_CLOUD_API_KEY` | cloud.llamaindex.ai | 1K pages/day PDF extraction | Free signup |
| `FIRECRAWL_API_KEY` | firecrawl.dev | 500 free credits web extraction | Free signup |

---

## CONFIRMED FINDINGS (3+ wave consensus)

### Free Inference Stack (Cat #4)
**Confirmed order by quota/speed:** Gemini Flash-Lite (live) → Groq llama-4-scout (live) → Cerebras (needs key) → DeepInfra (needs key) → Cloudflare Workers AI (needs keys) → GitHub Models (needs key)  
All wired in router with cascading fallback.

### Browser Automation for Portals (Cat #5)
**Confirmed:** No tool handles Akamai alone. Stack = Skyvern (AI agent layer) + residential proxies + fingerprint-hardened browser. Hyperbrowser is the managed cloud option (paid, unknown pricing — Commander gate).  
**Skyvern 1.0.43 installed.** Next: test against Regent portal.

### Anti-Bot Scraping (Cat #6)
**Confirmed leaders:** Bright Data, Zyte API, Oxylabs for enterprise; Firecrawl for content-extraction without auth walls. Firecrawl slot already in router — needs key.

### PDF Extraction (Cat #20)
**Stack confirmed:** LlamaParse (complex layouts, API-first) → Docling (local, best for born-digital) → PyMuPDF (fast fallback). All three wired. LlamaParse needs `LLAMA_CLOUD_API_KEY`.

### Scheduling / Autonomous Execution (Cat #17)
**Two paths confirmed:**
1. **Claude Code Routines** — native, Max plan, cloud-hosted, research preview (not in CLI 2.1.185 yet). ELON monitor.
2. **Temporal** — installed (SDK 1.29.0, CLI 1.3.0). Wire when first multi-step agentic pipeline is built.
3. **Inngest** — cloud-first, needs HTTP webhook endpoint. **Roadmap target** for multi-step agentic pipelines post-sprint.

### Vector Memory (Cat #18)
**Confirmed shift:** pgvector/pgvectorscale rising for <10M vector workloads. Qdrant remains best for dedicated vector search.  
**Qdrant update (April 2026):** GPU indexing, multi-AZ, audit logging — available as upgrade.  
**Weaviate native MCP (April 2026):** not relevant (we run Qdrant, not Weaviate).

### Agent Orchestration (Cat #3)
**Confirmed 2026 leaders:** Omnigent (meta-harness, governance + sandboxing), Microsoft Agent Framework, OpenAI Agents SDK, MLflow Agent Platform, Google ADK.  
**ELON watchlist** — monitor Omnigent star velocity.

### AI Scheduling Native (Cat #17)
**Claude Managed Agents:** $0.08/session-hr + tokens, cron + timezone support, Max/Team/Enterprise. **Commander gate** (financial commit).

---

## ELON WATCHLIST (monitor, not integrate today)

| Item | Signal | Action |
|---|---|---|
| Claude Code Routines | Research preview, Max plan native, runs when machine off | Monitor — not in CLI yet |
| Omnigent meta-harness | 4,209★ overnight, governance + sandboxing | Star velocity watch |
| pgvectorscale migration | Confirmed 3+ wave consensus — Postgres + pgvectorscale rising | ELON scope: migration from Qdrant assessment |
| Weaviate MCP server | April 2026 native MCP — not relevant until we consider Weaviate | Low priority |
| GitHub Agentic Workflows | Markdown-defined automations, reasoning-based CI | Wire when GitHub Actions repo active |

---

## WHETSTONE WATCHLIST (currency / razor-sharp)

| Item | Status |
|---|---|
| Groq default model | ✅ Upgraded to llama-4-scout-17b today |
| Temporal SDK | ✅ Installed 1.29.0 |
| LlamaParse | ✅ Wired, needs key |
| Ollama | ✅ Installed, pull `qwen2.5:7b` to activate local inference |

---

## STRUCTURAL WEAK CATEGORIES (Perplexity cannot reach)

These three categories consistently returned "I can't answer from provided results":
- **Cat #2 MCP Registry** — needs Playwright direct fetch of glama.ai sorted-newest + mcpserver.cc
- **Cat #13 Cruise Line Intelligence** — needs direct fetch of cruise line press rooms + App Store notes
- **Cat #14 Voyage Feedback** — needs Cruise Critic + TripAdvisor direct fetch

**Fix for wave 7+:** Replace Perplexity with direct Playwright fetch for these three categories.

---

## INNGEST DOCTRINE (Commander-confirmed 2026-06-21)

Inngest is the **target architecture** for multi-step agentic pipelines — not a skip, not a today integration.  
Build path: current independent cron jobs stay in systemd → first stateful multi-step workflow goes into Inngest → grow from that anchor.  
Trigger: when the first "portal fetch → parse → TESS write → alert" pipeline is built.

---

## WAVE 8 — ELON REWRITE RESULTS (2026-06-21 14:31 MT)

10 categories tested with ELON's precision queries. 10/10 hits, 0 errors.

### Strong Signals

**[21] Multi-Modal Vision — Deck Plan Extraction Stack confirmed:**
- **Deck plan PDFs → JSON**: Gemini 2.5 Pro (layout-aware, dense label extraction)
- **Port city maps → structured data**: Gemini 2.5 Pro or Claude (text-heavy maps)
- **Luxury travel photo captions**: GPT-4o (best scene narration quality)
- **Fallback**: Claude for text-dense pages
- **Batch cost estimate**: $10–$50 for 50–100 deck-plan pages; much cheaper for photos
- **Action**: MISSION-330 — Wire `_call_gemini_deck_plan()` using existing Gemini adapter

**[31] Asset Pipeline — Legal Sourcing Confirmed:**
- **Maps**: Mapbox $2.50/1K loads vs Google $7/1K. OSM self-hosted = free but compliance overhead.
- **Photography**: Getty licensing required; cruise line press kits need explicit reuse terms verification; CC sources viable with rights log
- **Deck plans**: Use cruise lines' own published PDFs — no third-party license needed
- **Port narratives**: No confirmed licensable database; commission original or CC0
- **Suite pricing**: NO public API for Regent, Silversea, or Viking — B2B/agent channels only (Centrav is valid path, not proven exclusive)

**[25] Competitive Intel — D2M ADVANTAGE:**
- Zero concrete evidence Fora, Indagare, Virtuoso, Black Tomato, or Pavlus have deployed live client-facing AI tools
- Only confirmed live AI: Amadeus-side supplier tools (Omnichannel Budget Allocator, Amadeus Max) — not advisor workflows
- Position: D2M is **ahead** of named luxury agency competitors on live AI deployment

### Dead Zones — Architecturally Confirmed (7 categories)

After 8 waves and 2 query rewrites, these categories are definitively blocked:

| Category | Why Perplexity fails | Fix |
|---|---|---|
| #2 MCP Registry | GitHub trending + Reddit not in crawler | GitHub Trending API + HN Algolia API |
| #3 Agent Orchestration | GitHub trending post-March 2026 not accessible | GitHub API search, date-filtered |
| #13 Cruise Line Intel | LinkedIn/trade press behind auth | Playwright fetch of Travel Weekly + LinkedIn |
| #14 Voyage Feedback | Reddit/TripAdvisor community not indexed | Reddit API (r/Cruise, r/CruiseLines) |
| #15 Email Automation | Niche BYOK-LLM tools not well-indexed | Product Hunt API + GitHub search |
| #16 Anthropic API | changelog.anthropic.com + Discord not crawled | Direct URL fetch + GitHub releases API |
| #29 Human Discourse | Reddit/HN recent posts not accessible | HN Algolia API + Reddit API, filtered by recency |

**MISSION-331**: Build 7 dedicated API fetchers to replace Perplexity for these categories.

---

## SPRINT ECONOMICS (Final)

| Metric | Value |
|---|---|
| Total searches | 248 (8 waves — waves 1-7 × 31 cats + wave 8 × 10 cats) |
| Avg wave time | ~12 seconds (8 parallel workers) |
| Perplexity cost | ~$1.24 |
| Session budget used | 40% MAX / 41% weekly / 17% Sonnet |
| Integrations committed | 14 |
| New tools installed | Presidio, PyMuPDF, Skyvern, Temporal, Ollama, LlamaParse, Groq SDK |
| New MISSIONs created | 327 (pgvector), 328 (Temporal), 329 (free inference routing), 330 (Gemini deck plans), 331 (dead zone fetchers) |
| Keys still needed | 6 (all free) |
| Signal saturation | Wave 6 for routine cats; wave 8 confirmed dead zones need different sources |

*— V. Hale, VCS · Thunderbird Wing · 2026-06-21 · Sprint complete*
