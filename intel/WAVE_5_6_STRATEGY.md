# THUNDERBIRD OS — WAVE 5 & 6 DEPLOYMENT STRATEGY
## Dreams2Memories Travel, LLC
## Strategic Planning: Lt Col Ryan "Viper" Castillo, A5
## Date: 2026-03-20 | Classification: INTERNAL — COMMANDER EYES

---

## STRATEGIC CONTEXT

Waves 1-4 built the machine: 13,850+ lines of learning infrastructure, persona memory, voice ledger, security hardening, A2A protocol, temporal knowledge graphs. The machine observes, remembers, and learns.

Waves 5 and 6 are about making the machine earn money and become impossible to replicate.

The competitive landscape says this clearly: ChatGPT abandoned direct bookings, 30% of travelers use AI for planning but only 2% trust AI to book, and every major tech company is building multi-agent orchestration. D2M's position -- AI-powered concierge with human trust at the close -- is exactly where the market is moving. The question is no longer "are we building the right thing?" It is "how fast can we widen the moat?"

Three vectors define these waves:

1. **Revenue Generation** -- Every feature must either create new revenue or protect existing margin
2. **Data Moat** -- Every client interaction should make the system smarter in ways competitors cannot replicate
3. **Commander Liberation** -- Remove John from every routine task so he can focus exclusively on relationship-building and closing

---

## WAVE 5: WEEKS 1-3 (APR 2026) — "REVENUE ENGINE"

**Theme:** Turn Thunderbird from an operations platform into a revenue-generating weapon. Every item here either puts money in the door or prevents it from walking out.

---

### 5.1 DANI VOICE AGENT — Phone Channel

**What it does for D2M:** Dani answers the Dreams2Memories phone number 24/7. Client calls in, hears a warm concierge voice, gets their question answered or their request captured. After-hours calls stop going to voicemail. 85% of callers who hit voicemail never call back -- that is revenue bleeding out.

- **Innovation:** Retell AI voice frontend + Thunderbird MCP backend + Dani persona voice profile
- **Build vs Buy vs Integrate:** BUILD the integration layer. BUY the voice infrastructure (Retell AI at $0.07/min).
- **Estimated LOE:** 5-7 days. Voice persona design (1 day), Retell API integration (2 days), MCP backend wiring (1 day), COS review gate for commitments (1 day), testing (1-2 days).
- **Dependencies:** Retell AI signup (pending), `thunderbird_dani_voice.py` (570 lines, exists but needs Retell wiring), voice ledger client rules (`thunderbird_voice_ledger.py`), COS review gate in `thunderbird_dani_engine.py`
- **Revenue impact:** Every after-hours call caught is a potential $5,000-50,000 booking saved. At even one recovered inquiry per month, this pays for itself 100x.
- **Key files:** `thunderbird_dani_voice.py`, `thunderbird_dani_engine.py`, `thunderbird_voice_ledger.py`

---

### 5.2 CLIENT AUDIO BRIEFINGS — The "Listen to Your Trip" Differentiator

**What it does for D2M:** Generate 5-10 minute audio overviews from trip dossiers. "Hey Missy, here's your Scandinavia trip overview -- listen on your commute." No luxury travel agency on the planet does this. It turns a static PDF into a personal experience a couple can listen to together over dinner.

- **Innovation:** NotebookLM-style audio generation from dossier content, delivered via client portal or email link
- **Build vs Buy vs Integrate:** BUILD using TTS API (ElevenLabs or OpenAI TTS) + dossier summarization pipeline. `thunderbird_audio_briefing.py` (752 lines) already exists.
- **Estimated LOE:** 4-5 days. TTS provider integration (1 day), dossier-to-script pipeline (2 days), audio hosting on portal or Google Drive (1 day), delivery mechanism (1 day).
- **Dependencies:** `thunderbird_audio_briefing.py` (exists, needs TTS wiring), ElevenLabs API key or OpenAI TTS, `portal/server.py` for client playback, dossier content from `dossiers/`
- **Revenue impact:** Pure differentiation. This is the kind of thing clients tell their friends about. Word-of-mouth referral driver.
- **Key files:** `thunderbird_audio_briefing.py`, `thunderbird_dossier.py`, `portal/server.py`

---

