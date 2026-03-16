# Build Log: Drive Hardening + Gmail + Tours Module
## Date: 2026-03-05
## Status: COMPLETE

---

## 1. Amadeus Credentials Setup
- Created `~/Thunderbird/amadeus_credentials.json` with test API keys
- Verified OAuth token + airport search (DEN returned)
- **Result:** Amadeus API fully operational

## 2. Google Drive Module Hardening (`thunderbird_drive.py`)

### Changes Made
- **Service caching:** `_get_drive_service()` now builds client once, reuses globally
- **Retry decorator:** `_retry_on_error` auto-retries on HTTP 429/500/503 with exponential backoff (3 attempts)
- **Query escaping:** `_escape_query()` prevents single-quote injection in Drive API queries
- **Pagination:** `drive_list_files` supports up to 500 results across multiple API pages via `nextPageToken`
- **Name search:** `drive_search` gained `search_type` param — `"fullText"` (default) or `"name"` for name-only search
- **Error detail:** HttpError responses now include `status_code` field
- **Import added:** `googleapiclient.errors.HttpError` for typed error handling

### Files Modified
- `~/Thunderbird/thunderbird_drive.py`

### Testing
- Drive API connection verified — listed 5 files including TITAN_BOOKINGS_VAULT folders

---

## 3. Gmail Module (`thunderbird_gmail.py`) — NEW

### Why OAuth 2.0 Instead of Service Account
- John uses personal Gmail (`johnloucks3@gmail.com`), not Google Workspace
- Domain-wide delegation requires Workspace Admin — not available
- Solution: OAuth 2.0 Desktop flow with one-time browser consent

### Tools Built (6)
| Tool | Purpose |
|------|---------|
| `gmail_get_profile` | Connectivity test — returns email, message/thread counts |
| `gmail_search_messages` | Search with Gmail query syntax (from:, subject:, etc.) |
| `gmail_read_message` | Full message content + attachment list (no download) |
| `gmail_read_thread` | All messages in a conversation thread |
| `gmail_list_drafts` | List existing drafts with metadata |
| `gmail_create_draft` | Create draft with reply support — NEVER auto-sends |

### Auth Flow
1. OAuth credentials created in GCP Console (`d2m-python-pipeline` project)
2. Saved as `~/Thunderbird/gmail_oauth_credentials.json`
3. Ran `python3 thunderbird_gmail.py --authorize` — browser consent flow
4. Token saved to `~/Thunderbird/gmail_token.json` — auto-refreshes

### Features
- Cached service instance
- Retry on transient errors (429/500/503)
- Body truncation (30K chars for messages, 15K per thread message)
- Attachment metadata extraction (filename, type, size — no download)
- Clear `RuntimeError` if token missing/expired, pointing to `--authorize`

### Testing
- Profile: 201,855 messages, 189,271 threads confirmed
- Recent messages pulled successfully with headers and snippets

### Files Created
- `~/Thunderbird/thunderbird_gmail.py`
- `~/Thunderbird/gmail_token.json` (auto-generated)

### GCP Setup Required (completed)
- Gmail API enabled in `d2m-python-pipeline` project
- OAuth consent screen configured (External, test user added)
- OAuth Desktop credentials created and downloaded

---

## 4. Tours & Activities Module (`thunderbird_tour_search.py`) — NEW

### Architecture (3-Tier, mirrors hotel module pattern)

**Tier 1 — API + Portal Search:**
- Amadeus Tours & Activities API (`/v1/shopping/activities` by lat/lon)
- Musement (browser scrape — their API now requires partner registration)
- Agent portal browser with login pause (ProjectExpedition, TAAP, Viator TA)
- Consumer price scraping (Expedia, Viator public)
- Content scraping (Fodor's, Rick Steves)

**Tier 2 — Comparison:**
- Side-by-side comparison with net+commission vs consumer pricing
- Best Value and Highest Rated badges
- Savings calculation when consumer prices provided

**Tier 3 — Proposal Generation:**
- Branded PDF with logo, headshot, slogan
- Tour option cards with photos, ratings, pricing
- Comparison table
- Recommendation section
- Gmail draft with PDF attachment via OAuth

### Tools Built (8)
| Tool | Purpose |
|------|---------|
| `search_tours` | Amadeus Tours API — search by coordinates |
| `search_tours_musement` | Musement browser scrape by city |
| `browse_tour_portal` | Visible browser + login pause for agent portals |
| `scrape_consumer_tour_prices` | Headless scrape Expedia/Viator public pricing |
| `scrape_tour_content` | Fodor's + Rick Steves recommendations |
| `compare_tours` | Side-by-side comparison (2-10 tours) |
| `render_tour_quote_pdf` | Branded PDF with D2M branding |
| `email_tour_quote` | Gmail draft via OAuth with PDF attachment |

### Portal Browser Login Pause
- Launches `headless=False` (visible browser window)
- Navigates to portal login page
- Polls for URL change every 3 seconds (configurable `login_timeout`, default 120s)
- Once URL changes from login page, proceeds with search
- Supports: ProjectExpedition, TAAP (Expedia TA), Viator TA, or any custom URL

### Branding
- Logo: `~/Thunderbird/Agency_Logo.png` — embedded as base64 in PDF header
- Headshot: `~/Thunderbird/John_Headshot.jpg` — circular crop in PDF footer
- Slogan: "D2M Travel, Curating the experience of a lifetime" — footer
- Colors: navy #0d1b2e, gold #c9a84c (consistent with CLAUDE.md brand tokens)

### Pricing
- `fmt_usd()` for consistent USD formatting
- `_apply_markup()` with EUR->USD conversion (1.09) and 25% standard / 22% premium markup
- Consumer price comparison with savings calculation

### Testing
- Amadeus Tours: 894 activities returned for Paris — pricing and formatting verified
- Musement: falls back to browser scrape (API requires partner header)
- MCP server: all 53 tools load cleanly

### Files Created
- `~/Thunderbird/thunderbird_tour_search.py`

---

## 5. MCP Server Updates (`travel_mcp_server.py`)

### Changes
- Added imports: `thunderbird_gmail`, `thunderbird_tour_search`
- Added registrations: `register_gmail_tools(mcp)`, `register_tour_search_tools(mcp)`
- Added startup log entries for Gmail (6 tools) and Tours (8 tools)
- **Total tools: 53** (was 35 at session start)

---

## 6. Claude Desktop Config Fix

### File: `~/.config/Claude/claude_desktop_config.json`
- Added `"env": {"PYTHONPATH": "/home/john/Thunderbird"}` to MCP server config
- Without this, module imports fail when Claude Desktop launches the MCP server

---

## 7. Flight Module Gmail Fix Needed (TODO)
- `email_flight_quote` in `thunderbird_flight_search.py` still uses service account delegation for Gmail
- Should be updated to use OAuth like `email_tour_quote` does
- Same issue exists in `thunderbird_hotel_search.py` if it has email tools

---

## File Inventory

| File | Status | Tools |
|------|--------|-------|
| `thunderbird_drive.py` | HARDENED | 8 |
| `thunderbird_gmail.py` | NEW | 6 |
| `thunderbird_tour_search.py` | NEW | 8 |
| `travel_mcp_server.py` | UPDATED | 53 total |
| `gmail_oauth_credentials.json` | NEW | — |
| `gmail_token.json` | NEW (auto) | — |
| `amadeus_credentials.json` | VERIFIED | — |
| `Agency_Logo.png` | VERIFIED | — |
| `John_Headshot.jpg` | VERIFIED | — |
