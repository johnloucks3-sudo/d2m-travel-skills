# A2 STAFF PAPER: Four Innovation Targets for Thunderbird OS

**From:** Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)
**To:** Commander (Yoda)
**Date:** 2026-03-20
**Classification:** INTERNAL — Dreams2Memories Travel, LLC

---

## ISSUE

Four emerging technologies require immediate assessment for integration into Thunderbird OS: Aven Hospitality MCP (hotel distribution), Claude Code Channels (Telegram C2 replacement candidate), Firecrawl MCP (web scraping), and Playwright MCP (browser automation). Each represents a potential capability upgrade or redundancy for our existing tooling.

---

## DISCUSSION

### 1. Aven Hospitality MCP Early Access

**What it is:** Aven Hospitality (formerly Sabre's hotel technology unit, acquired by TPG for $1.1B) has embedded Model Context Protocol directly into its SynXis Central Reservation System and Booking Engine, covering 35,000+ hotels across 190+ countries. This exposes verified hotel rates, real-time availability, and property content to AI agents via MCP — no per-property integrations needed.

**Confidence Level: HIGH** on the technology announcement. **MODERATE** on program access for travel advisors.

**Early Access Program:**
- **Timeline:** Q2 2026 (select hotel chains first, broader rollout after)
- **Application URL:** No public application portal exists as of today. The PR Newswire announcement and Skift exclusive both describe the program as targeting "select hotel chains" — not travel agents or AI platform operators.
- **Contact:** media@avenhospitality.com (PR contact from the press release)
- **Leadership:** Amy Read, VP of Innovation, is the named executive driving MCP enablement

**Critical Gap Identified:** The Early Access Program appears hotel-side only — hotels opt in to expose their inventory via MCP. There is no public-facing developer portal, partner API, or agent registration page. The program is designed for hotels to connect TO AI discovery platforms, not for agents to connect TO hotels. This is a supply-side play.

**D2M Relevance Assessment:**
- When Aven's MCP goes live, AI agents (including Thunderbird) will be able to query 35,000 hotels for real-time rates and availability via MCP — but only if Aven publishes their MCP endpoint or we register as a consuming platform
- This could disintermediate Bedsonline/TAAP for hotel search if we can connect directly
- Pricing and final transactions remain under hotel control — commission structure for MCP-connected agents is undefined

**What We Don't Know:**
1. Whether travel advisors/agents can register as MCP consumers (vs. only large AI platforms)
2. The MCP endpoint URL or authentication model
3. Commission structure for bookings originating from MCP queries
4. Whether SynXis MCP exposes net rates or rack rates
5. Whether our existing `search_hotels` / `check_hotel_rates` tools could be rewired to query Aven MCP

**Sources:**
- [PR Newswire — Aven MCP Announcement](https://www.prnewswire.com/news-releases/aven-hospitality-announces-mcp-enablement-across-its-platform-strengthening-hotels-position-in-ai-driven-discovery-302701925.html)
- [Skift Exclusive — Former Sabre Hotel Unit](https://skift.com/2026/03/02/former-sabre-hotel-unit-lays-groundwork-for-ai-distribution-exclusive/)
- [Hotel Management Network](https://www.hotelmanagement-network.com/news/aven-hospitality-enables-mcp-hotel/)

---

### 2. Claude Code Channels (Telegram Integration)

**What it is:** Anthropic launched Claude Code Channels on 2026-03-20 as a research preview. It is a plugin-based system that pushes messages from Telegram (or Discord) into a running Claude Code session on your local machine. The session processes requests with full filesystem, MCP, and git access, then replies back through the same messaging app.

**Confidence Level: HIGH** — official Anthropic documentation reviewed, setup commands verified.

**Architecture:**
- A Channel is an MCP server that pushes events into your running Claude Code session
- Channels are two-way: Claude reads inbound messages and replies back through the same channel
- Events only arrive while the session is open
- Requires Claude Code v2.1.80+, claude.ai login (no API key auth)
- Requires [Bun](https://bun.sh) runtime

**Exact Setup Commands:**
```bash
# 1. Install Bun (if not present)
curl -fsSL https://bun.sh/install | bash

# 2. In Claude Code, add the plugin marketplace
/plugin marketplace add anthropics/claude-plugins-official

# 3. Install the Telegram plugin
/plugin install telegram@claude-plugins-official

# 4. Configure with your BotFather token
/telegram:configure <TELEGRAM_BOT_TOKEN>

# 5. Launch Claude Code with the channel enabled
claude --channels plugin:telegram@claude-plugins-official

# 6. Pair your account (send any message to bot, get pairing code)
/telegram:access pair <code>

# 7. Lock to your account only
/telegram:access policy allowlist
```

**Comparison to Our Custom Telegram C2 (thunderbird_telegram_c2.py):**

| Capability | Our C2 Bot | Claude Code Channels |
|---|---|---|
| Persona routing (/hale, /dani, /dembe, etc.) | YES — 9 persona slash commands | NO — single Claude Code session |
| Multi-command system (/sitrep, /sss, /drafts, /scan, /learn, /voice, /inbox) | YES — 13+ commands | NO — natural language only |
| Commander-only auth | YES — TELEGRAM_COMMANDER_ID lockdown | YES — allowlist pairing |
| MCP tool access | YES — via Agent SDK calls to travel_mcp_server.py | YES — full MCP access natively |
| Always-on daemon | YES — systemd service, runs 24/7 | NO — requires active Claude Code session |
| Client-facing bot (Dani) | SEPARATE BOT (thunderbird_telegram.py) | NOT APPLICABLE |
| COS review gate | YES — drafts go through COS before send | NO — raw Claude responses |
| Draft approval flow (WF17) | YES | NO |
| Session persistence | YES — persistent across reboots | NO — session-scoped |
| Proactive notifications | YES — scheduled sweeps, alerts | NO — reactive only |
| Learning compiler integration | YES — captures diffs, extracts principles | NO |
| Voice ledger integration | YES — per-client tone rules | NO |
| Cost | $0 (Max plan via Agent SDK) | $0 (Max plan, claude.ai login) |

**Assessment:** Claude Code Channels is architecturally elegant but solves a different problem. It is a lightweight remote control for a Claude Code session — useful for developers issuing ad-hoc commands from their phone. Our C2 bot is a full command-and-control center with persona routing, workflow integration, review gates, and 24/7 availability. Channels cannot replace our C2.

**However:** Channels could be useful as a supplementary input — a way for Yoda to push quick messages into an active Claude Code session without opening a terminal. It would run alongside, not instead of, the C2 bot.

**Source:**
- [Claude Code Channels Documentation](https://code.claude.com/docs/en/channels)
- [MacStories First Look](https://www.macstories.net/stories/first-look-hands-on-with-claude-codes-new-telegram-and-discord-integrations/)
- [VentureBeat Coverage](https://venturebeat.com/orchestration/anthropic-just-shipped-an-openclaw-killer-called-claude-code-channels)

---

### 3. Firecrawl MCP Server

**What it is:** An MCP server that provides AI-powered web scraping, crawling, search, and structured data extraction. Handles JavaScript-rendered pages, batch processing, and has an autonomous research agent mode.

**Confidence Level: HIGH** — npm package verified, documentation reviewed, pricing confirmed.

**Installation:**
```bash
# Option A: Add to Claude Code directly
claude mcp add firecrawl -- npx -y firecrawl-mcp

# Option B: Add to mcp.json (for YOGA MCP server)
# In ~/.claude/mcp.json or project mcp.json:
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "fc-YOUR_API_KEY"
      }
    }
  }
}

# Option C: Self-hosted with HTTP transport (for integration with our MCP server)
env HTTP_STREAMABLE_SERVER=true \
  FIRECRAWL_API_KEY=fc-YOUR_KEY \
  npx -y firecrawl-mcp
# Exposes endpoint at http://localhost:3000/mcp
```

**Tools Exposed (12):**

| Tool | Description |
|---|---|
| `firecrawl_scrape` | Single URL extraction — markdown, JSON, structured |
| `firecrawl_batch_scrape` | Parallel multi-URL processing |
| `firecrawl_map` | Website URL discovery and indexing |
| `firecrawl_crawl` | Async site-wide crawling with depth control |
| `firecrawl_check_crawl_status` | Monitor crawl jobs |
| `firecrawl_search` | Web search with optional result scraping |
| `firecrawl_extract` | LLM-powered structured data extraction with schema |
| `firecrawl_agent` | Autonomous multi-step research agent |
| `firecrawl_agent_status` | Agent job status polling |
| `firecrawl_browser_create` | Persistent CDP browser sessions |
| `firecrawl_browser_execute` | Run code (bash/Python/JS) in browser context |
| `firecrawl_browser_delete` | Terminate browser sessions |

**Pricing:**

| Tier | Price | Credits/mo | Concurrency |
|---|---|---|---|
| Free | $0 | 500 (lifetime, one-time) | 2 |
| Hobby | $16/mo | 3,000 | 5 |
| Standard | $83/mo | 100,000 | 50 |
| Growth | $333/mo | 500,000 | 100 |

Credit costs: 1 credit per scraped page, 2 credits per 10 search results, 2 credits per minute of browser use.

**Comparison to Our Existing `browse_url` Tool:**

| Capability | Our `browse_url` (thunderbird_browser.py) | Firecrawl MCP |
|---|---|---|
| Single page scrape | YES — Playwright Stealth | YES — with JS rendering |
| Batch/crawl | NO | YES — async crawl with depth |
| Web search | NO (separate tools) | YES — built-in search |
| Structured extraction | NO — raw text/HTML | YES — LLM-powered with schema |
| Site mapping | NO | YES — URL discovery |
| Anti-detection | YES — playwright-stealth | YES — built-in |
| Persistent login profiles | YES — our killer feature | NO |
| Screenshot | YES | NO (browser mode only) |
| Click/interact | YES (browse_and_click) | YES (browser mode) |
| Cost | $0 (self-hosted Playwright) | $16-83/mo or free 500 |
| Agent portals (Bedsonline, Viking TA) | YES — profile-based auth | NO — no persistent auth |

**Assessment:** Firecrawl is superior for bulk scraping, site crawling, structured extraction, and web search. It does NOT replace our browse_url for authenticated portal work (Bedsonline, Viking TA, TESS logins). The two are complementary. The Free tier (500 credits) is sufficient for evaluation. Hobby tier ($16/mo) would cover our typical usage.

**Key D2M Use Cases:**
- Scraping cruise line pricing pages (replaces fragile custom scrapers)
- Competitor website monitoring
- Structured extraction of hotel amenities, port info, excursion details
- Research agent for destination intel gathering

**Sources:**
- [Firecrawl MCP Documentation](https://docs.firecrawl.dev/mcp-server)
- [GitHub — firecrawl-mcp-server](https://github.com/firecrawl/firecrawl-mcp-server)
- [NPM — firecrawl-mcp](https://www.npmjs.com/package/firecrawl-mcp)
- [Firecrawl Pricing](https://www.firecrawl.dev/pricing)

---

### 4. Playwright MCP Server (Microsoft Official)

**What it is:** Microsoft's official MCP server for browser automation via Playwright. Exposes 25+ tools for navigating, clicking, typing, screenshots, and page analysis. Uses structured accessibility snapshots instead of pixel-based vision by default — highly token-efficient.

**Confidence Level: HIGH** — npm package verified, Microsoft-maintained, Claude Code integration documented.

**Installation:**
```bash
# Option A: Add to Claude Code directly (recommended)
claude mcp add playwright -- npx @playwright/mcp@latest

# Option B: Add to mcp.json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}

# Option C: With headless mode (for server environments like YOGA)
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless"]
    }
  }
}

# Option D: With specific browser
claude mcp add playwright -- npx @playwright/mcp@latest --browser chromium --headless
```

**Key Configuration Flags:**

| Flag | Default | Description |
|---|---|---|
| `--browser` | chromium | chromium, firefox, webkit, msedge |
| `--headless` | false | Headless mode for server use |
| `--user-data-dir` | auto | Persistent browser profile path |
| `--viewport-size` | 1280x720 | Browser viewport dimensions |
| `--timeout-action` | 5000ms | Action timeout |
| `--timeout-navigation` | 60000ms | Navigation timeout |
| `--isolated` | false | In-memory profile, no disk persistence |
| `--storage-state` | none | Load cookies/storage from file |
| `--caps vision` | off | Enable screenshot-based vision mode |
| `--snapshot-mode` | incremental | incremental, full, or none |

**Tools Exposed (25+):**

| Category | Tools |
|---|---|
| Navigation | `browser_navigate`, `browser_navigate_back`, `browser_close` |
| Interaction | `browser_click`, `browser_type`, `browser_hover`, `browser_drag`, `browser_select_option`, `browser_press_key` |
| Observation | `browser_snapshot`, `browser_take_screenshot`, `browser_console_messages` |
| Tabs | `browser_tab_list`, `browser_tab_new`, `browser_tab_close` |
| Files/Dialogs | `browser_file_upload`, `browser_handle_dialog` |
| Output | `browser_pdf_save` |
| Waiting | `browser_wait_for` |
| Resize | `browser_resize` |

**Comparison to Our Existing Browser Tools:**

| Capability | Our Tools (thunderbird_browser.py) | Playwright MCP (@playwright/mcp) |
|---|---|---|
| Navigate & scrape | browse_url | browser_navigate + browser_snapshot |
| Click/interact | browse_and_click (JSON action array) | browser_click (natural language ref) |
| Form fill | browse_and_click (type action) | browser_type (element ref) |
| Login persistence | browse_login (profile-based) | --user-data-dir / --storage-state |
| Screenshots | YES | YES (+ accessibility snapshots) |
| Tab management | NO | YES — full tab control |
| PDF generation | NO | YES — browser_pdf_save |
| Dialog handling | NO | YES — browser_handle_dialog |
| File upload | NO | YES — browser_file_upload |
| Drag & drop | NO | YES — browser_drag |
| Console access | NO | YES — browser_console_messages |
| Stealth/anti-detection | YES — playwright-stealth | NO — standard Playwright |
| Agent portal profiles | YES — named profiles (bedsonline, viking_ta) | Partial — --user-data-dir |
| Cost | $0 | $0 |
| Maintained by | D2M (us) | Microsoft |

**Assessment:** The Microsoft Playwright MCP is significantly more capable than our custom browser module for general automation — tab management, dialog handling, file upload, PDF save, drag-and-drop, and accessibility snapshots are all features we lack. However, it does NOT include playwright-stealth, which we rely on for anti-detection on supplier portals. The two could coexist: Playwright MCP for general browsing tasks, our module for authenticated stealth portal work.

**Key D2M Use Cases:**
- General web research without needing our custom code
- PDF capture of booking confirmations
- File upload to supplier portals
- Multi-tab workflow automation
- Accessibility-snapshot-based page understanding (cheaper than vision)

**Sources:**
- [GitHub — microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
- [Simon Willison — Using Playwright MCP with Claude Code](https://til.simonwillison.net/claude-code/playwright-mcp-claude-code)
- [Builder.io — Playwright MCP Server with Claude Code](https://www.builder.io/blog/playwright-mcp-server-claude-code)

---

## OPTIONS

### Option 1: Full Adoption (all four)
Install Firecrawl MCP + Playwright MCP immediately. Set up Claude Code Channels as supplementary C2 input. Email Aven Hospitality to register interest. Cost: ~$16/mo (Firecrawl Hobby), rest is $0.

### Option 2: Targeted Adoption (Firecrawl + Playwright only)
Install both MCP servers on YOGA. Skip Channels (our C2 is superior). Monitor Aven from a distance until they publish a developer/agent portal. Cost: ~$16/mo.

### Option 3: Conservative — Playwright MCP only
Zero-cost upgrade. Playwright MCP adds 15+ capabilities we lack, no subscription required. Evaluate Firecrawl after free tier trial. Cost: $0.

---

## ACTIONS I RECOMMEND TAKING

1. **Playwright MCP — Install today.** Zero cost, zero risk, immediate capability gain. Run on YOGA headless:
   ```bash
   claude mcp add playwright -- npx @playwright/mcp@latest --headless
   ```
   This gives us tab management, PDF save, dialog handling, file upload, and accessibility snapshots we currently lack. Keep our `thunderbird_browser.py` for stealth portal work.

2. **Firecrawl MCP — Sign up for Free tier today, install, evaluate this week.** Get an API key at https://www.firecrawl.dev/app/api-keys (500 free credits, no card). Run a test scrape against a cruise pricing page. If it handles JS-rendered content better than our browse_url, upgrade to Hobby ($16/mo).
   ```bash
   claude mcp add firecrawl -- npx -y firecrawl-mcp
   ```

3. **Claude Code Channels — Do NOT migrate the C2 bot.** Our thunderbird_telegram_c2.py has persona routing, workflow integration, COS review gates, 24/7 daemon operation, and session persistence that Channels does not and cannot replicate. However, Channels could be useful as a secondary quick-input path during active coding sessions. Low priority — revisit after Channels exits research preview and supports always-on operation.

4. **Aven Hospitality — Send an inquiry email TODAY to media@avenhospitality.com.** The Early Access Program targets hotels, not agents — but we should register D2M's interest as an AI-powered travel advisory platform that would consume their MCP endpoint. The worst they say is "not yet." Draft below:

   > Subject: MCP Early Access — AI Travel Advisory Platform Interest
   >
   > I lead Dreams2Memories Travel, a luxury travel advisory practice that has built an AI-powered booking and concierge platform (Thunderbird OS) using the Model Context Protocol. We currently connect to hotel, cruise, and excursion suppliers via MCP and would be interested in consuming Aven's SynXis MCP endpoint as an early access participant.
   >
   > Our platform serves high-net-worth clients booking luxury properties across your 35,000+ hotel network. Real-time rate and availability access via MCP would allow us to surface verified hotel options within our AI concierge workflow.
   >
   > We would welcome the opportunity to discuss participation in your Q2 2026 Early Access Program.
   >
   > Thanks,
   > John Loucks
   > Dreams2Memories Travel, LLC

5. **Integration architecture on YOGA.** Both Firecrawl and Playwright MCP should run as separate MCP servers alongside our existing `travel_mcp_server.py`. They do NOT need to be embedded into our server — Claude Code and the Agent SDK can connect to multiple MCP servers simultaneously via `mcp.json`. Our `thunderbird_browser.py` remains the stealth-authenticated portal module.

---

*Staff Paper from Lt Col Marcus "Wraith" Dembe, A2, Dreams2Memories Travel, LLC*