### 5.3 GEMINI DEEP RESEARCH — A2 Force Multiplier

**What it does for D2M:** When Commander says "research Mediterranean options for the Kuklinski group," Deep Research autonomously browses 100+ sources, reads reviews, checks advisories, compares cruise lines, and produces a structured brief with citations. A2 (Wraith) adds the D2M relevance layer on top. What used to take hours takes minutes.

- **Innovation:** Gemini Deep Research API as an A2 research tool via MCP, plus Perplexity API for citation-rich supplemental research
- **Build vs Buy vs Integrate:** INTEGRATE. Add as MCP tools. Both have API access.
- **Estimated LOE:** 3-4 days. Gemini Deep Research MCP tool (1.5 days), Perplexity API MCP tool (1 day), citation formatting pipeline (0.5 day), A2 persona prompt updates (0.5 day).
- **Dependencies:** Google AI API key (may already have one), Perplexity API signup (pending on external list), `thunderbird_intel_crew.py`, `thunderbird_competitive_surveillance.py`
- **Revenue impact:** Faster research means faster proposals means faster closes. Research quality directly impacts Commander's credibility with clients.
- **Key files:** `thunderbird_intel_crew.py`, `thunderbird_competitive_surveillance.py`, `thunderbird_world_intel.py`, `travel_mcp_server.py`

---

### 5.4 FIRECRAWL + AVEN HOSPITALITY — Supply Chain Intelligence

**What it does for D2M:** Firecrawl replaces fragile `browse_url` scraping with production-grade web extraction for cruise line rates, hotel pricing, and competitor monitoring. Aven Hospitality's MCP-enabled hotel distribution (35,000+ properties) gives D2M direct rate queries without portal logins.

- **Innovation:** Firecrawl MCP for structured web scraping; Aven Hospitality MCP for direct hotel availability/rates
- **Build vs Buy vs Integrate:** INTEGRATE both. Firecrawl free tier (500 credits/mo). Aven Early Access Program.
- **Estimated LOE:** 2-3 days. Firecrawl MCP install (0.5 day), rate monitoring workflows (1 day), Aven Early Access application and initial integration (1-1.5 days).
- **Dependencies:** Firecrawl API signup (pending), Aven Early Access application (email media@avenhospitality.com), `thunderbird_hotel_search.py`, `thunderbird_price_monitor.py`
- **Revenue impact:** Better rate intelligence means better pricing for clients. Automated monitoring means Commander never misses a price drop on a booked property.
- **Key files:** `thunderbird_hotel_search.py`, `thunderbird_price_monitor.py`, `thunderbird_fare_watch.py`

---

### 5.5 SMART MODEL ROUTER — Cost Arbitrage at Scale

**What it does for D2M:** Automatically routes tasks to the cheapest model that can handle them. Opus for client proposals and grant narratives. Sonnet for standard email drafts and dossier updates. Haiku for file scans and status checks. Gemini Flash-Lite for bulk fare monitoring and email classification. Llama 4 Scout locally on YOGA for zero-cost data extraction. Projected 25-40% cost reduction on API-dependent tasks.

- **Innovation:** Multi-provider model router with automatic task classification and cost optimization
- **Build vs Buy vs Integrate:** BUILD. Upgrade existing `thunderbird_model_router.py` with task-to-model mapping and multi-provider support.
- **Estimated LOE:** 3-4 days. Task classification taxonomy (0.5 day), multi-provider API integration (1.5 days), subagent effort-level mapping (1 day), Llama 4 Scout local deployment via Ollama (1 day).
- **Dependencies:** `thunderbird_model_router.py` (exists), Ollama on YOGA for Llama 4, OpenAI API key for GPT-5.4-mini access, Google AI API key for Flash-Lite
- **Revenue impact:** Direct cost savings. On Max plan, less relevant for Claude usage, but critical for any external API calls, batch processing, and future scaling.
- **Key files:** `thunderbird_model_router.py`, `thunderbird_batch_run.py`, `.claude/agents/*.md`

---

### 5.6 CLIENT BULLETIN ENGINE — Proactive Revenue Touchpoints

**What it does for D2M:** Automated, personalized client bulletins. "The Regent Splendor just announced a new Mediterranean itinerary that matches your preferences." "Finnair adjusted schedules on your route -- here's what it means." These keep D2M in front of clients between bookings, drive repeat business, and position Commander as the advisor who is always watching.

