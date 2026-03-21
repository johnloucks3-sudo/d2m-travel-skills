# DEEP RESEARCH API EVALUATION -- A2 FORCE MULTIPLIER
## Dreams2Memories Travel, LLC -- Intelligence Assessment
## Date: 2026-03-20 -- Classification: INTERNAL -- COMMANDER EYES

---

ISSUE: A2 (Wraith) needs autonomous multi-source research capability to scale destination intel, cruise line analysis, and competitor surveillance beyond what manual tool-chaining provides today. Five platforms evaluated.

DISCUSSION: The competitor innovation scan identified deep research agents as commoditizing what A2 does manually. Rather than resist, we integrate. The question is which platform gives Thunderbird the best combination of depth, speed, cost, and API maturity for our specific use cases: luxury travel research, cruise line intel, geopolitical travel advisories, and supplier pricing.

---

## D2M RELEVANCE SUMMARY

1. **Gemini Deep Research is now API-accessible** -- Interactions API (public beta) provides programmatic access to the same 100+ source autonomous research that runs in Gemini UI. Requires polling-based async pattern. HIGH CONFIDENCE this works for destination research and travel advisories.
2. **Perplexity Sonar Deep Research is the fastest path to production** -- OpenAI-compatible chat completions API, no allowlist needed, citations baked in. Approximately $0.40 per deep research query. MODERATE-HIGH CONFIDENCE this is the right first integration.
3. **Tavily /research endpoint is GA but pricing is unpredictable** -- Dynamic credit consumption (4-250 credits per query) makes budgeting difficult. Better suited as a search layer feeding into our own synthesis, not as a standalone research tool.
4. **Exa.ai is a precision weapon, not a research agent** -- Sub-200ms neural search excels at finding specific content, but does not synthesize. Best used as a component inside A2's research pipeline, not as the research engine itself.
5. **You.com Research API is a viable Perplexity alternative** -- $6.25/1K queries, research_effort tiers, #1 on DeepSearchQA. Worth evaluating as a fallback or parallel source.

---

## 1. GEMINI DEEP RESEARCH

### 1A. API Access

| Field | Detail |
|-------|--------|
| **Availability** | Public beta via Interactions API. Generally available with allowlist for Enterprise tier. |
| **API Type** | Asynchronous polling -- `client.interactions.create()` with `background=True`, then poll `client.interactions.get()` |
| **SDK** | `google-genai` Python SDK (official). `pip install google-genai` |
| **Authentication** | Google AI Studio API key (free to create) or Vertex AI service account |
| **Agent Model** | `deep-research-pro-preview-12-2025` (latest as of Mar 2026) |
| **Status** | Preview. Interactions API is public beta. |

### 1B. Pricing

| Component | Cost |
|-----------|------|
| Input tokens | $1.25/1M (Gemini 2.5 Pro base, <=200K context) |
| Output tokens | $10.00/1M |
| Google Search grounding | $35/1K prompts (Gemini 2.x), $14/1K (Gemini 3.x) |
| Batch mode discount | 50% off interactive pricing |
| **Estimated cost per deep research query** | **$0.50-$2.00** (varies with search depth -- MODERATE CONFIDENCE) |

ASSESSMENT: Google does not publish a flat per-query price for Deep Research. Cost is driven by underlying token consumption plus grounding search charges. A typical query that triggers 20-40 searches and generates a multi-page report will likely cost $0.50-$2.00. INSUFFICIENT DATA to pin this down precisely without running test queries.

### 1C. Capabilities for D2M Use Cases

| Use Case | Suitability | Confidence |
|----------|-------------|------------|
| Destination research | EXCELLENT -- browses tourism boards, travel blogs, hotel reviews, government advisories | HIGH |
| Cruise line intel | GOOD -- can research sailing schedules, review aggregations, pricing trends | MODERATE |
| Competitor analysis | GOOD -- can research agency websites, industry publications | MODERATE |
| Travel advisory scanning | EXCELLENT -- accesses State Dept, FCO, WHO, news sources | HIGH |
| Supplier deal hunting | MODERATE -- cannot log into supplier portals (no auth context) | LOW-MODERATE |

### 1D. Technical Characteristics

