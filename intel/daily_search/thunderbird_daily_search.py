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
        "query": "What MCP servers were released or significantly updated in June 2026? Search glama.ai/mcp/servers (sorted newest), mcpserver.cc, and the official anthropics/modelcontextprotocol GitHub. For each server: name, repository URL, what it does, exact install command (npx/docker/pip), whether an API key is required, GitHub star count, and the workflow problem it solves. Flag any relevant to: web scraping, travel data APIs, browser automation, or document processing. Only list servers with a working install command — skip concept repos or unmaintained projects.",
        "recency": "week",
        "routine_candidate": True,   # prime Routines candidate — new releases weekly
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "McPoogle at mcp.mcpoogle.com/sse is searchable"
    },
    {
        "id": 3,
        "name": "AI Agent Orchestration & Meta-Harnesses",
        "persona": "You are an AI systems architect who has evaluated dozens of multi-agent frameworks. You are skeptical of hype and only recommend tools with production deployments.",
        "query": "What open-source AI agent orchestration frameworks or meta-harnesses were released or significantly updated in 2026? Include: GitHub repo, star count, license, Claude/Anthropic compatibility, and what specific problem it solves beyond LangChain. Focus on: budget enforcement, multi-agent coordination, policy gates, sandbox execution. Omnigent (omnigent-ai/omnigent) and cc-fleet (ethanhq/cc-fleet) are the benchmark — what else exists at this level?",
        "recency": "month",
        "routine_candidate": False,  # evolves slowly; monthly check sufficient
        "haiku_eligible": False,     # needs architecture reasoning
        "cadence": "monthly",
        "notes": "Omnigent 4296 stars, Apache-2.0 — reference point"
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
        "notes": "Spencer group air quote (DEN-FCO 12-pax) is the live use case"
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
        "notes": "35-50% arbitrage documented — confirmed pattern. Need automation."
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
        "notes": "TESS (JWT), Nexion portal, Regent OA portal are our live systems"
    },
    {
        "id": 13,
        "name": "Cruise Line Intelligence",
        "persona": "You are a cruise industry analyst who monitors technology deployments, app updates, and operational changes across luxury cruise lines. You separate marketing from actual technology signals.",
        "query": "What technology updates did Silversea, Regent Seven Seas, Viking Ocean, Princess Cruises, and Atlas Ocean Voyages make in 2025-2026? Check: each cruise line's press room, their Apple App Store and Google Play app listing version history and release notes, their LinkedIn company pages, and travel industry trade press (Travel Weekly, Cruise Industry News, Seatrade Cruise). What are the current app versions and recent update notes? Any AI features, new booking tools, loyalty program changes, advisor portal updates, or backend system migrations? What technology changes directly affect travel advisors who book these lines?",
        "recency": "month",
        "routine_candidate": True,   # prime Routines candidate — weekly cruise line news
        "haiku_eligible": False,     # needs signal vs. noise judgment
        "cadence": "weekly",
        "notes": "Silversea Silver Muse, Regent Grandeur, Viking Mars, Princess Discovery Princess, Atlas Ocean Voyages ships are our active fleet"
    },
    {
        "id": 14,
        "name": "Voyage Feedback & Community Intelligence",
        "persona": "You are a cruise travel researcher who monitors Cruise Critic, Reddit, and Facebook luxury cruise groups daily. You synthesize passenger feedback into actionable intelligence for travel advisors.",
        "query": "What are passengers, travel bloggers, and travel advisor community members saying about recent experiences on Silversea Silver Muse, Regent Seven Seas Seven Seas Grandeur, Viking Ocean Viking Mars, Princess Discovery Princess, and Atlas Ocean Voyages ships in 2025-2026? Search Cruise Critic ship review pages, TripAdvisor cruise reviews, travel blogs, and advisor forum posts. What recurring themes appear in passenger feedback: food quality, service consistency, cabin comfort, embarkation process, excursion quality? What specific complaints or praises appear repeatedly? What are travel advisors warning their clients about on each ship? Give concrete examples from actual reviews, not general summaries.",
        "recency": "month",
        "routine_candidate": True,   # community feedback changes constantly
        "haiku_eligible": False,     # needs pattern recognition + interpretation
        "cadence": "weekly",
        "notes": "McLeod sailed Silver Muse Jun 18. Grandeur group departs Aug 29."
    },
    {
        "id": 15,
        "name": "AI Email Intelligence & Lifecycle Automation",
        "persona": "You are a marketing automation engineer who specializes in AI-native email tools for small luxury service businesses. You know the difference between enterprise CRM and what a 1-person agency can actually use.",
        "query": "What AI-native email automation or lifecycle management tools were released in 2025-2026 that could automate client touchpoint sequences for a small luxury travel business? Include tools with: free tiers or low monthly cost, API access, trigger-based sending (booking milestone, date-based), and the ability to personalize based on client data. Which tools work without a massive contact list? Exclude Salesforce, HubSpot enterprise tier.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": True,
        "cadence": "monthly",
        "notes": "23-touchpoint lifecycle per client — currently manual. Automation is the goal."
    },
    {
        "id": 16,
        "name": "Anthropic API & Claude Agent SDK",
        "persona": "You are a senior Anthropic API developer who tracks every release, changelog, and beta feature. You read the Anthropic GitHub and Discord daily.",
        "query": "What new Claude API features, model releases, SDK updates, or beta capabilities did Anthropic announce or ship in Q1-Q2 2026? Include: claude-agent-sdk (npm @anthropic-ai/claude-agent-sdk) version history, new tool use patterns, extended thinking updates, computer use changes, pricing updates, and any new API endpoints. What is the agent SDK actually designed to replace or improve? Cite GitHub and official Anthropic docs.",
        "recency": "month",
        "routine_candidate": True,   # Anthropic ships constantly — weekly check
        "haiku_eligible": True,
        "cadence": "weekly",
        "notes": "claude-agent-sdk v0.3.185 found today. 223 published versions. May replace headless spawn."
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
        "query": "What AI vision tools or APIs in 2026 can analyze, describe, or search cruise ship photos, port city images, and ship deck plans? Include: tools for auto-captioning images for itinerary use, visual search for ship identification, OCR on deck plan PDFs, and photo quality assessment for marketing materials. What's free or low-cost? Which vision models (Gemini, GPT-4V, Claude) perform best on travel imagery specifically?",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,
        "cadence": "monthly",
        "notes": "Ship photos in Drive for Silver Muse, Nova, Viking Mars, Grandeur. Nobody querying them visually."
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
        "query": "What evidence exists in 2025-2026 that luxury travel agencies are deploying AI in their operations? Search LinkedIn for job postings at Virtuoso agencies, Fora Travel, Indagare, Black Tomato, and Pavlus Travel that mention AI, automation, or machine learning. Check their websites and press rooms for any AI concierge features, chatbots, or automated tools visible to clients or advisors. Search Travel Weekly, Travel + Leisure, Forbes Travel for any interviews with agency executives discussing AI adoption. What are luxury travel conferences (Virtuoso Travel Week, ASTA Global Convention 2025-2026) saying about AI? What specific capabilities are luxury advisors advertising on their websites that suggest AI behind them?",
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
        "query": "What is the developer and AI practitioner community saying in May-June 2026 about which AI tools actually work versus which ones are overhyped? Search for recent blog posts, Hacker News threads, developer newsletter mentions, and community discussions. What specific AI products or frameworks have developers publicly praised as genuinely useful and workflow-changing in 2026? What products have developers publicly criticized as not delivering on their promises? What are the most-discussed tool switches ('I switched from X to Y because...') in the AI development community in 2026? Which categories — agent frameworks, LLM APIs, browser automation, memory systems — have the strongest community consensus right now?",
        "recency": "week",
        "routine_candidate": True,   # discourse is real-time; prime Routines candidate
        "haiku_eligible": False,     # pattern recognition + signal extraction
        "cadence": "weekly",
        "notes": "This is the vaporware detector. 10 items in today's sweep were vaporware — this category prevents that."
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
        "query": "What APIs, databases, or tools in 2026 provide the following assets for luxury travel itinerary production: (1) embeddable or downloadable city/port maps (Google Maps API, Mapbox, OpenStreetMap licensing), (2) licensed port and destination photography (Unsplash API, Pexels, cruise line press kits, Getty travel), (3) cruise ship deck plans and suite diagrams in searchable/embeddable format, (4) pre-written evocative port descriptions or travel writing databases, (5) real-time suite availability and pricing from cruise lines. For each asset type: best source, licensing, cost, and API or download method.",
        "recency": "month",
        "routine_candidate": False,
        "haiku_eligible": False,     # creative + commercial licensing judgment needed
        "cadence": "monthly",
        "notes": "These are Luna and Dani's ingredients. Currently sourced manually every client. Automate the supply chain."
    },
]

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
    cats = CATEGORIES if not category_ids else [c for c in CATEGORIES if c["id"] in category_ids]
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
