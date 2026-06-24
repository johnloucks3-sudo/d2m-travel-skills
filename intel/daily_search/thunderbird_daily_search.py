#!/usr/bin/env python3
"""
Thunderbird Daily Intelligence Search Engine
31 categories · 4 cycles/day · Perplexity API (web search) + Groq (classification)

Commander directive 2026-06-21: daily mass search, compound learning.
"The more we search, the more valuable treasure we find."

Tags per category:
  routine_candidate: True = port to Claude MAX Routines when stable
  haiku_eligible:    True = Haiku can run this; False = needs Sonnet/Opus for analysis
  cadence:           daily | weekly | per_cycle
"""

import os, json, sys, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

# ── Config ────────────────────────────────────────────────────────────────────
PERPLEXITY_KEY = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"          # online search, cheapest tier
INTEL_DIR = Path(__file__).parent
MAX_WORKERS = 8                     # parallel agents (Perplexity rate: 5 req/min free → tune down if needed)
TIMEOUT = 60                        # seconds per search

WAVE = os.getenv("SEARCH_WAVE", "1")
RUN_TS = datetime.now().strftime("%Y-%m-%d_%H%M")
OUTPUT_FILE = INTEL_DIR / f"wave{WAVE}_{RUN_TS}.json"

# ── 31 Categories ─────────────────────────────────────────────────────────────
CATEGORIES = [
    {
        "id": 1,
        "name": "CC Plugin & Marketplace Ecosystem",
        "persona": "You are a senior Claude Code developer who builds and publishes CC plugins. You know the difference between real installable tools and speculative projects.",
        "query": "What Claude Code plugins, skills, and plugin marketplaces exist or were updated in June 2026? List only tools with a working install path (claude plugins install, npm, or git clone). Include: plugin name, marketplace source, what it does, GitHub repo and star count. Exclude anything without a verified install command.",
        "recency": "month",
        "routine_candidate": True,   # weekly sweep of new plugins
        "haiku_eligible": True,      # fetch + classify, no deep synthesis
        "cadence": "weekly",
        "notes": "Use McPoogle / glama.ai as secondary sources"
    },
    {
        "id": 2,
        "name": "MCP Server Registry — New Releases",
        "persona": "You are an AI infrastructure engineer who tracks the Model Context Protocol ecosystem daily. You only report servers with working npm packages or Docker images.",
        "query": "What MCP (Model Context Protocol) servers are documented on docs.anthropic.com or discussed in Claude documentation as officially supported or recommended in 2026? Also: what MCP servers for calendar access, email sending, web search, file systems, or browser control appear in tech articles, blog posts, or tutorials about building Claude agents? For each: name, what it does, install method (npx/docker/pip), whether an API key is required, and any GitHub repo URL or star count mentioned. Include any server with a working install command that appeared in any article or tutorial between January and June 2026. Flag any relevant to: web scraping, travel data APIs, browser automation, or document processing.",
        "recency": "week",
        "routine_candidate": True,   # prime Routines candidate — new releases weekly
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "Winning angle (2026-06-21 dead zone test): ask about documented/published servers, not GitHub trending. filesystem, GitHub, Playwright, Slack confirmed signal.",
    },
    {
        "id": 3,
        "name": "AI Agent Orchestration & Meta-Harnesses",
        "persona": "You are an AI systems architect who has evaluated dozens of multi-agent frameworks. You are skeptical of hype and only recommend tools with production deployments.",
        "query": "What AI agent orchestration frameworks are tech journalists, developer publications, and practitioners reporting as production-ready in 2026? Look for: survey data on which multi-agent frameworks developers are adopting, tech media coverage of frameworks competing with LangGraph, and analyst reports on what's winning for agentic AI workloads. For each framework (OpenAI Agents SDK, Semantic Kernel, Haystack, Mastra, smolagents, Google ADK, CrewAI, Microsoft Agent Framework, Omnigent): what published benchmarks or adoption reports exist, does it natively support Claude, and what problem class does it solve better than LangGraph? What does tech media say practitioners chose when they moved off LangChain/LangGraph for production agent work?",
        "recency": "month",
        "routine_candidate": False,  # evolves slowly; monthly check sufficient
        "haiku_eligible": False,     # needs architecture reasoning
        "cadence": "monthly",
        "notes": "Winning angle (2026-06-21): ask what tech media reports practitioners chose, not GitHub trending. Round 1: OpenAI Agents SDK, Mastra, smolagents confirmed as 2026 LangGraph replacements.",
    },
    {
        "id": 4,
        "name": "Free & High-Quota LLM APIs",
        "persona": "You are an AI cost optimization engineer who runs 10,000+ API calls per day on zero budget. You know every free tier, rate limit, and generous quota in the LLM market.",
        "query": "What LLM APIs offer the most generous free tiers or rate limits as of June 2026? For each: model name, context window, free requests per day, free requests per minute, whether it supports tool use/function calling, and the API endpoint format. Include Groq, Gemini Flash-Lite, Cerebras, Together.ai, Mistral, Cohere, and any new free entrants. Which ones work with a direct HTTP POST and BYOK?",
        "recency": "month",
        "routine_candidate": True,   # free tiers change; monthly audit valuable
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Groq llama-3.1-8b-instant and Gemini Flash-Lite already wired — what's next"
    },
    {
        "id": 5,
        "name": "Agentic Browser Automation",
        "persona": "You are an AI automation engineer who has tried every browser automation tool against enterprise-grade anti-bot systems including Akamai Bot Manager and Cloudflare. You know what works and what doesn't on travel portals.",
        "query": "What AI/LLM-driven browser automation tools exist in 2026 that can navigate complex portals with login walls, dynamic JavaScript, and anti-bot systems? Compare browser-use (99k stars), Playwright MCP, Hyperbrowser, and any 2026 entrants. For each: can it handle Akamai Bot Manager, cost if any, language/runtime, and real user reviews of success on airline or cruise line portals.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,     # needs capability comparison reasoning
        "cadence": "monthly",
        "notes": "Regent portal blocked headless Claude (Akamai). Atlas Ocean Voyages portal also in scope. This is our #1 unsolved problem."
    },
    {
        "id": 6,
        "name": "Anti-Bot Scraping Precision",
        "persona": "You are a web scraping engineer with 10 years experience bypassing enterprise anti-bot systems for the travel industry. You know the difference between tools that claim to work and tools that actually work on cruise line websites.",
        "query": "What commercial scraping API services are available in 2026 for data extraction from JavaScript-heavy and bot-protected websites? Compare Firecrawl, Zyte API (formerly Scrapinghub), ScrapingBee, Oxylabs, Apify, and BrightData. For each: free trial credits, cost per 1000 pages at paid tier, JavaScript rendering quality, ability to handle login-required pages, and real user reviews from Reddit or Stack Overflow about reliability. Which services do travel industry developers actually use for scraping airline, hotel, and cruise websites? What is the community consensus on which one handles enterprise-grade bot protection most reliably in 2026?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Firecrawl trial ready (needs API key from firecrawl.dev). 500 free credits."
    },
    {
        "id": 7,
        "name": "Flight Tech & Booking APIs",
        "persona": "You are a travel technology specialist with deep expertise in air distribution, GDS systems, and the shift to NDC. You advise travel agencies on flight technology.",
        "query": "What APIs, tools, or platforms in 2025-2026 enable flight price search or group booking for travel advisors without full IATA accreditation? Include: ITA Matrix access methods, Duffel API, Kiwi.com for agents, Skiplagged API if any, and NDC direct-connect options. Focus on: group bookings (10+ passengers), consolidated fares, and what's accessible to independent advisors at a host agency. What changed in 2026?",
        "recency": "month",
        "routine_candidate": True,   # NDC/GDS changes frequently
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "Spencer group air quote (DEN-FCO 12-pax) is the live use case",
        "suspended": True,
        "suspended_reason": "REPLACED_BY_MICRO: See categories 40 (group air) and 41 (NDC direct connect).",
    },
    {
        "id": 8,
        "name": "Hotel Tech & Inventory Systems",
        "persona": "You are a hotel distribution technology specialist who advises luxury travel agencies on how to access hotel inventory with commission.",
        "query": "What hotel booking APIs or platforms in 2026 allow independent travel advisors (at host agencies like Nexion or OA) to search and book luxury hotels with commission? Include: Expedia TAAP updates, Booking.com partner changes, SynXis direct connect, and any new luxury hotel API entrants. What's the best technology for sourcing and booking pre/post cruise hotels in European ports? What changed in 2026?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Pre/post cruise hotel for Grandeur group (Amsterdam, Barbados etc.) is live need"
    },
    {
        "id": 9,
        "name": "Ground Transport & Logistics Tech",
        "persona": "You are a destination management technology specialist focused on luxury ground transport for cruise passengers.",
        "query": "What APIs or booking platforms in 2026 handle luxury ground transport for cruise passengers: private car transfers from port to hotel, wheelchair-accessible transport, and cruise terminal logistics? Include Mozio, Get Transfer, Welcome Pickups, Blacklane, and any B2B transport APIs accessible to travel advisors. What's new in 2026? Which platforms work for European cruise ports (Amsterdam, Barcelona, Rome)?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Grandeur group ground transport (Barbados, Baltic ports) is live need"
    },
    {
        "id": 10,
        "name": "Shore Excursion Platforms & APIs",
        "persona": "You are a shore excursion specialist and travel technology analyst who has compared third-party excursion pricing against cruise line pricing across 50+ ports.",
        "query": "What APIs or booking platforms in 2026 allow travel advisors to offer third-party shore excursions at better prices than cruise line excursions? Include: Viator partner API, GetYourGuide affiliate, Withlocals, TourRadar, Bespoke Travel. For each: commission structure, API access requirements, price comparison vs. cruise lines, and which cruise lines still allow independent excursion booking. What's new or changed in 2026?",
        "recency": "month",
        "routine_candidate": True,   # pricing changes frequently
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "35-50% arbitrage documented — confirmed pattern. Need automation.",
        "suspended": True,
        "suspended_reason": "REPLACED_BY_MICRO: See categories 42 (Mediterranean) and 43 (Baltic/Nordic).",
    },
    {
        "id": 11,
        "name": "Land Tour & Package Tech",
        "persona": "You are a FIT and package travel technology specialist focused on custom European and Scandinavian land programs.",
        "query": "What technology platforms or APIs in 2026 enable travel advisors to build and book custom land packages or pre/post-cruise land programs without being a full DMC? Include: TourPlan, TravelgateX, Hotelbeds package tools, and any new FIT booking engines. Focus on: Scandinavian cruisetours, Baltic pre-cruise, and Mediterranean land extensions. What's changed in 2026 that makes this easier or harder?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "McLeod Dec 2026 Baltic cruise — pre/post land options needed"
    },
    {
        "id": 12,
        "name": "Cruise Tech & Booking Systems",
        "persona": "You are a cruise industry technology analyst who covers the booking systems and portal technology used by independent travel advisors at host agencies.",
        "query": "What changes to cruise booking technology or host agency platforms occurred in 2025-2026? Include: Sabre cruise module updates, TESS platform (Travel Edge) changes, Nexion portal updates, Outside Agents portal changes, and any new cruise booking engines or tools for independent advisors. What new technology are the cruise lines deploying that affects travel advisor workflows? Any new API access or partner portal changes?",
        "recency": "month",
        "routine_candidate": True,   # portal changes affect daily ops
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "TESS (JWT), Nexion portal, Regent OA portal are our live systems",
        "suspended": True,
        "suspended_reason": "REPLACED_BY_MICRO: See categories 44 (TESS), 45 (Nexion/OA), 46 (cruise line advisor portals).",
    },
    {
        "id": 13,
        "name": "Cruise Line Intelligence",
        "persona": "You are a cruise industry analyst who monitors technology deployments, app updates, and operational changes across luxury cruise lines. You separate marketing from actual technology signals.",
        "query": "What specific news, announcements, or developments about Silversea Cruises, Regent Seven Seas, Viking Ocean, Princess Cruises, and Atlas Ocean Voyages occurred in 2025-2026 that were covered by cruise industry media or the cruise lines' own press rooms? For each line: include any new ships announced, technology features deployed, fleet updates, partnership or loyalty program changes, advisor program changes, or notable pricing/itinerary news. Also: what are published cruise travel writers, luxury travel columnists, or cruise specialty sites saying in 2025-2026 about these lines' recent changes or new product?",
        "recency": "month",
        "routine_candidate": True,   # prime Routines candidate — weekly cruise line news
        "haiku_eligible": False,     # needs signal vs. noise judgment
        "cadence": "weekly",
        "notes": "Winning angle (2026-06-21): ask what cruise industry media reported, not LinkedIn. Silversea 140-day World Cruise 2026 confirmed signal. Active fleet: Silver Muse, Grandeur, Viking Mars, Discovery Princess, Atlas OA ships.",
    },
    {
        "id": 14,
        "name": "Voyage Feedback & Community Intelligence",
        "persona": "You are a cruise travel researcher who monitors Cruise Critic, Reddit, and Facebook luxury cruise groups daily. You synthesize passenger feedback into actionable intelligence for travel advisors.",
        "query": "What do published travel reviews, travel magazine articles, and cruise specialty websites say about the Silversea Silver Muse, Regent Seven Seas Grandeur, Viking Ocean Viking Mars, Princess Discovery Princess, and Atlas Ocean Voyages ships in 2025-2026? What do professional reviewers and cruise columnists consistently praise or criticize about food quality, service, cabin comfort, shore excursion quality, and value on each ship? Which ship gets higher marks from published reviewers, and are there any specific improvements or declines noted since these ships launched? Include any consumer-grade ratings data (TripAdvisor ship scores, Cruise Critic Overall ratings) where available.",
        "recency": "month",
        "routine_candidate": True,   # community feedback changes constantly
        "haiku_eligible": False,     # needs pattern recognition + interpretation
        "cadence": "weekly",
        "notes": "Winning angle (2026-06-21): ask what published reviews say, not community posts. Confirmed signal: Regent Grandeur edges Silver Muse overall; Silver Muse praised for refined cuisine + intimate feel. McLeod sailed Silver Muse Jun 18. Grandeur group departs Aug 29.",
    },
    {
        "id": 15,
        "name": "AI Email Intelligence & Lifecycle Automation",
        "persona": "You are a marketing automation engineer who specializes in AI-native email tools for small luxury service businesses. You know the difference between enterprise CRM and what a 1-person agency can actually use.",
        "query": "What AI-powered email personalization features did major email marketing platforms add in 2025-2026? Specifically: what did Klaviyo add for AI content generation and personalization? What AI features did Mailchimp/Intuit add? What did Brevo, ActiveCampaign, or Drip add for AI-written email content? For each platform: can you provide a client profile and have it write a personalized email draft (not just subject line suggestions), does it support bring-your-own LLM API key (Claude/OpenAI), what is the free or lowest tier price, and what do published reviews say about quality of AI-written output? Which platforms now let small agencies (1-person, 20-30 clients) generate fully personalized lifecycle emails from client data?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Winning angle (2026-06-21): ask about specific platform features in published reviews. Confirmed: Klaviyo + Brevo furthest ahead on AI content gen; Mailchimp AI = subject lines only. 23-touchpoint lifecycle per client — currently manual.",
    },
    {
        "id": 16,
        "name": "Anthropic API & Claude Agent SDK",
        "persona": "You are a senior Anthropic API developer who tracks every release, changelog, and beta feature. You read the Anthropic GitHub and Discord daily.",
        "query": "What is publicly reported about Anthropic's Claude model releases, API updates, and Agent SDK in tech news, developer blogs, and product announcements in 2025-2026? Include: exact model IDs and version strings mentioned in any published article (e.g. claude-opus-4-8, claude-fable-5, claude-sonnet-4-6), any API pricing changes reported in tech media, new SDK features covered in developer tutorials, extended thinking updates, and any publicly announced new capabilities. What do AI developer publications say is the current recommended Claude model for production agentic workloads as of June 2026? Also: what does tech media report about Anthropic's Agent SDK for programmatic Claude usage?",
        "recency": "month",
        "routine_candidate": True,   # Anthropic ships constantly — weekly check
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "Winning angle (2026-06-21): ask what tech media reports, not Anthropic Discord. CONFIRMED: claude-fable-5 live, claude-opus-4-8, claude-sonnet-4-6 are current model IDs. Agent SDK / subscription pool separation was planned but paused.",
    },
    {
        "id": 17,
        "name": "AI Scheduling & Autonomous Execution",
        "persona": "You are an AI infrastructure engineer who builds autonomous agent systems that run 24/7 without human intervention. You have replaced systemd timers with AI-native scheduling.",
        "query": "What tools or platforms in 2026 enable scheduling and autonomous execution of AI agents on a recurring basis? Include: Claude MAX Routines (cloud), Inngest, Trigger.dev, Modal cron, Temporal workflows, and any new entrants. For each: free tier, whether it natively supports Claude/Anthropic models, latency, and whether it can replace a systemd timer for AI workloads. What's new in 2026 specifically?",
        "recency": "month",
        "routine_candidate": False,  # meta — this category IS about scheduling
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "134 systemd timers in Thunderbird OS. Target: migrate recurring AI tasks to cloud."
    },
    {
        "id": 18,
        "name": "Vector Memory & Cross-Session Persistence",
        "persona": "You are an AI memory systems engineer who has benchmarked every major vector database for production AI agent use. You know the operational reality, not just the benchmarks.",
        "query": "What vector databases or agent memory tools were released or significantly updated in 2026? Compare Qdrant, Weaviate, Chroma, LanceDB, and new entrants on: free self-hosted tier, performance on collections under 100K embeddings, Python client quality, and suitability for cross-session agent memory. Are there any new MCP server integrations for vector memory? What are practitioners on HN and Reddit saying about which one they actually use in production?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Qdrant running in Thunderbird OS. collection: thunderbird_memories."
    },
    {
        "id": 19,
        "name": "LLM Cost Metering & Attribution",
        "persona": "You are an AI cost optimization engineer who tracks every dollar spent on LLM APIs and attributes it to specific tasks, personas, and workflows.",
        "query": "What tools in 2026 enable per-model, per-persona, or per-task cost attribution for Claude and multi-model AI applications? Include: ccusage updates, OpenTelemetry for AI (OTEL metrics), Helicone, LangSmith cost tracking, and any new entrants. For each: does it work with Claude MAX plan, does it support custom tags/attributes per API call, and does it alert on budget cliffs? What's new in 2026?",
        "recency": "month",
        "routine_candidate": True,   # billing changes monthly; monitor ongoing
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "CC OTEL native via OTEL_METRICS_INCLUDE_ENTRYPOINT=true. Need to wire."
    },
    {
        "id": 20,
        "name": "PDF & Document Intelligence",
        "persona": "You are an AI document processing engineer who specializes in extracting structured data from complex travel industry PDFs: cruise brochures, booking confirmations, insurance certificates, and visa forms.",
        "query": "What AI tools in 2026 extract structured data from PDFs for travel use cases? Include: LlamaParse, Unstructured.io, Docling, Marker, and any 2026 entrants. For each: free tier or self-hosted option, accuracy on multi-column PDFs and scanned documents, Python API quality, and speed on a 50-page cruise brochure. What are developers saying actually works vs. what the marketing claims? Include any MCP server integrations.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Cruise brochures, Regent invoices, insurance PDFs — all manual today"
    },
    {
        "id": 21,
        "name": "Multi-Modal Vision Tools",
        "persona": "You are a computer vision engineer specializing in travel media: cruise ship photography, port city imagery, and maritime documentation.",
        "query": "What AI vision tools in 2026 can extract STRUCTURED DATA from cruise ship deck plan PDFs (suite numbers, deck layout, balcony vs. no-balcony classification) and from port city maps (landmark names, walking distances, port gate locations)? Also: which vision model or tool produces the best auto-captions for luxury travel itinerary photos (ship exteriors, port skylines, dining photos)? For each use case: best tool, batch API cost estimate for 50-100 images, and any free or low-cost tier. Which vision model handles fine-grained document layout best: Gemini, GPT-4o, or Claude?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Ship photos in Drive for Silver Muse, Nova, Viking Mars, Grandeur. Nobody querying them visually.",
        "suspended": True,
        "suspended_reason": "REPLACED_BY_MICRO: See categories 37 (deck plan extraction), 38 (photo captions), 39 (port map data).",
    },
    {
        "id": 22,
        "name": "Open-Source LLM Ecosystem",
        "persona": "You are an open-source AI deployment engineer who runs local models on consumer hardware. You know which models actually work and which only look good on benchmarks.",
        "query": "What open-source LLMs released in 2025-2026 run well on 16-32GB RAM consumer hardware and perform at a useful level for text generation, classification, and summarization? Compare: Llama 3.x variants, Mistral/Mixtral updates, Gemma 2, Phi-4, Qwen 2.5, and any 2026 releases. For each: Ollama model name for install, speed on CPU-only (tokens/sec estimate), context length, and honest quality assessment for customer-facing copy generation.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "YOGA (192.168.1.198) has RAM headroom. Local inference untested."
    },
    {
        "id": 23,
        "name": "CLI & Terminal-Native AI Tools",
        "persona": "You are a senior developer with 20 years of Unix experience who lives in the terminal. You only use tools that work without a browser or GUI.",
        "query": "What command-line or terminal-native AI tools were released or significantly updated in 2025-2026? Include tools that: run in bash/zsh, integrate with existing shell workflows, don't require a GUI, and do something useful beyond what Claude Code already does. Examples wanted: shell AI assistants, terminal diff/code tools, CLI documentation generators, command explainers. For each: free tier, install command, and the specific workflow problem it solves.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Claude Code is already the primary. Looking for what extends it."
    },
    {
        "id": 24,
        "name": "AI Security & PII Governance",
        "persona": "You are an AI security engineer and privacy compliance specialist focused on protecting client PII in LLM pipelines. You build guardrails, not just audit them.",
        "query": "What tools in 2026 help prevent client PII from reaching untrusted LLMs in AI pipelines? Include: local PII redaction libraries (Presidio, Scrubadub), API gateway PII filters, prompt injection detectors, and audit trail tools for AI outputs. Focus on tools that work at the code/API level (not enterprise SaaS), have Python bindings, and can redact names, booking references, and payment data before a query reaches an open-source model.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "PII fence doctrine: OpenCode/DeepSeek never receives client PII. Need mechanical enforcement."
    },
    {
        "id": 25,
        "name": "Competitive Intelligence: AI in Travel",
        "persona": "You are a travel industry analyst who tracks how luxury travel agencies and cruise specialists are deploying AI in their client-facing and back-office operations.",
        "query": "What CONCRETE evidence exists that luxury travel agencies have deployed AI in 2025-2026 — not intention-to-deploy, but live tools? Find: specific tool names mentioned in advisor job postings at Virtuoso/Fora/Indagare/Black Tomato/Pavlus, advisor testimonials naming specific AI products they use, startup funding announcements for AI-in-luxury-travel, conference session recordings where advisors name their stack. Are Fora or Indagare ahead of us? What specific capability would a client notice? Rate our position: leading, at-par, or behind.",
        "recency": "month",
        "routine_candidate": True,   # competitive landscape shifts monthly
        "haiku_eligible": False,     # strategic interpretation needed
        "cadence": "monthly",
        "notes": "D2M differentiator is AI-assisted depth. Need to know what competitors are actually doing."
    },
    {
        "id": 26,
        "name": "GitHub Automation for AI Workflows",
        "persona": "You are a DevOps engineer specializing in CI/CD for AI-generated code. You have automated the testing of LLM outputs and prompt regression pipelines.",
        "query": "What GitHub Actions, tools, or CI/CD patterns in 2026 are specifically designed for AI development workflows? Include: automated testing of LLM outputs (does the prompt still produce the right result?), prompt regression testing on model updates, AI dependency currency tools (like Renovate but for model versions), and deployment patterns for AI-heavy apps. What's new in 2026 beyond what Renovate already handles?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Renovate installed today. CI registry in config/ci_registry.json."
    },
    {
        "id": 27,
        "name": "Voice & Conversational Client Interfaces",
        "persona": "You are a conversational AI engineer who has deployed voice agents for small service businesses. You know the real cost and quality of every voice AI platform.",
        "query": "What voice AI or conversational interface tools in 2026 could enable a 1-person luxury travel agency to handle client inquiries by phone or offer a voice booking assistant? Include: VAPI, Retell AI, ElevenLabs Conversational AI, Twilio AI, Bland AI, and 2026 entrants. For each: free tier minutes, voice quality rating from real users, whether it can be customized with business knowledge (RAG), cost per minute at low volume (<100 calls/month), and setup complexity for a non-engineer.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Phone: 719-291-0742. Clients call. Voice AI could extend coverage."
    },
    {
        "id": 28,
        "name": "Owner/User Training — AI for Small Business",
        "persona": "You are an AI education specialist who creates training for non-technical small business owners learning to use Claude, AI agents, and automation tools. You know what actually works for solo operators, not developers.",
        "query": "What AI learning resources, courses, tutorials, or communities in 2025-2026 are specifically designed for small business owners (not developers) learning to use Claude Code, Claude Projects, AI agents, and automation for their business? Include: free courses, YouTube channels, practical newsletters, Discord communities, and hands-on guides. Which ones have real business owner testimonials, not just developer reviews? What is the consensus on the fastest path from zero to productive?",
        "recency": "month",
        "routine_candidate": True,   # new resources constantly; earmark as Haiku weekly scan
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "Commander is the owner/user. Training resources that match his profile matter."
    },
    {
        "id": 29,
        "name": "Human Assessment & Tech Discourse",
        "persona": "You are an early AI adopter who has been burned by vaporware and now only trusts community consensus. You read Reddit, Hacker News, X/Twitter, and Discord every day for 'this sucks' and 'changed my stack' signal.",
        "query": "What do developer surveys, NPS studies, and tech publications report about AI tool adoption and switching patterns in 2025-2026? Include: any published NPS scores for coding assistants (GitHub Copilot vs Cursor vs Claude Code vs Continue.dev), survey data on which AI frameworks developers are adopting or abandoning, tech journalism covering 'tool X losing market share to Y', and analyst reports on which LLM orchestration or vector DB tools are winning in new production deployments. Specifically: what do published surveys say about why developers left LangChain, what won browser automation mindshare, and which vector DB is reported as the choice for greenfield 2026 projects? Include any JetBrains, Stack Overflow, or similar annual survey data on AI tool preference.",
        "recency": "week",
        "routine_candidate": True,   # discourse is real-time; prime Routines candidate
        "haiku_eligible": False,     # pattern recognition + signal extraction
        "cadence": "weekly",
        "notes": "Winning angle (2026-06-21): survey data + tech journalism, not Reddit posts. CONFIRMED: JetBrains survey Claude Code NPS 54 vs Copilot NPS 11 vs Cursor NPS 34. LangChain losing production agent work to OpenAI Agents SDK, Mastra, smolagents.",
    },
    {
        "id": 30,
        "name": "Owner/User Training — AI Workflow Mastery",
        "persona": "You are a productivity coach specializing in AI workflow mastery for executives and business owners who want to lead AI adoption in their business, not just delegate it.",
        "query": "What practical guides, frameworks, or communities in 2025-2026 teach business owners how to direct AI agents, write effective prompts, and integrate AI tools into daily operations without depending on a developer? Include: prompt engineering for business owners, AI delegation frameworks, resources on Claude Code for non-technical founders, and any case studies of 1-2 person businesses successfully running AI-heavy operations. What's the most cited resource for going from 'I use ChatGPT occasionally' to 'I run an AI-powered business'?",
        "recency": "month",
        "routine_candidate": True,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "Different angle from #28 — this one is about mastery and leadership, not onboarding"
    },
    {
        "id": 31,
        "name": "Client Product Asset Pipeline",
        "persona": "You are a luxury travel content specialist who sources every ingredient that goes into a premium client itinerary: maps, photography, descriptive copy, ship schematics, and real-time availability data.",
        "query": "What are the legally-clean sourcing strategies for these five itinerary asset types in 2026: (1) Port/city maps — Mapbox vs. Google Maps Static API embed cost comparison; OpenStreetMap self-hosted option; (2) Destination photography — does Getty Images have a media-kit tier for small agencies; what Creative Commons sources have cruise-quality imagery; do Regent/Silversea/Viking press kits allow advisor reuse; (3) Deck plans — where do cruise lines publish deck plans publicly (PDF or interactive); any third-party aggregator; (4) Port narratives — any licensable travel writing databases or CC0 sources; (5) Suite pricing — does Regent, Silversea, or Viking expose a pricing API, or is Centrav the only B2B path? Include specific license terms and cost for each.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,     # creative + commercial licensing judgment needed
        "cadence": "monthly",
        "notes": "These are Luna and Dani's ingredients. Currently sourced manually every client. Automate the supply chain.",
        "suspended": True,
        "suspended_reason": "REPLACED_BY_MICRO: See categories 32-36 (maps, photography, deck plans, narratives, suite pricing).",
    },

    # ── MICRO-CATEGORIES: Precision slices added 2026-06-21 (ELON + Whetstone) ──────
    # Parent categories #7, #10, #12, #21, #31 suspended in favor of these.
    # "Assembled virtually" = ELON synthesizes related slices in inter-wave analysis.

    # ── #31 SLICE: Client Product Asset Pipeline → 5 targeted micro-categories ──
    {
        "id": 32,
        "name": "Port Maps — Mapbox vs Google vs OSM (2026 Pricing & License)",
        "persona": "You are a developer evaluating map API costs for embedding port city maps in luxury client PDF itineraries. You need exact 2026 pricing, license restrictions, and the cheapest production path.",
        "query": "Compare Mapbox Static Images API vs Google Maps Static API vs self-hosted OpenStreetMap/MapLibre for embedding port city maps in client-facing PDF itineraries in 2026. For each: exact price per 1,000 map renders, whether commercial use in client PDFs is permitted, whether a static PNG can be generated server-side without a browser, attribution requirements, and minimum monthly cost. Which is cheapest for ~200 client maps/month? What are the API call formats?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #31. Wave 8 confirmed Mapbox ~$2.50/1K vs Google ~$7/1K — get exact 2026 pricing + license specifics.",
    },
    {
        "id": 33,
        "name": "Cruise Destination Photography — Legal Sources & License 2026",
        "persona": "You are a content licensing specialist for luxury travel agencies. You know the exact difference between 'can view' and 'can commercially reuse' for every image source.",
        "query": "What are the legally clean sources for cruise destination photos usable in commercial client itineraries in 2026? For each source: exact license terms for commercial reuse in client PDFs, whether attribution is required, and cost. Specifically: (1) Does Getty Images have any small-agency licensing tier? (2) Do Unsplash API and Pexels terms permit commercial client itinerary use? (3) Do Regent Seven Seas, Silversea, Viking Ocean, and Princess Cruises press kits explicitly permit advisor commercial reuse? What do luxury travel agencies actually use for destination imagery?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #31. Wave 8 flagged uncertainty about press kit reuse rights and Getty small-agency tiers.",
    },
    {
        "id": 34,
        "name": "Cruise Ship Deck Plans — Where Lines Publish Them & Reuse Rights 2026",
        "persona": "You are a cruise industry content researcher who knows exactly where Silversea, Regent, Viking, and Princess publish their deck plans and what you can legally do with them.",
        "query": "Where do Silversea, Regent Seven Seas, Viking Ocean, and Princess Cruises publish their cruise ship deck plans in 2026? For each cruise line: the URL or page, format (interactive web vs downloadable PDF vs image file), whether plans show suite categories and balcony/no-balcony designations, and what the terms say about reproducing plans in client-facing itineraries. Are there third-party aggregators (CruiseMapper, CruiseLine.com, others) with downloadable deck plan formats? What are their usage terms?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #31. Need specific deck plan sources for itinerary production automation (MISSION-330).",
    },
    {
        "id": 35,
        "name": "Port Narrative Databases & Travel Writing Licenses 2026",
        "persona": "You are a travel content director who sources licensed port descriptions for luxury travel agencies. You know every database and syndication service that exists for this.",
        "query": "What databases or services in 2026 provide licensable port city and cruise destination narrative content for use in travel agency client itineraries? Include: Lonely Planet content licensing, travel writing syndication services, CC0 or public-domain travel content archives, any services designed for travel agencies. What do luxury travel agencies actually use for port copy — license, commission original writing, or use AI? What's the cost for ~50 port descriptions/year? Any API or bulk download access?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #31. Wave 8 found no specific licensable database — deeper search needed.",
    },
    {
        "id": 36,
        "name": "Cruise Suite Pricing Access — Advisor Channels 2026 (Regent/Silversea/Viking)",
        "persona": "You are an independent travel advisor at a host agency who needs the fastest path to accurate Regent, Silversea, and Viking suite pricing. You have tried every channel.",
        "query": "How do independent travel advisors at host agencies access real-time Regent Seven Seas, Silversea, and Viking Ocean cruise suite pricing and availability in 2026? For each line: which channel gives the most current pricing — the line's own advisor portal, a host agency portal (Nexion, Outside Agents), a consolidator (Centrav), GDS, or phone? Is there any data feed, pricing API, or automated pull available? What changed in 2025-2026 about how these three lines distribute pricing to advisors? What do experienced Regent/Silversea/Viking advisors recommend?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #31. Wave 8: no public API confirmed. Need full advisor channel landscape.",
    },

    # ── #21 SLICE: Multi-Modal Vision → 3 use-case micro-categories ──
    {
        "id": 37,
        "name": "Gemini 2.5 Pro — Deck Plan PDF Structured Extraction (Prompts & Workflow)",
        "persona": "You are a developer who has built cruise ship deck plan extraction pipelines using Gemini 2.5 Pro. You know the exact prompts, pre-processing steps, and failure modes.",
        "query": "What is the best 2026 workflow for extracting structured JSON data from cruise ship deck plan PDFs using Gemini 2.5 Pro? Specifically: (1) what prompt structure produces clean JSON with suite_number, deck_number, balcony_type, cabin_category, location_on_deck fields? (2) Does pre-converting PDF pages to high-res PNG images before sending to Gemini improve accuracy? (3) What are the common failure modes on multi-page deck plans with diagrams and legends? (4) Any GitHub repos or blog posts showing this workflow? (5) What does a Gemini API call cost for a 20-page deck plan PDF?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #21. MISSION-330 is building this. Wave 8 confirmed Gemini 2.5 Pro is best model for deck plan extraction.",
    },
    {
        "id": 38,
        "name": "GPT-4o Luxury Travel Photo Auto-Captioning — Batch Workflow 2026",
        "persona": "You are a developer who has built batch photo captioning pipelines for luxury travel agencies using GPT-4o. You know the exact system prompts, batch API options, and cost structure.",
        "query": "What is the best 2026 workflow for batch auto-captioning 50-100 luxury cruise travel photos using GPT-4o? Specifically: (1) what system prompt produces one-sentence captions in 'luxury travel magazine' tone for ship exteriors, port skylines, and dining scenes? (2) Is GPT-4o Batch API meaningfully cheaper than real-time for this volume? (3) What is the actual cost per image at current 2026 pricing? (4) Is Gemini Flash a viable lower-cost alternative for captioning quality? (5) Any working GitHub repos showing a travel photo captioning pipeline?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #21. Wave 8 confirmed GPT-4o best for luxury photo captions. Need implementation details for MISSION-330 adjacent work.",
    },
    {
        "id": 39,
        "name": "Port City Map Data Extraction — Landmarks & Distances (AI vs API)",
        "persona": "You are a developer building an automated port guide system for a luxury cruise travel agency. You have compared AI vision approaches against API-based approaches for extracting port data.",
        "query": "What is the best 2026 approach for extracting structured port city data (landmark names, port gate/pier locations, walking distances to key sites, neighborhood names) for cruise itinerary port guides? Compare: (1) Gemini 2.5 Pro reading a map image — accuracy and cost for 20 ports/year, (2) Google Maps Places API + Geocoding API — cost and data completeness for cruise ports, (3) OpenStreetMap Overpass API — how to query for cruise port landmarks specifically. Which gives the best accuracy-to-cost ratio for a workflow processing 20-30 unique cruise ports per year? Any working examples?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #21. Port data needed for automated port guide sections in client itineraries.",
    },

    # ── #7 SLICE: Flight Tech → 2 mission-specific micro-categories ──
    {
        "id": 40,
        "name": "Group Air Booking for Travel Advisors — 10-20 Passengers 2026",
        "persona": "You are a travel advisor who specializes in group air bookings for luxury cruise passengers. You know the group desk process at every major US carrier and what changed in 2026.",
        "query": "How does the group air booking process work for independent travel advisors in 2026 for groups of 10-20 passengers? Include: which US carriers have dedicated group desks and their phone numbers (United group desk 800-426-1122, Delta, American, etc.), minimum passenger count for group pricing, how far in advance to request a quote, whether written quotes are binding, whether host agency membership (Nexion, Outside Agents) suffices without IATA credentials, typical discount vs retail pricing, and what changed in 2025-2026. Any new platforms or tools that simplify group air quoting?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #7. Spencer DEN-FCO 12-pax is the live use case (MISSION-196A). Commander calls United group desk — need full process brief.",
    },
    {
        "id": 41,
        "name": "NDC Direct Connect for Independent Travel Advisors 2026",
        "persona": "You are a travel advisor at a host agency who has thoroughly evaluated NDC direct connect options and knows what actually works vs. what is still theoretical.",
        "query": "What NDC (New Distribution Capability) direct connect options are realistically available to independent travel advisors at host agencies like Nexion, Outside Agents, or Travel Edge in 2026? Which airlines offer advisor-direct NDC access? Is pricing or availability actually meaningfully better than GDS in 2026 — what are advisors reporting? What platforms (Duffel, Kiwi, Spotnana, Internova) aggregate NDC for advisors? What are the main workflow friction points vs. traditional GDS? What changed in 2026?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #7. Evaluating flight booking options for advisor efficiency beyond direct group desk calls.",
    },

    # ── #10 SLICE: Shore Excursions → 2 active-itinerary micro-categories ──
    {
        "id": 42,
        "name": "Mediterranean Shore Excursions — Regent Grandeur Aug 2026 Ports",
        "persona": "You are a shore excursion specialist for luxury Regent Seven Seas passengers who knows every third-party operator in Mediterranean cruise ports and where the real value is.",
        "query": "What are the best third-party shore excursion options for Regent Seven Seas Grandeur passengers in Mediterranean summer 2026 ports? Compare Viator, GetYourGuide, and Withlocals for key Mediterranean cruise ports (Barcelona, Lisbon, Civitavecchia/Rome, Piraeus/Athens, Valletta/Malta, Dubrovnik). For each port: are third-party tours meaningfully cheaper than Regent's included excursions? Which excursion categories (private cars, small-group food tours, walking tours) offer best value? Do advisors earn commission from Viator or GetYourGuide bookings? Are there any Regent-specific restrictions on independent excursions in these ports?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #10. Grandeur group (Furlow, Ely-Darrow, Nichols) departs Aug 29. Port intelligence for client briefing.",
    },
    {
        "id": 43,
        "name": "Baltic & Nordic Shore Excursions — Viking Mars Dec 2026 Ports",
        "persona": "You are a shore excursion specialist for Viking Ocean passengers in Baltic and Nordic ports who knows exactly where independent excursions beat the ship's offerings.",
        "query": "What third-party shore excursion options are available in Baltic and Nordic cruise ports for Viking Ocean passengers in late 2026? Cover: Copenhagen, Stockholm, Helsinki, Tallinn, Gdansk/Gdynia, and Oslo. For each port: best Viator/GetYourGuide options vs Viking-included excursions with price comparison, whether independent exploration is safe and viable for luxury passengers, and what Viking passengers specifically say about ship vs independent in these ports. Any advisor commissions from third-party bookings? What's new or changed in 2026 for Baltic cruise port access?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #10. Kuklinski group (Viking Mars Dec 17) needs Baltic port intelligence.",
    },

    # ── #12 SLICE: Cruise Tech → 3 platform-specific micro-categories ──
    {
        "id": 44,
        "name": "TESS / Travel Edge Booking Platform — 2026 Updates & Advisor Feedback",
        "persona": "You are a travel advisor who uses TESS (Travel Edge booking system) as your primary booking platform and follows every update closely through advisor communities.",
        "query": "What new features, updates, or changes did Travel Edge's TESS booking platform release in 2025-2026? Include: new booking workflow features, reporting tool improvements, commission tracking changes, cruise line portal integration updates, and any known bugs or workarounds. What are Nexion and Travel Edge advisors saying about TESS in advisor forums, Facebook groups, or ASTA/CLIA communities? Is there an API or integration capability in TESS for external tools?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #12. TESS is primary booking system with JWT integration. Need platform intelligence.",
    },
    {
        "id": 45,
        "name": "Nexion & Outside Agents — Advisor Portal & Tools 2026",
        "persona": "You are an independent travel advisor who holds memberships with both Nexion and Outside Agents and monitors every host agency platform update for productivity tools.",
        "query": "What new tools, portal features, reports, or programs did Nexion and Outside Agents add for their independent travel advisors in 2025-2026? Include: commission tracking improvements, new booking tools, training resources, preferred supplier program changes, co-op marketing tools, and technology partnerships. What are advisors in the Nexion and Outside Agents communities saying — what's most useful, what's broken, what they wish existed? Any new AI tools either host agency is piloting?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #12. D2M has both Nexion (Regent/Princess) and Outside Agents (Silversea/Viking) relationships.",
    },
    {
        "id": 46,
        "name": "Regent, Silversea & Viking — Advisor-Facing Portal & Commission Changes 2026",
        "persona": "You are a luxury cruise specialist who books Regent Seven Seas, Silversea, and Viking Ocean heavily and monitors every advisor-facing portal and commission change at these lines.",
        "query": "What changed in the advisor-facing portals, commission structures, booking tools, or marketing programs for Regent Seven Seas, Silversea, and Viking Ocean in 2025-2026? For each cruise line: new portal UI or booking features, commission tier changes or overrides, preferred advisor status requirements, group booking tool updates, co-op marketing or FAM trip programs, and what experienced advisors in these lines are saying in advisor communities. Any technology changes these lines made specifically to improve advisor workflow in 2025-2026?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Slice of #12. All three are active booking lines. Commission and portal intelligence direct P0 value.",
    },
]

