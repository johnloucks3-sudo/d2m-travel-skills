# MCP Directory Submission Guide
## Thunderbird OS — Dreams2Memories Travel MCP Server
### Prepared by: A5 (Castillo) | 2026-03-20

---

## 1. SUBMISSION STRATEGY

### Priority Directories

| # | Directory | URL | Audience | Priority | Status |
|---|-----------|-----|----------|----------|--------|
| **1** | **Smithery** | smithery.ai | Developers building MCP integrations, Claude/LLM power users | **HIGH** — largest curated MCP directory, editorial review | [ ] |
| **2** | **PulseMCP** | pulsemcp.com | MCP ecosystem tracker, dev community, AI builders | **HIGH** — featured listings, newsletter distribution | [ ] |
| **3** | **MCPize** | mcpize.com | Claude Desktop users, MCP newcomers, tool discoverers | **HIGH** — fast-growing, category browsing | [ ] |
| **4** | **Glama MCP Directory** | glama.ai/mcp/servers | Claude/LLM developers, open-source builders | **MEDIUM** — GitHub-indexed, auto-crawls repos | [ ] |
| **5** | **MCP Hub** | mcphub.io | Enterprise MCP users, tool aggregators | **MEDIUM** — newer directory, growing | [ ] |
| **6** | **Awesome MCP Servers** | github.com/punkpeye/awesome-mcp-servers | GitHub community, open-source devs | **MEDIUM** — PR-based, curated awesome-list | [ ] |
| **7** | **MCP.so** | mcp.so | Developer directory, search-oriented | **LOW** — smaller but indexed by search engines | [ ] |
| **8** | **Cursor MCP Directory** | cursor.directory | Cursor IDE users, coding AI users | **LOW** — IDE-specific but high traffic | [ ] |

### Submission Order
1. Smithery + PulseMCP simultaneously (both have review periods)
2. MCPize (quick listing, no review gate)
3. Glama / MCP Hub / Awesome MCP Servers (batch submit)
4. Cursor / MCP.so (opportunistic)

### Pre-Submission Checklist
- [ ] Ensure `mcp.d2mluxury.quest` is reachable externally (Cloudflare tunnel up)
- [ ] Verify `/mcp` endpoint returns valid MCP Streamable HTTP responses
- [ ] Prepare 3-4 screenshots of tool output (quote PDFs, dossier views, search results)
- [ ] GitHub repo or public docs page for the listing link (if required — some directories need a repo URL)
- [ ] Record a 60-second Loom demo showing a flight search → quote PDF flow

---

## 2. LISTING COPY

### Title
```
Thunderbird OS — AI Luxury Travel Concierge (170+ Tools)
```

### Short Description (max 160 chars)
```
Full-stack luxury travel MCP server: flights, hotels, cruises, excursions, transfers, dining, client management, PDF generation, and Google Workspace — 170+ tools.
```

### Long Description (Directory Listing Body)
```
Thunderbird OS is a production MCP server powering Dreams2Memories Travel, LLC — an AI-driven luxury travel concierge.

170+ tools across 56 modules covering the complete travel advisory workflow:

SEARCH & BOOKING
• Flight search & price verification (Amadeus GDS, FlightAware, FR24)
• Hotel search & rate comparison (Bedsonline/Hotelbeds, Expedia TAAP)
• Cruise voyage & cabin scraping (8 luxury lines — Silversea, Regent Seven Seas, Cunard, Viking, Oceania, Seabourn, Ponant, AmaWaterways)
• Excursion search (Viator, GetYourGuide, Musement, Shore Excursions Group)
• Transfer booking (Mozio, Welcome Pickups, Blacklane)
• Restaurant search & reservations (OpenTable)
• Tour search (Amadeus, Musement, consumer price scraping)

INTELLIGENCE & MONITORING
• Fare watch with price history tracking
• Airline route change monitoring
• Competitive surveillance
• Ship intelligence sweeps across luxury cruise lines
• World intelligence briefings (travel advisories, country intel, NOAA weather)
• X/OSINT feed scanning
• Morning briefing automation

CLIENT MANAGEMENT
• Trip dossiers with gap detection scanner
• Booking master synchronization (Excel + Google Sheets)
• Anchor date tracking with calendar sync
• Commission reconciliation
• Guest profile forms
• Client materials generation (branded PDFs)
• Survey compilation

DOCUMENT GENERATION
• Branded PDF quotes (flights, hotels, tours, cruises)
• Hotel guide PDFs with comparison matrices
• Itinerary generation from templates
• Ship comparison reports (PDF + DOCX)

GOOGLE WORKSPACE
• Gmail (search, read, draft, send, labels, threads)
• Google Drive (upload, download, search, folder management)
• Google Calendar (events, free time, meeting scheduling)
• Google Keep (notes, checklists)
• Evernote mirroring

AI PERSONA SYSTEM
• 8 specialized AI personas (A-Staff model)
• CrewAI multi-agent pipelines
• Agent-to-Agent (A2A) protocol
• Voice ledger for per-client tone management
• Learning compiler (captures edits, extracts principles, applies forward)

INFRASTRUCTURE
• Telegram C2 bot integration
• Commander inbox (email classification + tasking)
• Session checkpointing
• Health monitoring
• Shell execution with audit logging
• TESS booking system integration (Outside Agents)
• Shared memory across sessions

Transport: Streamable HTTP (production), SSE (legacy), stdio (local CLI)
Runtime: Python 3.11+ on FastMCP
```