- **Innovation:** `thunderbird_bulletin.py` (1,042 lines already built) wired to client preferences, fare watch alerts, and cruise line announcements
- **Build vs Buy vs Integrate:** BUILD the wiring. The bulletin engine exists but is not connected to the auto-enrich pipeline, fare watch, or competitive surveillance.
- **Estimated LOE:** 3-4 days. Wire bulletin to fare watch alerts (1 day), connect to competitive surveillance for cruise line news (1 day), client preference matching from dossiers (1 day), COS review gate before send (0.5 day).
- **Dependencies:** `thunderbird_bulletin.py` (exists), `thunderbird_fare_watch.py`, `thunderbird_competitive_surveillance.py`, `thunderbird_auto_enrich.py`, dossier preference data
- **Revenue impact:** Each bulletin is a touchpoint. Touchpoints drive repeat bookings. The advisor who sends relevant intel between trips wins the next booking.
- **Key files:** `thunderbird_bulletin.py`, `thunderbird_fare_watch.py`, `thunderbird_competitive_surveillance.py`, `thunderbird_auto_enrich.py`

---

### 5.7 N8N WORKFLOW INTELLIGENCE — AI Decision Nodes

**What it does for D2M:** Install the n8n MCP server so Claude can create, modify, and debug the 16 existing n8n workflows via natural language. Then upgrade key workflows with AI decision nodes: incoming email gets classified by AI (client inquiry vs. supplier confirmation vs. spam) and routed accordingly, instead of following fixed rules.

- **Innovation:** n8n MCP server for Claude-managed workflows + generative orchestration (AI decides routing at runtime)
- **Build vs Buy vs Integrate:** INTEGRATE n8n MCP server. BUILD AI decision nodes in workflows.
- **Estimated LOE:** 3-4 days. n8n MCP server install (0.5 day), Claude workflow management testing (0.5 day), AI classification node for email routing (1 day), AI decision node for alert prioritization (1 day), testing across existing 16 workflows (1 day).
- **Dependencies:** n8n instance on YOGA, n8n MCP server package, existing workflows in `deploy/n8n/` (16 JSON files), `thunderbird_email_classifier.py`
- **Revenue impact:** Reduces false-positive alerts (Commander stops ignoring notifications) and catches real opportunities faster.
- **Key files:** `deploy/n8n/*.json` (16 workflows), `thunderbird_email_classifier.py`, `thunderbird_commander_inbox.py`

---

### WAVE 5 SUMMARY

| # | Innovation | LOE | B/B/I | Revenue Vector |
|---|-----------|-----|-------|----------------|
| 5.1 | Dani Voice Agent | 5-7 days | Build+Buy | Recovered calls = recovered bookings |
| 5.2 | Client Audio Briefings | 4-5 days | Build | Differentiation = referrals |
| 5.3 | Gemini Deep Research | 3-4 days | Integrate | Faster research = faster closes |
| 5.4 | Firecrawl + Aven | 2-3 days | Integrate | Better rates = better pricing |
| 5.5 | Smart Model Router | 3-4 days | Build | Cost reduction 25-40% |
| 5.6 | Client Bulletin Engine | 3-4 days | Build | Proactive touchpoints = repeat bookings |
| 5.7 | n8n AI Decision Nodes | 3-4 days | Integrate+Build | Faster routing = faster action |

**Total Wave 5 LOE:** 23-31 days of development effort
**Expected completion:** End of April 2026

---

## WAVE 6: WEEKS 4-7 (MAY 2026) — "DATA MOAT"

**Theme:** Build capabilities that get stronger with every client interaction. Create switching costs so high that clients could never get the same experience elsewhere. Turn Thunderbird from a tool into a platform.

---

### 6.1 SEMANTIC SEARCH LAYER — "Ask Anything About Any Client"

**What it does for D2M:** Vector embeddings across ALL D2M data -- dossiers, booking PDFs, email history, supplier contracts, intel reports, voice ledger entries. Commander asks "which clients have expressed interest in Mediterranean cruises?" and gets answers from across every data source. Currently, this question requires manually checking each dossier.

