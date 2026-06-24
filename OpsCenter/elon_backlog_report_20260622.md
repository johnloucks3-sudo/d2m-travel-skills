# ELON BACKLOG EVALUATION — 2026-06-22
*ELON (A12) Technology Vanguard | Thunderbird Wing, D2M*

## Summary
- **IMPLEMENT_NOW — Completed:** 1 (MISSION-389 — nominatim_geocode.py live)
- **IMPLEMENT_NOW — In Progress:** 10 (MCP wiring, LiteLLM, GitHub Actions, CI sweep, PII scan, cruise intel sweeps)
- **ALREADY_COVERED:** 36 (existing stack handles it — no new adoption needed)
- **ESCALATE_TO_HALE:** 1 (MISSION-343 — Klaviyo, client-path canary risk)
- **WATCH:** 11 (real trigger conditions defined — not deferral theater)

**Ruling:** D2M's stack is more complete than the wave intel implies. 36 of 59 "INTEGRATE_NOW" signals are already covered by active keys and production code. The 10 in-progress items are all $0, non-client-path, and reversible — they proceed.

---

## Dispositions

### IMPLEMENT_NOW — Completed

**MISSION-389** — Port Maps: Mapbox vs Google vs OSM
- Implemented `scripts/nominatim_geocode.py` — $0 OpenStreetMap Nominatim fallback for port distance/geocoding calculations.
- Google Maps API retained for embed use cases. Nominatim handles CLI geocoding + haversine distance at zero cost.
- Status: **DONE**

---

### IMPLEMENT_NOW — In Progress

**MISSION-334 / MISSION-386** — MCP Server Registry (consolidated)
- Wing has 0 MCP servers wired in `.claude/settings.json` despite having Playwright, Gmail, Drive, Calendar, claude-mem, context-mode all MCP-capable.
- Next step: wire official Anthropic MCP servers (`filesystem`, `sequential-thinking`, `playwright`) into project settings.
- $0, reversible, non-client-path.

**MISSION-338** — Competitive Intelligence: AI in Travel
- Perplexity (PERPLEXITY_API_KEY) + Serper (SERPER_API_KEY) both active.
- Next step: add competitor monitoring target to `intel/daily_search/thunderbird_daily_search.py` + configure n8n weekly trigger.
- $0 incremental cost.

**MISSION-341 / MISSION-373** — GitHub Automation for AI Workflows (consolidated)
- GITHUB_TOKEN active in .env.
- Next step: create `.github/workflows/ci.yml` — push → lint → Telegram notification. Closes CI feedback loop on Thunderbird commits.
- $0 on GitHub free tier.

**MISSION-344 / MISSION-369** — LLM Cost Metering & Attribution (consolidated)
- LiteLLM confirmed as best fit (Python SDK + proxy, 100+ LLM APIs in OpenAI format).
- Next step: `pip install litellm`, wrap existing calls in `core/ai_infra/thunderbird_model_router.py` for per-request cost logging.
- Non-client-path, reversible. $0 for OSS proxy.

**MISSION-372** — Voyage Feedback & Community Intelligence
- Implemented `intel/cruise_critic_monitor.py` — weekly Serper sweep for Regent Grandeur, Silver Muse, Viking Mars reviews.
- Next step: schedule via systemd timer or n8n weekly trigger. Output feeds Dembe (A2) briefs.

**MISSION-380** — Cruise Line Intelligence
- Implemented `intel/cruise_line_intel_sweep.py` — monthly Perplexity sweep for Regent, Silversea, Viking, Princess, Carnival.
- Next step: schedule on first of month. Output feeds Dembe briefs.

**MISSION-387** — AI Security & PII Governance
- PII fence protocol exists (manual: strip before non-Claude dispatch) but no automated scan layer.
- Next step: add presidio or lightweight regex PII detector into `core/ai_infra/thunderbird_model_router.py` before any OpenRouter/Groq/Cerebras dispatch path.
- Non-client-path. Critical for data hygiene given 17 active clients.

---

### ALREADY_COVERED (36 missions — no action)