### Category Tags
```
travel, luxury-travel, booking, flights, hotels, cruises, excursions, transfers,
google-workspace, gmail, pdf-generation, client-management, ai-agents, crewai,
intelligence, monitoring, concierge, automation, multi-agent, a2a
```

### Screenshots to Prepare

| # | Screenshot | What It Shows |
|---|-----------|---------------|
| 1 | Hotel guide PDF output | A branded D2M hotel guide with comparison matrix, navy/gold design |
| 2 | Flight search results | Amadeus search → structured JSON with pricing, routing, airlines |
| 3 | Cruise cabin availability | Live Playwright scrape of Silversea or Regent voyage page |
| 4 | Tool list in Claude Desktop | The full 170+ tool list as seen by the LLM client |
| 5 | Trip dossier | Client dossier with booking details, anchor dates, gap alerts |

---

## 3. DIFFERENTIATION POINTS

Use these in listing descriptions, social posts, and any pitch copy.

### vs. Generic Travel APIs (Amadeus MCP, Booking.com scrapers)
- **Full workflow, not just search.** Most travel MCP servers do one thing (flight search or hotel lookup). Thunderbird covers search → compare → quote → PDF → email → track → reconcile commissions. End-to-end.
- **8 luxury cruise lines.** No other MCP server scrapes live cabin availability across Silversea, Regent, Cunard, Viking, Oceania, Seabourn, Ponant, and AmaWaterways. This is not consumer cruise shopping — it is advisor-grade intelligence.
- **Multi-source aggregation.** Hotels from Bedsonline AND Expedia TAAP. Excursions from Viator AND GetYourGuide AND Musement AND Shore Excursions Group. Transfers from Mozio AND Welcome Pickups AND Blacklane. Compare net rates across suppliers in one call.

### vs. CRM/Booking Systems
- **AI-native.** Built for LLM consumption from day one — every tool returns structured JSON that Claude can reason over. Not a REST API wrapped in MCP; designed for MCP.
- **Voice and tone management.** The voice ledger tracks how the advisor writes to each client tier. The learning compiler captures edits and applies them forward. No other travel MCP does this.
- **Persona system.** 8 specialized AI personas with distinct competencies (research, concierge, finance, strategy, ethics). CrewAI pipelines for multi-agent research. This is an operating system, not a tool collection.

### vs. DIY Automation (n8n, Zapier, Make)
- **170+ tools, zero workflow configuration.** Connect the MCP server and every tool is available to the LLM immediately. No drag-and-drop workflow building, no trigger mapping.
- **Branded document output.** PDF generation with Jinja2 + WeasyPrint — hotel guides, flight quotes, tour quotes, ship comparisons — all in D2M branding. The LLM generates the document, not just the data.

### The One-Liner
> "The only MCP server that takes a client from 'I want to go to Greece' to a branded PDF proposal with hotels, flights, excursions, transfers, dining, and a cruise comparison — in one session."

---

## 4. TARGET USERS

### Primary
| Segment | Why They Care |
|---------|--------------|
| **Independent travel advisors** | Instant access to multi-supplier search, branded quotes, client management — replaces 6+ browser tabs and manual PDF creation |
| **Host agency affiliates (Outside Agents, CLIA, ASTA)** | Commission tracking, TESS integration, booking reconciliation — advisor-grade back office |
| **AI/LLM developers in travel** | Production-tested MCP server architecture: 56 modules, Streamable HTTP, CrewAI integration, A2A protocol |
| **Luxury travel agencies (small teams)** | 8-line cruise intelligence, voice/tone management, branded document generation — enterprise tooling at indie scale |

### Secondary
| Segment | Why They Care |
|---------|--------------|
| **MCP ecosystem builders** | Reference implementation for a large-scale, multi-module MCP server with production transport |
| **Claude Code power users** | Example of what a 170+ tool MCP server looks like in daily production use |
| **Travel tech startups** | Architecture patterns: fare watch, anchor dates, dossier scanning, commission reconciliation |

---

## 5. TECHNICAL REQUIREMENTS