- **Innovation:** Cohere embeddings (or sqlite-vec) + vector database over entire D2M document corpus
- **Build vs Buy vs Integrate:** BUILD with open-source components. sqlite-vec keeps it local and free. Cohere embeddings for production quality.
- **Estimated LOE:** 5-7 days. Document ingestion pipeline (2 days), embedding generation (1 day), vector search API (1 day), query interface via MCP tool (1 day), initial corpus indexing (1-2 days).
- **Dependencies:** sqlite-vec (already referenced in master inventory as READY), `thunderbird_shared_memory.py`, all dossier files, email archives, booking PDFs
- **Revenue impact:** This is the data moat. Every email, every dossier update, every client interaction makes the search smarter. After 50 clients, no competitor can match the institutional knowledge locked in this system.
- **Key files:** `thunderbird_shared_memory.py`, `thunderbird_hud_memory.py`, `thunderbird_temporal_memory.py`, `dossiers/`

---

### 6.2 CONTINUOUS CONTEXT ENGINE — "Thunderbird Never Forgets"

**What it does for D2M:** Replace the manual `MEMORY.md` and `session_autosave_latest.md` system with automatic context persistence via hooks. Every session starts with full operational awareness. PostCompact hooks capture what survived compaction. SessionStart hooks inject the latest client context. SubagentStart hooks load persona-specific memory. The 8 Staff Skills ("capture the diff, extract the principle, apply forward") become automatic infrastructure, not behavioral aspirations.

- **Innovation:** Hook-driven continuous context (Continuous-Claude-v2 pattern) + official Anthropic Memory Tool + PostCompact hook for compaction recovery
- **Build vs Buy vs Integrate:** BUILD using hook system + existing memory infrastructure. INTEGRATE official Memory Tool when available.
- **Estimated LOE:** 5-6 days. PostCompact hook implementation (1 day), SessionStart context injection (1 day), SubagentStart/Stop hooks for persona memory (1.5 days), automatic diff-to-principle pipeline (1.5 days).
- **Dependencies:** Claude Code hooks system (operational), `thunderbird_learning.py`, `thunderbird_persona_memory.py`, `thunderbird_session_checkpoint.py`, `.claude/agents/*.md`
- **Revenue impact:** Indirect but massive. Context loss between sessions is the single biggest source of rework. Eliminating it saves 15-20% of operational time.
- **Key files:** `thunderbird_learning.py`, `thunderbird_persona_memory.py`, `thunderbird_session_checkpoint.py`, `thunderbird_conversation_learner.py`

---

### 6.3 TRIP ARCHITECT PRO — Interactive Itinerary Builder

**What it does for D2M:** The `thunderbird_trip_architect.py` (1,862 lines) is the biggest underutilized module in the codebase. Wire it to auto-enrich data, real-time pricing from Firecrawl/Aven, audio briefing generation, and the client portal. A client inquiry goes from "we want to go to Scandinavia" to a fully priced, visually rich, audio-narrated trip proposal in under an hour instead of a full day.

- **Innovation:** End-to-end proposal automation: Trip Architect + auto-enrich + real-time pricing + Canva visuals + audio briefing + portal delivery
- **Build vs Buy vs Integrate:** BUILD the integration wiring. All components exist separately.
- **Estimated LOE:** 6-8 days. Trip Architect to auto-enrich pipeline (1.5 days), real-time pricing integration (1.5 days), Canva MCP visual generation (1 day), audio briefing attachment (1 day), portal delivery endpoint (1 day), end-to-end testing (1-2 days).
- **Dependencies:** `thunderbird_trip_architect.py` (exists, 1,862 lines), `thunderbird_auto_enrich.py`, Canva MCP (already connected), `thunderbird_audio_briefing.py`, `portal/server.py`, Wave 5 items 5.2 and 5.4
- **Revenue impact:** Speed kills in luxury travel. The advisor who delivers a beautiful, comprehensive proposal first wins the booking. Cutting proposal time from 8 hours to 1 hour means Commander can handle 4-5x more prospects.
- **Key files:** `thunderbird_trip_architect.py`, `thunderbird_auto_enrich.py`, `thunderbird_quote_render.py`, `portal/server.py`

---

### 6.4 MULTI-CHANNEL DANI — OpenClaw Gateway