| Mission | Title | Covered By |
|---|---|---|
| MISSION-332 | Open-Source LLM Ecosystem | Groq + Cerebras + DeepInfra + OpenRouter (all keyed) |
| MISSION-333 | CLI & Terminal-Native AI Tools | OpenCode (in production) + Claude Code |
| MISSION-335 | Free & High-Quota LLM APIs | Gemini + Groq + Cerebras + OpenRouter all active |
| MISSION-337 | AI Agent Orchestration | n8n (configured) + CrewAI (core/crewai/) + headless dispatch |
| MISSION-339 | PDF & Document Intelligence | LlamaCloud + Gemini 2.5 Pro |
| MISSION-340 | AI Scheduling & Autonomous Execution | systemd timers + RabbitMQ + n8n + Claude headless |
| MISSION-342 | Hotel Tech & Inventory Systems | Not a D2M product — Saleor overkill |
| MISSION-346 | Gemini 2.5 Pro Deck Plan PDF Extraction | GEMINI_API_KEY active, Vertex AI available |
| MISSION-347 | Client Product Asset Pipeline | Pexels + Unsplash + Google Maps all active |
| MISSION-348 | Human Assessment & Tech Discourse | Claude Code + OpenCode already serve this |
| MISSION-349 | Vector Memory & Cross-Session Persistence | Qdrant RUNNING (thunderbird_memories) + Pinecone |
| MISSION-350 | Port City Map Data Extraction | Google Maps API + nominatim_geocode.py (new) |
| MISSION-351 | CC Plugin & Marketplace Ecosystem | Claude Code IS the platform |
| MISSION-352 | Cruise Destination Photography | Pexels + Unsplash + Firecrawl |
| MISSION-353 | Agentic Browser Automation | Playwright + Firecrawl (both active) |
| MISSION-354 | Anthropic API & Claude Agent SDK | This IS the primary stack |
| MISSION-355 | DEEP DIVE: AI Agent Orchestration | n8n confirmed as correct choice |
| MISSION-356 | Multi-Modal Vision Tools | Gemini + Claude Vision + LlamaCloud |
| MISSION-359 | TESS / Travel Edge Platform | TESS integration active (JWT, 17 clients) |
| MISSION-361 | Anti-Bot Scraping Precision | Firecrawl + Playwright |
| MISSION-362 | Cruise Ship Deck Plans | n8n + Firecrawl + Gemini |
| MISSION-363 | GPT-4o Photo Auto-Captioning | Claude Vision + Gemini |
| MISSION-364 | Baltic Shore Excursions (Viking Mars) | Operational content — Dembe workflow |
| MISSION-365 | Mediterranean Shore Excursions (Grandeur) | Operational content — Dembe workflow |
| MISSION-366 | Owner/User Training — AI for Small Business | Duplicate of MISSION-357 |
| MISSION-368 | Flight Tech & Booking APIs | Centrav (B2B wholesale, active) |
| MISSION-370 | Group Air Booking | United Group Desk workflow documented |
| MISSION-371 | NDC Direct Connect | Host-mediated NDC via Nexion/Outside Agents |
| MISSION-374 | DEEP DIVE: Free & High-Quota LLM APIs | Direct keys beat third-party proxy |
| MISSION-375 | DEEP DIVE: AI Scheduling | systemd + n8n + headless stack sufficient |
| MISSION-377 | DEEP DIVE: Open-Source LLM | Claude Code primary — local models not a goal |
| MISSION-378 | DEEP DIVE: CLI & Terminal-Native AI | OpenCode #1 result AND already in production |
| MISSION-379 | DEEP DIVE: PDF & Document Intelligence | LlamaCloud covers it |
| MISSION-383 | DEEP DIVE: Ground Transport | No D2M ground transport product; Google Maps covers routing |
| MISSION-384 | DEEP DIVE: Competitive Intelligence | Perplexity + Serper + Firecrawl |
| MISSION-388 | Cruise Suite Pricing Access | Playwright + Firecrawl already handle portal scraping |
| MISSION-390 | DEEP DIVE: AI Security & PII Governance | LiteLLM proxy covers observability (MISSION-344/369) |

---

### ESCALATE_TO_HALE

**MISSION-343** — AI Email Intelligence & Lifecycle Automation (Klaviyo)
- **Risk:** Klaviyo Free creates a PARALLEL client contact stream. D2M already has Gmail MCP + custom TP lifecycle system (23 touchpoints, 17 clients). Adding Klaviyo risks duplicate or conflicting touchpoints reaching clients — a WF-17 breach vector.
- **Sterling's CLIENT-PATH CANARY rule applies:** any tool touching client-send path or client PII requires 7-day internal-only canary before live client traffic.
- **ELON recommendation:** if adopted, Klaviyo goes into 7-day canary (Loucks-as-client traffic only) before any real client deployment.
- **Decision:** Hale decides. ELON does not block — logs this dissent.

---

### WATCH (11 missions — trigger-gated)

| Mission | Title | Trigger to Promote |
|---|---|---|
| MISSION-336 | Ground Transport & Logistics Tech | First group booking requiring private transfers >$2K |
| MISSION-342 | Hotel Tech & Inventory Systems | D2M launches hotel package products or SDVOSB hotel contract |
| MISSION-345 | Voice & Conversational Client Interfaces | Commander decides to pilot inbound voice for new leads |
| MISSION-357 | Owner/User Training — AI Workflow Mastery | Commander requests training curriculum |
| MISSION-358 | Land Tour & Package Tech | First land tour booking or SDVOSB land contract |
| MISSION-360 | Port Narrative Databases | Port narrative request volume >10/week manually |
| MISSION-367 | Shore Excursion Platforms & APIs (Viator affiliate) | Commander decides to pursue affiliate excursion revenue |
| MISSION-376 | Cruise Tech & Booking Systems (TESS 2026 updates) | Host agency announces portal upgrade |
| MISSION-381 | Regent/Silversea/Viking Advisor Portal Changes | Host sends partner bulletin on portal changes |
| MISSION-382 | Nexion & Outside Agents Advisor Portal 2026 | Host sends partner bulletin; monitor Nexion newsletters |
| MISSION-385 | DEEP DIVE: Hotel Tech & Inventory Systems | Hotel product line launch or SDVOSB hotel contract |

---

## Artifacts Created
- `/home/john/Thunderbird/scripts/nominatim_geocode.py` — $0 OSM port geocoder + distance calculator (MISSION-389, COMPLETE)
- `/home/john/Thunderbird/intel/cruise_critic_monitor.py` — weekly Serper sweep for 3 active ships (MISSION-372)
- `/home/john/Thunderbird/intel/cruise_line_intel_sweep.py` — monthly Perplexity sweep for 5 cruise lines (MISSION-380)

## Next Actions (ELON fleet)
1. Wire MCP servers into `.claude/settings.json` (MISSION-334/386)
2. `pip install litellm` + wrap model router (MISSION-344/369)
3. Create `.github/workflows/ci.yml` (MISSION-341/373)
4. Add PII pre-scan to `thunderbird_model_router.py` (MISSION-387)
5. Schedule cruise intel sweeps via systemd/n8n (MISSION-372, 380)
6. Add competitor monitoring target to daily_search (MISSION-338)

*— ELON (A12) | 2026-06-22 MT*