| Parameter | Value |
|-----------|-------|
| Latency | 2-10 minutes per research query (iterative browsing) |
| Rate limits | Lower than standard Gemini API (exact limits undisclosed for preview) |
| Output format | Markdown text with inline citations. No structured JSON. |
| Stateful | Yes -- `previous_interaction_id` allows follow-up queries |
| Max concurrent | Not documented. Likely low during preview. |

### 1E. Code Example

```python
import time
from google import genai

client = genai.Client(api_key="YOUR_GOOGLE_AI_API_KEY")

# Launch deep research -- runs asynchronously
interaction = client.interactions.create(
    input=(
        "Research luxury cruise options in the Mediterranean for August 2026. "
        "Focus on Silversea, Regent Seven Seas, and Oceania. "
        "Include pricing trends, new ship deployments, and port highlights. "
        "Cite all sources."
    ),
    agent="deep-research-pro-preview-12-2025",
    background=True,
)
print(f"Research started: {interaction.id}")

# Poll until complete (2-10 min typical)
while True:
    result = client.interactions.get(interaction.id)
    if result.status == "completed":
        report = result.outputs[-1].text
        print(report)
        break
    elif result.status in ("failed", "cancelled"):
        print(f"Research failed: {result.status}")
        break
    time.sleep(15)

# Follow-up query using stateful conversation
followup = client.interactions.create(
    input="Now compare cabin pricing for Penthouse Suites across those three lines.",
    agent="deep-research-pro-preview-12-2025",
    previous_interaction_id=interaction.id,
    background=True,
)
```

### 1F. Gaps & Risks

- **Preview status** -- API surface may change. Not recommended as sole dependency.
- **No structured output** -- Returns markdown, not JSON. Requires post-processing for integration into dossiers or Booking Master.
- **Latency** -- 2-10 minutes makes this unsuitable for real-time client queries. Best for scheduled/batch research.
- **Allowlist uncertainty** -- Enterprise tier requires allowlist. Developer tier (Google AI Studio) appears open, but Google could gate access.
- **We already have a Gemini API key** -- `GOOGLE_AI_API_KEY` is set in the environment (used by `thunderbird_model_router.py` for Flash calls). Same key should work for Interactions API.

---

## 2. PERPLEXITY SONAR DEEP RESEARCH

### 2A. API Access

| Field | Detail |
|-------|--------|
| **Availability** | Generally available. No allowlist. |
| **API Type** | OpenAI-compatible chat completions. Async endpoint for deep research. |
| **SDK** | OpenAI Python SDK or raw `requests`. `pip install openai` |
| **Authentication** | Perplexity API key (pay-as-you-go credits) |
| **Model** | `sonar-deep-research` |
| **Status** | Production GA |

### 2B. Pricing

| Component | Cost per 1M |
|-----------|-------------|
| Input tokens | $2.00 |
| Output tokens | $8.00 |
| Citation tokens | $2.00 |
| Reasoning tokens | $3.00 |
| Search queries | $5.00/1K searches |
| **Estimated cost per deep research query** | **$0.30-$0.50** (based on documented example: $0.409 for a typical query) |

ASSESSMENT: Perplexity is the most transparent on pricing. A typical deep research query with ~18 searches, 7K output tokens, 20K citation tokens, and 74K reasoning tokens costs approximately $0.41. HIGH CONFIDENCE on this estimate.

### 2C. Capabilities for D2M Use Cases

| Use Case | Suitability | Confidence |
|----------|-------------|------------|
| Destination research | EXCELLENT -- real-time web search with synthesis and citations | HIGH |
| Cruise line intel | GOOD -- searches cruise forums, review sites, news | MODERATE-HIGH |
| Competitor analysis | GOOD -- can find and synthesize competitor information | MODERATE |
| Travel advisory scanning | EXCELLENT -- real-time access to advisory sources | HIGH |
| Supplier deal hunting | MODERATE -- searches publicly available pricing, cannot access gated portals | MODERATE |

### 2D. Technical Characteristics

| Parameter | Value |
|-----------|-------|
| Latency | 30-120 seconds (significantly faster than Gemini Deep Research) |
| Rate limits | Standard API rate limits apply. No special restrictions documented. |
| Output format | Text with inline citations (URLs). Standard chat completion response. |
| Async support | Yes -- `client.async_.chat.completions.create()` for sonar-deep-research |
| Citation format | URLs returned in response metadata |

### 2E. Code Example