**What it does for D2M:** Deploy Dani on every channel clients use -- Telegram, WhatsApp, Signal, iMessage, SMS -- through a single gateway. Currently Dani only lives on Telegram and email. OpenClaw (210K GitHub stars) routes all channels through one local gateway on YOGA. One Dani brain, every channel.

- **Innovation:** OpenClaw local gateway for multi-channel AI concierge deployment
- **Build vs Buy vs Integrate:** INTEGRATE OpenClaw. BUILD channel-specific adaptations (WhatsApp has media limitations, SMS has character limits, etc.).
- **Estimated LOE:** 5-6 days. OpenClaw deployment on YOGA (1 day), Telegram channel migration/parallel (1 day), WhatsApp Business API setup (1.5 days), channel-specific message formatting (1 day), COS review gate across all channels (0.5 day).
- **Dependencies:** OpenClaw on YOGA, WhatsApp Business API approval, `thunderbird_telegram.py`, `thunderbird_dani_engine.py`, `thunderbird_whatsapp.py` (44 lines -- skeleton only)
- **Revenue impact:** Meet clients where they are. The Westbrooks might prefer WhatsApp. The Furlows might prefer iMessage. Removing channel friction removes booking friction.
- **Key files:** `thunderbird_telegram.py`, `thunderbird_dani_engine.py`, `thunderbird_whatsapp.py`

---

### 6.5 GRANT COMPILER + SUBMISSION ENGINE

**What it does for D2M:** Automate the grant application pipeline. The narrative is written. The SDVOSB and USAFA credentials are confirmed. Eight grant targets are identified. What is missing is the compilation-to-submission pipeline: pull the right narrative sections, format to each grant's requirements, generate supporting documentation (Thunderbird architecture diagrams, market validation data, financial projections), track submission deadlines, and manage follow-up.

- **Innovation:** Grant-specific document compiler + deadline tracking + automated formatting per grant requirements
- **Build vs Buy vs Integrate:** BUILD. This is custom to D2M's situation.
- **Estimated LOE:** 5-7 days. Grant requirement parser (1.5 days), narrative section mapper (1 day), financial projection generator via A9 (1 day), architecture diagram generation via Excalidraw or Canva (1 day), deadline tracker integrated with calendar (0.5 day), submission packaging (1 day).
- **Dependencies:** Grant narrative (v1 complete, backed up to Drive), `thunderbird_calendar_sync.py`, Canva MCP for visuals, A9 (Harlan) financial models, 8 target grants identified
- **Revenue impact:** DIRECT. SBIR/STTR grants range from $150K-$1.5M. SDVOSB set-asides add additional opportunities. Even one successful grant funds 2-3 years of Thunderbird development.
- **Key files:** Grant narrative on Google Drive, `thunderbird_calendar_sync.py`, `thunderbird_tasks.py`

---

### 6.6 OPERATIONS DASHBOARD — Real-Time Business Intelligence

**What it does for D2M:** A single screen showing everything that matters: active bookings and their status, upcoming payment deadlines, commission balances, fare watch alerts, dossier completeness scores, MCP tool health, client communication recency, pipeline value. Currently, this information is scattered across TESS, Google Sheets, dossiers, n8n, and email.

- **Innovation:** Centralized dashboard pulling from all Thunderbird data sources, served via client portal infrastructure
- **Build vs Buy vs Integrate:** BUILD. `thunderbird_dashboard.py` (984 lines) exists as a skeleton.
- **Estimated LOE:** 5-7 days. Data aggregation from TESS, booking master, dossiers (2 days), dashboard UI on portal infrastructure (2 days), real-time update via n8n triggers (1 day), mobile-responsive for Commander's Chromebook/phone (1 day).
- **Dependencies:** `thunderbird_dashboard.py` (exists), `portal/server.py`, TESS API, `thunderbird_reconciliation.py`, `thunderbird_fare_watch.py`, `thunderbird_dossier_scanner.py`, `thunderbird_health.py`
- **Revenue impact:** Commander sees the whole business at a glance. No more "I forgot that payment was due." No more "I didn't realize that fare dropped." Operational awareness protects revenue.
- **Key files:** `thunderbird_dashboard.py`, `portal/server.py`, `thunderbird_health.py`, `thunderbird_heartbeat.py`

---