# ── Inter-wave override (written by inter_wave_analyst.py between waves) ──────
_OVERRIDE = INTEL_DIR / "categories_live.json"
if _OVERRIDE.exists():
    try:
        CATEGORIES = json.loads(_OVERRIDE.read_text())
        print(f"  [analyst] Loaded {len(CATEGORIES)} evolved categories from categories_live.json", flush=True)
    except Exception as _e:
        print(f"  [analyst] Override load failed ({_e}), using base categories", flush=True)

# ── Routines & Haiku Summary (earmarked per Commander directive 2026-06-21) ──
ROUTINE_CANDIDATES = [c["id"] for c in CATEGORIES if c.get("routine_candidate")]
HAIKU_ELIGIBLE    = [c["id"] for c in CATEGORIES if c.get("haiku_eligible")]

# ── Search Engine ─────────────────────────────────────────────────────────────
def search_category(cat: dict) -> dict:
    cat_id   = cat["id"]
    cat_name = cat["name"]
    print(f"\n  [{cat_id:02d}] ▶ SEARCHING: {cat_name}", flush=True)

    if not PERPLEXITY_KEY:
        return {"id": cat_id, "name": cat_name, "error": "PERPLEXITY_API_KEY not set", "result": None}

    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {"role": "system", "content": cat["persona"]},
            {"role": "user",   "content": cat["query"]},
        ],
        "search_recency_filter": cat.get("recency", "month"),
        "return_citations": True,
        "max_tokens": 1500,
    }

    try:
        t0 = time.time()
        resp = requests.post(
            PERPLEXITY_URL,
            headers={"Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
        elapsed = round(time.time() - t0, 1)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        print(f"  [{cat_id:02d}] ✅ COMPLETE ({elapsed}s) — {len(citations)} citations", flush=True)
        # Print first 300 chars as preview
        preview = content[:300].replace("\n", " ")
        print(f"  [{cat_id:02d}]    Preview: {preview}...", flush=True)
        return {
            "id": cat_id,
            "name": cat_name,
            "result": content,
            "citations": citations,
            "elapsed_s": elapsed,
            "error": None,
            "routine_candidate": cat.get("routine_candidate", False),
            "haiku_eligible": cat.get("haiku_eligible", False),
            "cadence": cat.get("cadence", "monthly"),
            "notes": cat.get("notes", ""),
        }
    except Exception as exc:
        print(f"  [{cat_id:02d}] ❌ ERROR: {exc}", flush=True)
        return {"id": cat_id, "name": cat_name, "error": str(exc), "result": None}


def run_wave(category_ids: list = None) -> list:
    if category_ids:
        cats = [c for c in CATEGORIES if c["id"] in category_ids]
    else:
        cats = [c for c in CATEGORIES if not c.get("suspended")]
    results = [None] * len(cats)

    print(f"\n{'='*70}")
    print(f"  THUNDERBIRD DAILY INTELLIGENCE — WAVE {WAVE}")
    print(f"  {RUN_TS} MT · {len(cats)} categories · {MAX_WORKERS} parallel agents")
    print(f"  Routine candidates: {ROUTINE_CANDIDATES}")
    print(f"  Haiku-eligible:     {HAIKU_ELIGIBLE}")
    print(f"{'='*70}\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(search_category, cat): i for i, cat in enumerate(cats)}
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    # Sort by id for clean output
    results = sorted([r for r in results if r], key=lambda x: x["id"])

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "wave": WAVE,
            "run_ts": RUN_TS,
            "total_categories": len(results),
            "routine_candidates": ROUTINE_CANDIDATES,
            "haiku_eligible": HAIKU_ELIGIBLE,
            "results": results,
        }, f, indent=2)

    success = sum(1 for r in results if r.get("result"))
    errors  = sum(1 for r in results if r.get("error"))
    print(f"\n{'='*70}")
    print(f"  WAVE {WAVE} COMPLETE — {success} hits · {errors} errors")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"{'='*70}\n")
    return results


if __name__ == "__main__":
    # Optional: pass category IDs as args to run a subset
    ids = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None
    run_wave(ids)