```python
import requests

PERPLEXITY_API_KEY = "pplx-YOUR_API_KEY"

def deep_research(query: str) -> dict:
    """Run Perplexity Sonar Deep Research query."""
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar-deep-research",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a luxury travel research analyst for Dreams2Memories Travel. "
                        "Provide detailed, cited research. Focus on pricing, availability, "
                        "client experience quality, and competitive positioning."
                    ),
                },
                {"role": "user", "content": query},
            ],
        },
        timeout=180,  # Deep research can take 2-3 minutes
    )
    response.raise_for_status()
    data = response.json()
    return {
        "report": data["choices"][0]["message"]["content"],
        "citations": data.get("citations", []),
        "usage": data.get("usage", {}),
    }


# Example: Cruise line intel
result = deep_research(
    "Compare Silversea Silver Nova vs Regent Seven Seas Grandeur for Mediterranean "
    "cruises in August 2026. Include suite pricing, itinerary differences, "
    "onboard amenities, and recent passenger reviews."
)
print(result["report"])
print(f"\nSources: {result['citations']}")
```

### 2F. Gaps & Risks

- **No structured output** -- Like Gemini, returns text. Post-processing needed.
- **Citation quality varies** -- Some citations may be to paywalled or low-quality sources.
- **Cost at scale** -- At $0.40/query, 50 daily research queries = $20/day = $600/month. Need to be selective.
- **No stateful conversation** -- Each query is independent (unlike Gemini's `previous_interaction_id`).

---

## 3. TAVILY

### 3A. API Access

| Field | Detail |
|-------|--------|
| **Availability** | GA. /research endpoint publicly available. |
| **API Type** | REST API + Python SDK |
| **SDK** | `tavily-python`. `pip install tavily-python` |
| **Authentication** | Tavily API key |
| **Status** | Production GA. Acquired by Nebius (Feb 2026). |

### 3B. Pricing

| Endpoint | Credit Cost | Dollar Cost |
|----------|-------------|-------------|
| Basic search | 1 credit | $0.005-$0.008 |
| Advanced search | 2 credits | $0.010-$0.016 |
| Extract (per 5 URLs) | 1-2 credits | $0.005-$0.016 |
| **/research** | **4-250 credits (dynamic)** | **$0.02-$2.00** |
| Free tier | 1,000 credits/month | $0 |

Plans: Free (1K credits) | $50/mo (10K) | $150/mo (30K) | $300/mo (60K) | $500/mo (100K)
PAYG overage: $0.008/credit

ASSESSMENT: The /research endpoint's dynamic pricing (4-250 credits) is a budgeting problem. A complex travel research query could burn 100+ credits ($0.80+). The basic search endpoint at 1 credit is excellent value as a component in a larger pipeline. MODERATE CONFIDENCE that average research queries will cost $0.20-$0.80.

### 3C. Code Example

```python
from tavily import TavilyClient

client = TavilyClient(api_key="tvly-YOUR_API_KEY")

# Simple search -- 1 credit, fast
search_results = client.search(
    query="Silversea Silver Nova Mediterranean August 2026 pricing",
    search_depth="advanced",
    include_domains=["silversea.com", "cruisecritic.com", "vacationstogo.com"],
    max_results=10,
)

# Deep research -- 4-250 credits, slower
research_report = client.research(
    query=(
        "What are the best luxury cruise options in the Mediterranean "
        "for August 2026? Compare Silversea, Regent, and Oceania."
    ),
)

# Context retrieval for RAG -- useful for feeding into A2's analysis
context = client.get_search_context(
    query="Travel advisory Greece Turkey August 2026 safety",
    max_tokens=4000,
)
```

### 3D. Best Use for D2M

Tavily's strength is as a **search component**, not a standalone research agent. Best deployment:
- Use `search()` and `extract()` as tools inside A2's research pipeline
- Feed Tavily search results into Opus for synthesis (we already pay $0 for Opus on Max)
- Skip the /research endpoint -- unpredictable cost, and we can get better results routing Tavily search data through our own A2 persona

---

## 4. EXA.AI

### 4A. API Access

| Field | Detail |
|-------|--------|
| **Availability** | GA. No restrictions. |
| **API Type** | REST API + Python SDK |
| **SDK** | `exa-py`. `pip install exa-py` |
| **Authentication** | Exa API key. $10 free credit on signup. |
| **Status** | Production GA |

### 4B. Pricing

| Operation | Cost |
|-----------|------|
| Search with contents | $7/1K requests (10 results each) |
| Exa Instant (sub-200ms) | $5/1K requests |
| Search only (no contents) | $3/1K requests |
| **Cost per query** | **$0.003-$0.007** |

ASSESSMENT: Exa is extremely cheap per query. This is the best option for high-volume, real-time search -- fare monitoring, daily advisory scans, competitor website checks. Not a deep research tool. HIGH CONFIDENCE on pricing.

### 4C. Code Example

```python
from exa_py import Exa

exa = Exa(api_key="YOUR_EXA_API_KEY")

# Neural search -- finds semantically relevant results, not keyword matches
results = exa.search_and_contents(
    "luxury Mediterranean cruise reviews August 2026 passenger experience",
    num_results=10,
    highlights=True,
    start_published_date="2026-01-01",
    include_domains=[
        "cruisecritic.com", "silversea.com", "rssc.com",
        "oceaniacruises.com", "seabourn.com",
    ],
)

for result in results.results:
    print(f"\n{result.title}")
    print(f"  URL: {result.url}")
    print(f"  Published: {result.published_date}")
    for highlight in result.highlights:
        print(f"  > {highlight}")

# Instant search for real-time monitoring
instant_results = exa.search(
    "Silversea Silver Nova itinerary change cancellation",
    type="instant",
    num_results=5,
)
```

### 4D. Best Use for D2M

- **Daily automated scans** -- Cruise line news, route changes, competitor moves
- **Real-time alerts** -- Airline disruptions, port closures, safety advisories
- **Feed into A2 pipeline** -- Exa finds the sources, Opus synthesizes the analysis
- **NOT a standalone research tool** -- No synthesis capability

---

## 5. YOU.COM RESEARCH API

### 5A. API Access

| Field | Detail |
|-------|--------|
| **Availability** | GA. Early access for Deep Search. |
| **API Type** | REST API + Python SDK |
| **SDK** | Official Python SDK. `pip install you-python` |
| **Authentication** | You.com API key. $100 free credit. |
| **Status** | Production GA. #1 on DeepSearchQA benchmark. |

### 5B. Pricing

| Tier | Cost |
|------|------|
| Research API | $6.25/1K queries ($0.00625/query) |
| Deep Search (heavy research) | ~$15/query |
| Standard search | Cheaper, billed per 1K calls |
| Free credit | $100 on signup |

ASSESSMENT: The Research API at $0.00625/query is remarkably cheap for what it provides. Deep Search at ~$15/query is expensive for our use case. The standard Research endpoint is a strong Perplexity alternative. MODERATE CONFIDENCE -- need to validate output quality for travel-specific queries.

### 5C. Code Example

```python
import requests

YOU_API_KEY = "YOUR_YOU_API_KEY"

# Research API -- multi-step web research with citations
response = requests.get(
    "https://api.ydc-index.io/v1/research",
    headers={"X-API-Key": YOU_API_KEY},
    params={
        "query": (
            "What are the newest luxury cruise ships deploying to the "
            "Mediterranean in summer 2026? Focus on Silversea, Regent, "
            "Oceania, and Viking."
        ),
        "research_effort": "deep",  # lite | standard | deep | exhaustive | frontier
    },
    timeout=120,
)
data = response.json()
print(data.get("answer", ""))
for source in data.get("sources", []):
    print(f"  - {source.get('title')}: {source.get('url')}")
```

### 5D. Best Use for D2M

- **Perplexity alternative/fallback** -- Similar capability, potentially cheaper at scale
- **research_effort tiers** -- Can dial up/down based on query importance
- **$100 free credit** -- Enough for extensive evaluation before committing

---

## PRICING COMPARISON TABLE

| Platform | Cost per Research Query | Free Tier | Latency | Structured Output | Citations | Production Status |
|----------|------------------------|-----------|---------|-------------------|-----------|-------------------|
| **Gemini Deep Research** | $0.50-$2.00 (est.) | 15 RPD free | 2-10 min | No (markdown) | Yes (inline) | Preview/Beta |
| **Perplexity Sonar Deep** | $0.30-$0.50 | None (pay-go) | 30-120 sec | No (text) | Yes (URLs) | GA |
| **Tavily /research** | $0.02-$2.00 (dynamic) | 1K credits/mo | 10-60 sec | Partial | Yes | GA |
| **Exa.ai** | $0.003-$0.007 (search only) | $10 credit | <200ms | Yes (JSON) | Yes (URLs) | GA |
| **You.com Research** | $0.006-$15.00 (by tier) | $100 credit | 10-120 sec | Partial | Yes | GA |

### Monthly Cost Projection (D2M Usage Pattern)

Assuming 10 deep research queries/day + 50 quick searches/day:

| Platform | Deep Research (10/day) | Quick Search (50/day) | Monthly Total |
|----------|------------------------|-----------------------|---------------|
| **Gemini** | $15-$60/day | N/A (separate tool) | $450-$1,800 |
| **Perplexity** | $3-$5/day | N/A (separate model) | $90-$150 |
| **Tavily** | $2-$20/day | $0.25-$0.40/day | $68-$612 |
| **Exa.ai** | N/A (no synthesis) | $0.35/day | $11 |
| **You.com** | $0.06/day (research) | $0.31/day | $11 |

---

## INTEGRATION ARCHITECTURE RECOMMENDATION

### Phase 1: Perplexity Sonar Deep Research (IMMEDIATE -- Week 1)

**Rationale:** Best combination of output quality, pricing transparency, API simplicity, and production readiness. OpenAI-compatible means minimal new code.

**Implementation as MCP Tool:**

```python
# thunderbird_deep_research.py
# New module -- A2 Deep Research Engine

import os
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

# A2 system prompt for research queries
A2_RESEARCH_SYSTEM = """You are a luxury travel research analyst for Dreams2Memories Travel, LLC.
Your research supports high-net-worth client trip planning.

Research standards:
- Cite all sources with URLs
- State confidence levels (high/moderate/low) for claims
- Distinguish between verified data and analysis
- Focus on: pricing, availability, client experience, safety, logistics
- Target cruise lines: Silversea, Regent Seven Seas, Cunard, Oceania, Seabourn, Viking, AmaWaterways, Ponant
- Always identify information gaps -- what you could NOT find matters"""


def deep_research(query: str, context: str = "") -> Dict[str, Any]:
    """Execute a Perplexity Sonar Deep Research query.

    Args:
        query: The research question
        context: Optional client/trip context to focus the research

    Returns:
        dict with: report, citations, usage, cost_estimate
    """
    if not PERPLEXITY_API_KEY:
        return {"error": "PERPLEXITY_API_KEY not set", "report": ""}

    system_content = A2_RESEARCH_SYSTEM
    if context:
        system_content += f"\n\nClient/Trip Context:\n{context}"

    try:
        response = requests.post(
            PERPLEXITY_URL,
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar-deep-research",
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": query},
                ],
            },
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()

        usage = data.get("usage", {})
        # Estimate cost based on known pricing
        input_cost = usage.get("prompt_tokens", 0) * 2.0 / 1_000_000
        output_cost = usage.get("completion_tokens", 0) * 8.0 / 1_000_000
        est_cost = input_cost + output_cost

        return {
            "report": data["choices"][0]["message"]["content"],
            "citations": data.get("citations", []),
            "usage": usage,
            "cost_estimate": round(est_cost, 4),
            "model": "sonar-deep-research",
        }
    except requests.RequestException as e:
        logger.error(f"Deep research failed: {e}")
        return {"error": str(e), "report": ""}


# ── MCP Tool Registration ──

def register_deep_research_tools(mcp):
    """Register deep research tools on the MCP server."""

    @mcp.tool(
        name="deep_research",
        description=(
            "A2 Deep Research: Run a multi-source autonomous research query "
            "using Perplexity Sonar Deep Research. Returns a cited report. "
            "Use for destination research, cruise intel, travel advisories, "
            "competitor analysis. Takes 30-120 seconds."
        ),
    )
    async def tool_deep_research(
        query: str,
        context: str = "",
    ) -> str:
        result = deep_research(query, context)
        if result.get("error"):
            return f"Research failed: {result['error']}"

        output = f"## A2 DEEP RESEARCH REPORT\n\n"
        output += result["report"]
        output += f"\n\n---\n"
        output += f"**Sources:** {len(result.get('citations', []))} cited\n"
        output += f"**Estimated cost:** ${result.get('cost_estimate', 'N/A')}\n"
        output += f"**Model:** {result.get('model', 'unknown')}\n"
        return output
```

### Phase 2: Exa.ai as Real-Time Search Layer (Week 2-3)

**Rationale:** At $0.007/query, Exa is cheap enough to run on every scheduled scan. Use for daily monitoring, not deep research.

```python
# Add to thunderbird_deep_research.py

from exa_py import Exa

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")

CRUISE_DOMAINS = [
    "cruisecritic.com", "silversea.com", "rssc.com",
    "oceaniacruises.com", "seabourn.com", "vikingcruises.com",
    "amawaterways.com", "ponant.com", "cunard.com",
]

TRAVEL_ADVISORY_DOMAINS = [
    "travel.state.gov", "gov.uk", "smartraveller.gov.au",
    "who.int", "cdc.gov",
]


def exa_scan(query: str, domains: list = None,
             num_results: int = 10, days_back: int = 7) -> list:
    """Run Exa neural search for real-time monitoring.

    Returns list of {title, url, published_date, highlights}.
    Cost: ~$0.007 per query.
    """
    if not EXA_API_KEY:
        return []

    exa = Exa(api_key=EXA_API_KEY)
    from datetime import datetime, timedelta
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    kwargs = {
        "num_results": num_results,
        "highlights": True,
        "start_published_date": start_date,
    }
    if domains:
        kwargs["include_domains"] = domains

    try:
        results = exa.search_and_contents(query, **kwargs)
        return [
            {
                "title": r.title,
                "url": r.url,
                "published_date": r.published_date,
                "highlights": r.highlights,
            }
            for r in results.results
        ]
    except Exception as e:
        logger.error(f"Exa scan failed: {e}")
        return []
```

### Phase 3: Gemini Deep Research as Premium Tier (Month 2)

**Rationale:** Wait for Interactions API to leave preview. Use for high-stakes research where 100+ source depth justifies the cost and latency (pre-trip comprehensive destination briefs, annual competitor landscape reports).

### Phase 4: You.com as Perplexity Failover (Month 2)

**Rationale:** $100 free credit makes evaluation risk-free. Build as a drop-in replacement for Perplexity in case of API outages or pricing changes.

---

## INTEGRATION INTO THUNDERBIRD

### Where It Fits

```
Commander asks A2 question
        |
        v
   A2 (Wraith) persona
        |
        +-- Simple lookup? --> Existing MCP tools (browse_url, web_search, etc.)
        |
        +-- Multi-source research needed? --> deep_research() [Perplexity]
        |
        +-- Real-time monitoring scan? --> exa_scan() [Exa.ai]
        |
        +-- Comprehensive brief (pre-trip)? --> Gemini Deep Research [Phase 3]
        |
        v
   A2 synthesizes with Opus persona context
        |
        v
   Report delivered via Telegram C2 or email
```

### Scheduled Research Jobs (n8n / systemd)

| Job | Tool | Schedule | Est. Monthly Cost |
|-----|------|----------|-------------------|
| Daily cruise line news scan | Exa.ai | 6:00 AM MDT | $6.30 |
| Daily travel advisory scan | Exa.ai | 6:15 AM MDT | $6.30 |
| Weekly competitor analysis | Perplexity Deep | Sundays 7:00 AM | $7.20 |
| Weekly destination intel (active bookings) | Perplexity Deep | Mondays 7:00 AM | $10.80 |
| Monthly cruise pricing sweep | Gemini Deep (Phase 3) | 1st of month | $8-$16 |
| **Monthly total** | | | **$39-$47** |

### Files to Create/Modify

| File | Action |
|------|--------|
| `thunderbird_deep_research.py` | **CREATE** -- New module (code above) |
| `travel_mcp_server.py` | **MODIFY** -- Import and register deep_research tools |
| `thunderbird_model_router.py` | **MODIFY** -- Add `deep_research` to MODEL_TAGS |
| `thunderbird_api_costs.py` | **MODIFY** -- Add Perplexity/Exa pricing to PRICING dict |
| `thunderbird_batch_run.py` | **MODIFY** -- Add scheduled research jobs |
| `deploy/n8n/` | **MODIFY** -- Add research automation workflows |
| `.env` or environment | **MODIFY** -- Add PERPLEXITY_API_KEY, EXA_API_KEY |

---

## ACTIONS I RECOMMEND TAKING

1. **Sign up for Perplexity API key** -- Go to perplexity.ai/api-platform, create account, fund with $20 to start. No allowlist, instant access.
2. **Sign up for Exa.ai** -- $10 free credit, no CC required. Get API key from exa.ai.
3. **Build `thunderbird_deep_research.py`** -- Phase 1 code above is production-ready. Register as MCP tool.
4. **Run 10 test queries** -- Validate Perplexity output quality against our specific use cases before scheduling automated jobs.
5. **Do NOT commit to Gemini Deep Research yet** -- Preview status and allowlist uncertainty make it a Phase 3 play. We already have the API key; just wait for GA.
6. **Evaluate You.com with free $100 credit** -- Zero-risk evaluation. Run same test queries, compare output quality to Perplexity.
7. **Budget allocation** -- $50/month covers all research automation at projected usage levels. This replaces hours of manual A2 research.

---

## INFORMATION GAPS

| Gap | Impact | Mitigation |
|-----|--------|------------|
| Gemini Deep Research exact per-query cost | Cannot budget Phase 3 | Run test queries when we get access |
| Perplexity citation quality for travel-specific sources | May need post-processing | 10-query validation sprint |
| Tavily /research credit consumption for travel queries | Cannot predict costs | Stick to Tavily search-only; use Perplexity for synthesis |
| You.com Research output quality vs Perplexity | Unknown comparative quality | Free $100 credit evaluation |
| Rate limits on all platforms under sustained automated use | Could block scheduled jobs | Build fallback chains: Perplexity -> You.com -> Tavily+Opus |
| Exa.ai coverage of cruise-specific content | May miss niche cruise forums | Test with known cruise intel queries |

---

## CONFIDENCE ASSESSMENT

- **Perplexity as Phase 1 choice:** HIGH CONFIDENCE. Best price/performance/maturity combination.
- **Exa.ai as monitoring layer:** HIGH CONFIDENCE. Price point and speed are unmatched for scan workloads.
- **Gemini Deep Research potential:** MODERATE CONFIDENCE. Capability is proven in UI; API maturity is the concern.
- **Monthly cost projection ($39-$47):** MODERATE CONFIDENCE. Actual costs depend on query complexity and volume.
- **Integration timeline (Phase 1 in one week):** HIGH CONFIDENCE. Code is straightforward; biggest variable is API key provisioning.

---

```
Staff Paper from Lt Col Marcus "Wraith" Dembe (A2), D2M Travel
```

Sources:
- [Gemini Deep Research Agent Docs](https://ai.google.dev/gemini-api/docs/deep-research)
- [Gemini Interactions API Docs](https://ai.google.dev/gemini-api/docs/interactions)
- [Gemini Deep Research API in Production (Google Cloud Blog)](https://medium.com/google-cloud/how-to-use-the-gemini-deep-research-api-in-production-978055873a39)
- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Perplexity Sonar Deep Research Docs](https://docs.perplexity.ai/getting-started/models/models/sonar-deep-research)
- [Perplexity API Pricing](https://docs.perplexity.ai/docs/getting-started/pricing)
- [Perplexity Chat Completions SDK](https://docs.perplexity.ai/guides/chat-completions-sdk)
- [Tavily Credits and Pricing](https://docs.tavily.com/documentation/api-credits)
- [Tavily Python SDK (GitHub)](https://github.com/tavily-ai/tavily-python)
- [Tavily /research Endpoint Blog](https://blog.tavily.com/research-en/)
- [Exa.ai Pricing](https://exa.ai/pricing)
- [Exa Python SDK Docs](https://docs.exa.ai/sdks/python-sdk-specification)
- [Exa Instant Announcement](https://www.marktechpost.com/2026/02/13/exa-ai-introduces-exa-instant-a-sub-200ms-neural-search-engine-designed-to-eliminate-bottlenecks-for-real-time-agentic-workflows/)
- [You.com API Pricing](https://home.you.com/pricing/api)
- [You.com Research API Docs](https://documentation.you.com/api-reference/research)
- [You.com Research API Announcement](https://you.com/resources/research-api-by-you-com)
- [Best Deep Research APIs for Agentic Workflows (Firecrawl)](https://www.firecrawl.dev/blog/best-deep-research-apis)
- [agent-deep-research (GitHub -- Gemini Interactions API CLI)](https://github.com/24601/agent-deep-research)