### 6.7 KLIPY-STYLE AUTO-CRM — Every Interaction Builds the Dossier

**What it does for D2M:** Every email, every Telegram message, every phone call transcript (from Dani Voice), every booking confirmation automatically updates the client dossier. No manual entry. Commander sends a casual email to the Lyons mentioning dinner in Athens -- the dossier auto-captures "dinner interest, Athens, ~Aug 10." Currently, dossier updates are manual or semi-automated.

- **Innovation:** Auto-CRM pipeline: all communication channels feed into dossier enrichment engine with entity extraction and preference detection
- **Build vs Buy vs Integrate:** BUILD on existing infrastructure. `thunderbird_auto_enrich.py` does partial enrichment. Extend it to all channels with NLP entity/preference extraction.
- **Estimated LOE:** 4-5 days. Email-to-dossier pipeline (1.5 days), Telegram-to-dossier pipeline (1 day), voice transcript-to-dossier pipeline (1 day), entity/preference extraction (1 day), duplicate/conflict resolution (0.5 day).
- **Dependencies:** `thunderbird_auto_enrich.py`, `thunderbird_dossier.py`, `thunderbird_conversation_learner.py`, `thunderbird_dani_voice.py` (for voice transcripts), `thunderbird_gmail.py`
- **Revenue impact:** The dossier becomes a living document that knows the client better with every interaction. After 6 months, D2M's understanding of a client's preferences, travel style, dietary needs, and relationship dynamics is so deep that switching to another advisor would mean starting from zero.
- **Key files:** `thunderbird_auto_enrich.py`, `thunderbird_dossier.py`, `thunderbird_conversation_learner.py`, `thunderbird_info_delta.py`

---

### WAVE 6 SUMMARY

| # | Innovation | LOE | B/B/I | Moat Vector |
|---|-----------|-----|-------|-------------|
| 6.1 | Semantic Search Layer | 5-7 days | Build | Institutional knowledge compounds |
| 6.2 | Continuous Context Engine | 5-6 days | Build | Zero context loss = zero rework |
| 6.3 | Trip Architect Pro | 6-8 days | Build | Proposal speed = competitive kill shot |
| 6.4 | Multi-Channel Dani | 5-6 days | Integrate+Build | Meet clients on their channel |
| 6.5 | Grant Compiler | 5-7 days | Build | Direct funding = $150K-$1.5M |
| 6.6 | Operations Dashboard | 5-7 days | Build | Operational awareness protects revenue |
| 6.7 | Auto-CRM Pipeline | 4-5 days | Build | Every interaction deepens the moat |

**Total Wave 6 LOE:** 35-46 days of development effort
**Expected completion:** End of June 2026

---

## WAVE 7+ HORIZON — "THE FUTURE WAR"

Things that are not ready yet but could be transformative. Monitor quarterly.

---

### 7.1 A2A AGENT ECONOMY — Dani Negotiates with Hotel AIs

**What:** When hotel chains and cruise lines deploy their own AI agents (Aven is already doing this), Dani should be able to negotiate directly: "I have a client looking for a balcony suite on the Silver Nova, Aug 15-22. What's the best agent rate?" Agent-to-agent, protocol-native, no portals, no phone calls.

**Why not yet:** Supplier agent deployment is early (Aven Q2 2026 earliest). A2A protocol is v0.3. But D2M's A2A MCP tools (`a2a_ask`, `a2a_broadcast`, `a2a_chain`) position us to be day-one ready.

**Watch trigger:** Aven Early Access ships. Any cruise line announces A2A/MCP agent.

---

### 7.2 THUNDERBIRD AS A PLATFORM — White-Label for Travel Advisors

**What:** Package Thunderbird OS as a platform other luxury travel advisors can use. The Wing architecture, Dani engine, dossier system, voice agent, auto-CRM, bulletin engine -- all of it. SaaS pricing. SDVOSB-eligible government contracts for travel management.

**Why not yet:** D2M needs to prove the system at scale first. 20+ active clients, 6+ months of operational data, and a refined onboarding flow. But the architecture is already modular enough to support multi-tenant deployment.

**Watch trigger:** D2M hits 20 active bookings. First advisor asks "what system do you use?"

