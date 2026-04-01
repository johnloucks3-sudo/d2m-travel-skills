"""
api_registry.py — Thunderbird OS API Registry
==============================================
Single source of truth for all available APIs.
Goose and Hale can task any API directly via the dispatcher schema.

Task schema for direct API calls:
{
    "content": "search for Silversea cruises departing Miami",
    "assigned_to": "api",
    "task_type": "api_call",
    "api_target": "amadeus",        ← key from this registry
    "api_method": "search_flights",  ← method hint for the agent
    "api_params": "{...}"            ← optional JSON params
}
"""

# ── Registry ──────────────────────────────────────────────────────────────────
# Each entry: name → {category, env_key, base_url, cost_tier, notes, mcp_tool}

APIS = {

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    "anthropic": {
        "category":  "llm",
        "label":     "Anthropic Claude API",
        "env_key":   "ANTHROPIC_API_KEY",
        "base_url":  "https://api.anthropic.com",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "Full Claude API. Use Max OAuth ($0) for agent tasks; reserve API key for programmatic calls.",
        "mcp_tool":  None,
    },
    "openai": {
        "category":  "llm",
        "label":     "OpenAI GPT",
        "env_key":   "OPENAI_API_KEY",
        "base_url":  "https://api.openai.com",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "GPT-4o, GPT-4-turbo, DALL-E, Whisper. Use for image generation or when Claude unavailable.",
        "mcp_tool":  None,
    },
    "gemini": {
        "category":  "llm",
        "label":     "Google Gemini API",
        "env_key":   "GEMINI_API_KEY",
        "base_url":  "https://generativelanguage.googleapis.com",
        "cost_tier": "free_tier",
        "agent":     "goose",
        "notes":     "Gemini 2.5 Flash = free tier. Default Goose model. 1M context. Excellent for intel/research.",
        "mcp_tool":  None,
    },
    "groq": {
        "category":  "llm",
        "label":     "Groq Inference API",
        "env_key":   "GROQ_API_KEY",
        "base_url":  "https://api.groq.com",
        "cost_tier": "free_tier",
        "agent":     "goose",
        "notes":     "Ultra-fast LLaMA/Mixtral inference. Free. Use for classification, summarization, routing.",
        "mcp_tool":  "groq_gmail_query",
    },
    "deepseek": {
        "category":  "llm",
        "label":     "DeepSeek",
        "env_key":   "DEEPSEEK_API_KEY",
        "base_url":  "https://api.deepseek.com",
        "cost_tier": "cheap",
        "agent":     "auto",
        "notes":     "Standing arbitrator (SO). Use for second opinions on complex decisions. Very cheap.",
        "mcp_tool":  None,
    },
    "poe": {
        "category":  "llm",
        "label":     "Poe Multi-Model API",
        "env_key":   "POE_API_KEY",
        "base_url":  "https://api.poe.com",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "Access to Claude, GPT-4, Gemini via Poe. Overflow bucket when Claude Max saturated.",
        "mcp_tool":  None,
    },
    "anythingllm": {
        "category":  "llm",
        "label":     "AnythingLLM (Local)",
        "env_key":   "ANYTHINGLLM_API_KEY",
        "base_url":  "http://localhost:3001",
        "cost_tier": "free",
        "agent":     "auto",
        "notes":     "Local RAG + LLM. $0 always. Use for document ingestion and offline queries.",
        "mcp_tool":  None,
    },

    # ── Search & Data ─────────────────────────────────────────────────────────
    "serper": {
        "category":  "search",
        "label":     "Serper Google Search",
        "env_key":   "SERPER_API_KEY",
        "base_url":  "https://google.serper.dev",
        "cost_tier": "cheap",
        "agent":     "goose",
        "notes":     "Real-time Google search results. ~$0.001/query. Primary web search for intel.",
        "mcp_tool":  None,
    },
    "gcp_search": {
        "category":  "search",
        "label":     "GCP Custom Search",
        "env_key":   "GOOGLE_API_KEY",
        "base_url":  "https://customsearch.googleapis.com",
        "cost_tier": "free_tier",
        "agent":     "goose",
        "notes":     "100 free searches/day. D2M-tuned index.",
        "mcp_tool":  None,
    },
    "pinecone": {
        "category":  "vector_db",
        "label":     "Pinecone Vector DB",
        "env_key":   "PINECONE_API_KEY",
        "base_url":  "https://thunderbird-260220-7xttuu4.svc.aped-4627-b74a.pinecone.io",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "Semantic memory for Thunderbird namespace. Use for similarity search across D2M knowledge.",
        "mcp_tool":  None,
    },
    "x_twitter": {
        "category":  "social_intel",
        "label":     "X / Twitter API",
        "env_key":   "X_BEARER_TOKEN",
        "base_url":  "https://api.twitter.com/2",
        "cost_tier": "paid",
        "agent":     "goose",
        "notes":     "OSINT feed. Cruise industry news, competitor monitoring, travel trends.",
        "mcp_tool":  "scrape_x_osint_feed",
    },
    "apify": {
        "category":  "scraping",
        "label":     "Apify Web Scraper",
        "env_key":   "APIFY_API_TOKEN",
        "base_url":  "https://api.apify.com",
        "cost_tier": "paid",
        "agent":     "goose",
        "notes":     "Full web scraping. Use for competitor pricing, tour content, cruise line pages.",
        "mcp_tool":  "scrape_consumer_tour_prices",
    },

    # ── Automation ────────────────────────────────────────────────────────────
    "n8n": {
        "category":  "automation",
        "label":     "n8n Workflow Automation",
        "env_key":   "N8N_API_KEY",
        "base_url":  "http://10.0.0.53:5678",
        "cost_tier": "free",
        "agent":     "goose",
        "notes":     "24 workflows live. MCP server at /mcp. Trigger workflows via REST or MCP. Local only (LAN).",
        "mcp_tool":  None,
        "mcp_url":   "http://10.0.0.53:5678/mcp",
    },
    "zapier": {
        "category":  "automation",
        "label":     "Zapier",
        "env_key":   "ZAPIER_API_KEY",
        "base_url":  "https://api.zapier.com",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "External automation bridge. Use when n8n can't reach external services.",
        "mcp_tool":  None,
    },
    "calendly": {
        "category":  "scheduling",
        "label":     "Calendly",
        "env_key":   "CALENDLY_API_KEY",
        "base_url":  "https://api.calendly.com",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "Client scheduling links. Auto-populate guest profile intake forms.",
        "mcp_tool":  None,
    },
    "signwell": {
        "category":  "documents",
        "label":     "SignWell E-Signatures",
        "env_key":   "SIGNWELL_API_KEY",
        "base_url":  "https://www.signwell.com/api/v1",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "Client contract e-signatures. Use for booking agreements and proposals.",
        "mcp_tool":  None,
    },

    # ── Travel / Booking ──────────────────────────────────────────────────────
    "amadeus": {
        "category":  "travel",
        "label":     "Amadeus Flight & Hotel API",
        "env_key":   "AMADEUS_API_KEY",
        "base_url":  "https://api.amadeus.com",
        "cost_tier": "paid",
        "agent":     "hale",
        "notes":     "GDS flight search, hotel rates, seat maps. Primary flight search engine.",
        "mcp_tool":  "search_flights",
    },
    "hotelbeds": {
        "category":  "travel",
        "label":     "Hotelbeds / TAAP",
        "env_key":   "HOTELBEDS_API_KEY",
        "base_url":  "https://api.test.hotelbeds.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "25% markup model. 180K+ hotels. Primary hotel booking engine.",
        "mcp_tool":  "get_taap_hotel_rates",
    },
    "expedia": {
        "category":  "travel",
        "label":     "Expedia Partner API",
        "env_key":   "EXPEDIA_API_KEY",
        "base_url":  "https://api.expediagroup.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "Expedia affiliate rates. Backup when Hotelbeds unavailable.",
        "mcp_tool":  None,
    },
    "viator": {
        "category":  "travel",
        "label":     "Viator Excursions",
        "env_key":   "VIATOR_API_KEY",
        "base_url":  "https://api.viator.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "300K+ tours and activities. 8% agent commission. Primary excursion search.",
        "mcp_tool":  "search_viator_excursions",
    },
    "getyourguide": {
        "category":  "travel",
        "label":     "GetYourGuide",
        "env_key":   "GETYOURGUIDE_API_KEY",
        "base_url":  "https://api.getyourguide.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "Alternative excursion source. Good coverage in Europe.",
        "mcp_tool":  "search_getyourguide_excursions",
    },
    "blacklane": {
        "category":  "travel",
        "label":     "Blacklane Transfers",
        "env_key":   "BLACKLANE_API_KEY",
        "base_url":  "https://api.blacklane.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "Premium airport/city transfers. Primary luxury ground transport.",
        "mcp_tool":  "search_blacklane_transfers",
    },
    "mozio": {
        "category":  "travel",
        "label":     "Mozio Transfers",
        "env_key":   "MOZIO_API_KEY",
        "base_url":  "https://api.mozio.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "Budget/mid-tier transfers. Backup when Blacklane unavailable.",
        "mcp_tool":  "search_mozio_transfers",
    },
    "welcome_pickups": {
        "category":  "travel",
        "label":     "Welcome Pickups",
        "env_key":   "WELCOME_PICKUPS_API_KEY",
        "base_url":  "https://api.welcomepickups.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "Airport welcome pickups in 100+ cities.",
        "mcp_tool":  "search_welcome_pickups",
    },
    "opentable": {
        "category":  "travel",
        "label":     "OpenTable Dining",
        "env_key":   "OPENTABLE_API_KEY",
        "base_url":  "https://platform.opentable.com",
        "cost_tier": "free",
        "agent":     "hale",
        "notes":     "Restaurant reservations. Used for pre/post cruise dining.",
        "mcp_tool":  "search_opentable_restaurants",
    },
    "shore_excursions": {
        "category":  "travel",
        "label":     "Shore Excursions Group",
        "env_key":   "SHORE_EXCURSIONS_API_KEY",
        "base_url":  "https://api.shoreexcursionsgroup.com",
        "cost_tier": "commissionable",
        "agent":     "hale",
        "notes":     "Cruise-specific group shore excursions. 10–15% commission.",
        "mcp_tool":  "search_shore_excursions_group",
    },
    "tomtom": {
        "category":  "maps",
        "label":     "TomTom Maps & Geocoding",
        "env_key":   "TOMTOM_API_KEY",
        "base_url":  "https://api.tomtom.com",
        "cost_tier": "free_tier",
        "agent":     "goose",
        "notes":     "Geocoding, routing, port city maps. Used for itinerary map generation.",
        "mcp_tool":  None,
    },

    # ── Google Workspace ──────────────────────────────────────────────────────
    "gmail": {
        "category":  "workspace",
        "label":     "Gmail API",
        "env_key":   "GOOGLE_OAUTH_CREDENTIALS",
        "base_url":  "https://gmail.googleapis.com",
        "cost_tier": "free",
        "agent":     "hale",
        "notes":     "d2mconcierge@gmail.com. Drafts, send, search. Always send FROM d2mconcierge.",
        "mcp_tool":  "gmail_search_messages",
    },
    "google_drive": {
        "category":  "workspace",
        "label":     "Google Drive API",
        "env_key":   "GOOGLE_OAUTH_CREDENTIALS",
        "base_url":  "https://www.googleapis.com/drive",
        "cost_tier": "free",
        "agent":     "hale",
        "notes":     "Dossier storage, itinerary PDFs, ship photos. rclone mirrors daily.",
        "mcp_tool":  "drive_search",
    },
    "google_calendar": {
        "category":  "workspace",
        "label":     "Google Calendar API",
        "env_key":   "GOOGLE_OAUTH_CREDENTIALS",
        "base_url":  "https://www.googleapis.com/calendar",
        "cost_tier": "free",
        "agent":     "hale",
        "notes":     "Booking deadlines, FPDs, client events. Syncs from booking master sheet.",
        "mcp_tool":  "calendar_list_events",
    },
    "google_keep": {
        "category":  "workspace",
        "label":     "Google Keep API",
        "env_key":   "GOOGLE_OAUTH_CREDENTIALS",
        "base_url":  "https://keep.googleapis.com",
        "cost_tier": "free",
        "agent":     "hale",
        "notes":     "Quick notes, checklists. Used for Commander's rapid capture.",
        "mcp_tool":  "keep_create_note",
    },

    # ── Media ──────────────────────────────────────────────────────────────────
    "pexels": {
        "category":  "media",
        "label":     "Pexels Stock Photos",
        "env_key":   "PEXELS_API_KEY",
        "base_url":  "https://api.pexels.com",
        "cost_tier": "free",
        "agent":     "hale",
        "notes":     "Free high-res images. Primary source for itinerary destination photos.",
        "mcp_tool":  "generate_itinerary_images",
    },
    "unsplash": {
        "category":  "media",
        "label":     "Unsplash Stock Photos",
        "env_key":   "UNSPLASH_ACCESS_KEY",
        "base_url":  "https://api.unsplash.com",
        "cost_tier": "free",
        "agent":     "hale",
        "notes":     "Backup image source. Higher quality but stricter terms.",
        "mcp_tool":  None,
    },
}

# ── Lookup helpers ────────────────────────────────────────────────────────────

def get_api(name: str) -> dict | None:
    return APIS.get(name.lower())

def list_by_category(category: str) -> list[str]:
    return [k for k, v in APIS.items() if v["category"] == category]

def list_by_agent(agent: str) -> list[str]:
    return [k for k, v in APIS.items() if v["agent"] in (agent, "auto")]

def list_with_mcp_tools() -> list[str]:
    return [k for k, v in APIS.items() if v.get("mcp_tool")]

def summary_table() -> str:
    """Return a markdown summary table of all APIs."""
    lines = [
        "| API | Category | Cost | Agent | MCP Tool |",
        "|-----|----------|------|-------|----------|",
    ]
    for name, cfg in sorted(APIS.items(), key=lambda x: (x[1]["category"], x[0])):
        lines.append(
            f"| {cfg['label']} | {cfg['category']} | {cfg['cost_tier']} "
            f"| {cfg['agent']} | {cfg.get('mcp_tool') or '—'} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Total APIs registered: {len(APIS)}")
    print()
    print(summary_table())