### Runtime
- **Python:** 3.11+
- **MCP SDK:** `mcp[server]` (FastMCP) — latest version
- **Transport:** Streamable HTTP (production), SSE (legacy/deprecated April 2026), stdio (local CLI)
- **Default Port:** 8765

### Key Dependencies
```
fastmcp
pydantic>=2.0
playwright (+ playwright-stealth for cruise scraping)
weasyprint (PDF generation)
jinja2 (template engine)
openpyxl (Excel sync)
amadeus (flight/tour search — requires API key)
google-api-python-client (Gmail, Drive, Calendar, Keep)
google-auth-oauthlib
crewai (multi-agent pipelines)
httpx (async HTTP)
```

### API Keys Required
| Service | Key Type | Where to Get |
|---------|----------|-------------|
| Amadeus | API Key + Secret | developers.amadeus.com |
| Bedsonline/Hotelbeds | API Key + Secret | developer.hotelbeds.com |
| Expedia TAAP | Partner credentials | expediapartnersolutions.com |
| FlightAware | AeroAPI key | flightaware.com/aeroapi |
| FR24 (FlightRadar24) | API key | flightradar24.com/premium |
| Viator | Partner API key | viatorpartner.com |
| GetYourGuide | Partner API key | partner.getyourguide.com |
| Mozio | API key | mozio.com/partner |
| Welcome Pickups | Partner credentials | welcomepickups.com |
| Blacklane | API key | blacklane.com/partners |
| OpenTable | Affiliate API | opentable.com/affiliates |
| Google OAuth | Service account JSON | console.cloud.google.com |
| Stability AI | API key (optional, for image generation) | stability.ai |

### Connection
```json
{
  "mcpServers": {
    "dreams2memories": {
      "url": "https://mcp.d2mluxury.quest/mcp",
      "transport": "streamable-http"
    }
  }
}
```

For local/stdio:
```json
{
  "mcpServers": {
    "dreams2memories": {
      "command": "python",
      "args": ["travel_mcp_server.py"],
      "cwd": "/home/john/Thunderbird"
    }
  }
}
```

### Server Launch
```bash
# Production (Streamable HTTP behind Cloudflare tunnel)
python travel_mcp_server.py --http --port=8765

# Legacy SSE (deprecated)
python travel_mcp_server.py --sse --port=8765

# Local stdio (Claude CLI)
python travel_mcp_server.py
```

### Infrastructure (D2M Production)
- **Host:** YOGA (192.168.1.198) — openSUSE Tumbleweed
- **Tunnel:** Cloudflare → `mcp.d2mluxury.quest` → localhost:8765
- **Endpoint:** `https://mcp.d2mluxury.quest/mcp`
- **DNS Rebinding:** Configured for tunnel hostname, LAN, and Tailscale IPs
- **Service:** systemd unit for auto-restart

---

## 6. SUBMISSION TEMPLATES

### Smithery Submission (smithery.ai)
Smithery uses a `smithery.yaml` manifest. Prepare this file in the repo root:

```yaml
name: thunderbird-os
display_name: "Thunderbird OS — AI Luxury Travel Concierge"
description: "Production MCP server for luxury travel advisory — 170+ tools covering flights, hotels, cruises, excursions, transfers, dining, Google Workspace, client management, and AI persona coordination."
icon: "✈️"
categories:
  - travel
  - productivity
  - automation
  - ai-agents
transport: streamable-http
url: https://mcp.d2mluxury.quest/mcp
```

### Awesome MCP Servers PR
Submit a PR adding this line under the `Travel` category (or create the category):

```markdown
- [Thunderbird OS](https://mcp.d2mluxury.quest) - Full-stack luxury travel concierge MCP server with 170+ tools: flights (Amadeus), hotels (Bedsonline/TAAP), 8 luxury cruise lines, excursions, transfers, dining, Google Workspace, branded PDF generation, AI persona system, and client management.
```

### PulseMCP Submission
PulseMCP accepts submissions via their website form. Use:
- **Name:** Thunderbird OS
- **One-line:** AI luxury travel concierge — 170+ MCP tools from flight search to branded PDF delivery
- **Category:** Travel & Hospitality
- **Link:** https://mcp.d2mluxury.quest

---

## 7. POST-SUBMISSION TRACKING

| Directory | Submitted | Listed | Notes |
|-----------|-----------|--------|-------|
| Smithery | | | |
| PulseMCP | | | |
| MCPize | | | |
| Glama | | | |
| MCP Hub | | | |
| Awesome MCP Servers | | | |
| MCP.so | | | |
| Cursor Directory | | | |

Update this table as submissions go out.

---

*Prepared by A5 (Castillo) — Strategy & Business Growth, Dreams2Memories Travel, LLC*