**Revenue potential:** $500-2,000/month per advisor. 50 advisors = $300K-$1.2M ARR. This changes D2M from a travel agency to a travel technology company.

---

### 7.3 VIDEO TRIP PRESENTATIONS — AI-Generated Destination Films

**What:** Generate 2-3 minute AI video presentations for each proposed trip. Destination footage, property walkthroughs, excursion previews, narrated by Dani's voice. Send before the sales call. Client watches a mini-film of their trip before they even commit.

**Why not yet:** Video generation quality (Veo 3.1, Sora) is improving but not production-luxury-quality yet. Cost per video is still high. By Q4 2026, this should be feasible.

**Watch trigger:** Veo 3.1 or equivalent reaches photorealistic quality at under $5/minute of generated content.

---

### 7.4 PREDICTIVE BOOKING ENGINE — "Commander, the Furlows Will Want This"

**What:** Analyze client travel patterns, preferences, budget cycles, and past behavior to predict what they will want before they ask. "The Furlows traveled Mediterranean in 2024, Scandinavia in 2025. Based on pattern, they'll be interested in Asia or South Pacific for 2027. Regent's new Grand Asia voyage launches next month -- get ahead of it."

**Why not yet:** Needs 12+ months of dossier data and 15+ clients to build meaningful patterns. The auto-CRM (Wave 6.7) and semantic search (Wave 6.1) are prerequisites.

**Watch trigger:** D2M hits 15 clients with 12+ months of interaction history.

---

### 7.5 REAL-TIME DISRUPTION RESPONSE — "Your Flight Changed, Here's the Fix"

**What:** Monitor every booked client's flights, ports, and hotels for disruptions in real time. Flight canceled? Dani already has three alternatives ready and texts the client before they even check their email. Port closure? Alternative excursion options generated automatically. This is concierge service that feels like magic.

**Why not yet:** Needs reliable real-time flight tracking (FlightAware integration exists but is polling-based), weather API wiring, and the multi-channel Dani (Wave 6.4) for instant client notification. Most of the pieces exist in `thunderbird_airline_monitor.py`, `thunderbird_fare_watch.py`, and `thunderbird_followup_reminders.py` -- they just need to be wired into a real-time response pipeline.

**Watch trigger:** Wave 6.4 (multi-channel Dani) and 5.1 (Dani Voice) are both operational.

---

### 7.6 APPLE/SIRI INTELLIGENCE INTEGRATION

**What:** When Apple Intelligence becomes capable (Spring/Summer 2026), clients will ask Siri to interact with services. "Hey Siri, when does my Dreams2Memories trip depart?" The client portal should emit structured data (calendar events, structured itineraries) that Apple Intelligence can consume and present.

**Why not yet:** Apple Intelligence is still rolling out. Siri's capability is uncertain. But the client portal (`portal/server.py`) should be designed with structured data outputs from the start.

**Watch trigger:** Apple Intelligence demonstrates reliable third-party service integration.

---

### 7.7 LOCAL LLM FLEET ON YOGA — Zero-Cost AI Operations

**What:** Deploy Llama 4 Scout, Mistral, and specialized fine-tuned models locally on YOGA for zero-cost bulk operations. Email classification, PDF extraction, fare monitoring, dossier gap detection -- all running locally, all free. Reserve API calls for client-facing quality work only.

**Why not yet:** YOGA hardware needs assessment for local LLM capacity. Llama 4 Scout (17B active params) should run on decent GPU. If YOGA has a capable GPU, this is Wave 6 material. If not, it stays on the horizon until hardware upgrade.

**Watch trigger:** Assess YOGA GPU capability. If adequate, promote to Wave 6.

---

## GAP ANALYSIS: BUILT BUT NOT WIRED

These modules exist in the codebase but are underconnected. Wiring them is often higher ROI than building new features.

| Module | Lines | Status | Wiring Needed |
|--------|-------|--------|---------------|
| `thunderbird_trip_architect.py` | 1,862 | Built, underused | Connect to auto-enrich, pricing, portal (Wave 6.3) |
| `thunderbird_bulletin.py` | 1,042 | Built, not connected | Wire to fare watch, competitive surveillance (Wave 5.6) |
| `thunderbird_dashboard.py` | 984 | Skeleton | Full build needed (Wave 6.6) |
| `thunderbird_overwatch.py` | 1,244 | Built, unclear integration | Assess and wire to monitoring pipeline |
| `thunderbird_concierge_monitor.py` | 1,337 | Built, underused | Connect to multi-channel Dani (Wave 6.4) |
| `thunderbird_audio_briefing.py` | 752 | Built, needs TTS | Wire TTS provider (Wave 5.2) |
| `thunderbird_commission_recon.py` | 856 | Built, manual trigger | Wire to n8n scheduled workflow |
| `thunderbird_switchblade.py` | 785 | Built, purpose unclear | Assess and integrate or deprecate |
| `thunderbird_star_protocol.py` | 868 | Built, manual trigger | Wire to automated quality pipeline |
| `thunderbird_files_api.py` | 378 | Skeleton | Connect to Anthropic Files API (Wave 6) |
| `thunderbird_whatsapp.py` | 44 | Skeleton only | Build out via OpenClaw (Wave 6.4) |
| `thunderbird_autopilot.py` | 215 | Minimal | Assess for automation pipeline integration |
| `thunderbird_survey.py` | 422 | Built, not deployed | Wire to post-trip workflow |
| `thunderbird_followup_reminders.py` | 225 | Built, not connected | Wire to COS daily brief and n8n |

---

## EXTERNAL SIGNUPS REQUIRED

Priority order for the pending signups:

| # | Service | Wave | Cost | Why First |
|---|---------|------|------|-----------|
| 1 | **Retell AI** | 5.1 | $0.07/min | Voice agent is the biggest revenue play |
| 2 | **Firecrawl** | 5.4 | Free (500/mo) | Immediate scraping upgrade, zero risk |
| 3 | **Perplexity API** | 5.3 | TBD | Research force multiplier |
| 4 | **Exa.ai** | 5.3 | TBD | Supplemental research, neural search |
| 5 | **Zep** | 6.2 | $25/mo | Temporal KG after data accumulation |

---

## DEPENDENCIES MAP

```
Wave 5.1 (Dani Voice) ---------> Wave 6.4 (Multi-Channel) ---------> Wave 7.5 (Disruption Response)
Wave 5.2 (Audio Briefings) ----> Wave 6.3 (Trip Architect Pro)
Wave 5.4 (Firecrawl/Aven) ----> Wave 6.3 (Trip Architect Pro) ----> Wave 7.1 (A2A Economy)
Wave 5.6 (Bulletins) ----------> Wave 7.4 (Predictive Booking)
Wave 6.1 (Semantic Search) ----> Wave 7.4 (Predictive Booking)
Wave 6.7 (Auto-CRM) -----------> Wave 7.4 (Predictive Booking)
Wave 6.5 (Grant Compiler) -----> Independent (can start immediately)
Wave 6.6 (Dashboard) ----------> Independent (can start immediately)
```

---

## STRATEGIC ASSESSMENT

The competitive landscape is converging fast. Every major AI company is building multi-agent systems. Every travel company is experimenting with AI. D2M's advantage is that we are already operational -- not experimenting, not piloting, operating. 120+ MCP tools, 8 personas, 16 n8n workflows, client portal, Telegram C2. That is a 6-month lead.

Wave 5 widens the lead by turning the infrastructure into revenue-generating capabilities.
Wave 6 makes the lead permanent by building a data moat that deepens with every client interaction.

The single highest-leverage item across both waves is **6.3 Trip Architect Pro** -- the integration play that wires together trip architect, auto-enrich, real-time pricing, Canva visuals, audio briefings, and portal delivery. It is the full-stack client experience: inquiry to stunning, audio-narrated, visually rich proposal in under an hour. No solo travel advisor on earth can match that speed and quality. That is the kill shot.

The single highest-revenue item is **6.5 Grant Compiler**. A successful SBIR/STTR application at $750K funds the entire operation for two years and validates Thunderbird OS as innovation worth investing in.

The single highest-urgency item is **5.1 Dani Voice Agent**. Every unanswered call is a potential booking walking out the door. This should be the first thing built in Wave 5.

---

*Strategy Paper from Lt Col Ryan "Viper" Castillo, A5 Strategic Planning & Business Growth*
*Dreams2Memories Travel, LLC — Thunderbird OS*
*"Tactics without strategy is noise before defeat."*
