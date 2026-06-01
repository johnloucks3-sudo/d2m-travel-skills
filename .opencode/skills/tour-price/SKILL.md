---
name: tour-price
description: "Shore excursion and activity pricing via GetYourGuide, Viator, Shore Excursions Group, Amadeus, and consumer scrapers. Produces side-by-side comparison, D2M commission estimates, and branded PDF quote. Triggers on: tour price, shore excursion, excursion pricing, activity search, GetYourGuide, Viator, things to do, port activity, tour quote, tour options, cruise excursion, excursion recommendation, excursion cost, activity cost, tour comparison, what to do in port"
---

# /tour-price — Shore Excursion & Activity Pricing

You execute this procedure yourself. No handoff to Claude Code.
Use /ask-opus only if you hit a judgment call that requires Opus-level creative reasoning (e.g., writing the recommendation narrative for the PDF).

## Usage

```
/tour-price [port/city] [date YYYY-MM-DD] [optional: keywords]
```

Examples:
- `/tour-price Santorini 2026-08-31`
- `/tour-price Rome 2026-06-15 food tour`
- `/tour-price Dubrovnik 2026-09-02` (cruise port — use `search_shore_excursions_group`)

---

## Source Selection Guide

| Port type | Primary source | Fallback |
|---|---|---|
| Cruise port (SEG covers 300+ ports) | `search_shore_excursions_group` | `search_viator_excursions` |
| Major European city | `search_viator_excursions` + `search_getyourguide_excursions` | `search_tours` (Amadeus by lat/lon) |
| Asia / Americas / global | `search_getyourguide_excursions` | `search_tours_musement` (city name) |
| Any | Consumer price check: `scrape_consumer_tour_prices` | Expert content: `scrape_tour_content` |

Commission rates by source:
- Viator: 8–12% of client price
- GetYourGuide: 8–12% of client price
- Shore Excursions Group: 8% flat
- Amadeus: markup applied by script (standard 25%, premium 22%)

---

## Step 1 — Check Credentials

```bash
# Viator
ls /home/john/Thunderbird/viator_credentials.json 2>/dev/null && echo "FOUND" || echo "MISSING"

# GetYourGuide
ls /home/john/Thunderbird/getyourguide_credentials.json 2>/dev/null && echo "FOUND" || echo "MISSING"

# Shore Excursions Group
ls /home/john/Thunderbird/shore_excursions_credentials.json 2>/dev/null && echo "FOUND" || echo "MISSING"

# Amadeus (fallback)
ls /home/john/Thunderbird/amadeus_credentials.json 2>/dev/null && echo "FOUND" || echo "MISSING"
```

If a credentials file is MISSING, that provider will return `status: credentials_required` — skip to the next source in the fallback chain. Do not stop.

---

## Step 2 — Search via MCP Tools

All search functions are registered as MCP tools via `travel_mcp_server.py`. Call them directly.

### 2A — Shore Excursions Group (cruise ports — primary)

```python
# MCP tool: search_shore_excursions_group
# Args:
#   destination: str  — port city (e.g., "Santorini", "Dubrovnik", "Nassau")
#   ship: str         — ship name, optional (e.g., "Silver Nova")
#   date: str         — YYYY-MM-DD, optional

# Returns JSON:
# {
#   "status": "success",
#   "destination": "Santorini",
#   "total_results": 12,
#   "results": [
#     {
#       "name": "...",
#       "description": "...",      # trimmed to 400 chars
#       "price_per_person_usd": "$89.00",
#       "duration": "4 hours",
#       "booking_url": "...",
#       "image_url": "...",
#       "rating": 4.7,
#       "review_count": 234,
#       "commission_estimate": {"low": "$7.12", "high": "$7.12", "rate_range": "8-8%"},
#       "excursion_id": "...",
#       "source": "shore_excursions_group"
#     }
#   ],
#   "commission_note": "Shore Excursions Group agent commission: 8% of client price"
# }
```

### 2B — Viator Partner API

```python
# MCP tool: search_viator_excursions
# Args:
#   destination: str  — city or region (e.g., "Athens", "Barcelona")
#   date: str         — YYYY-MM-DD (required)
#   keywords: str     — optional filter (e.g., "food tour", "sunset cruise")

# Returns JSON:
# {
#   "status": "success",
#   "total_results": 20,
#   "results": [
#     {
#       "name": "...",
#       "description": "...",      # trimmed to 400 chars
#       "price_per_person_usd": "$95.00",
#       "duration": 180,           # minutes, or "Varies"
#       "booking_url": "https://www.viator.com/tours/[productCode]",
#       "image_url": "...",
#       "rating": 4.8,
#       "review_count": 512,
#       "commission_estimate": {"low": "$7.60", "high": "$11.40", "rate_range": "8-12%"},
#       "product_code": "...",
#       "source": "viator"
#     }
#   ],
#   "commission_note": "Viator agent commission: 8-12% of client price"
# }
```

### 2C — GetYourGuide Integrator API

```python
# MCP tool: search_getyourguide_excursions
# Args:
#   destination: str  — city or region (e.g., "Rome", "Tokyo")
#   date: str         — YYYY-MM-DD (required)
#   keywords: str     — optional filter (e.g., "cooking class", "wine tour")

# Returns JSON:
# {
#   "status": "success",
#   "total_results": 20,
#   "results": [
#     {
#       "name": "...",
#       "description": "...",      # trimmed to 400 chars
#       "price_per_person_usd": "$78.00",
#       "duration": "3 hours",
#       "booking_url": "...",
#       "image_url": "...",
#       "rating": 4.6,
#       "review_count": 308,
#       "commission_estimate": {"low": "$6.24", "high": "$9.36", "rate_range": "8-12%"},
#       "activity_id": "...",
#       "source": "getyourguide"
#     }
#   ],
#   "commission_note": "GetYourGuide partner commission: 8-12% of client price"
# }
```

### 2D — Amadeus Tours & Activities (by coordinates)

Use this when you have lat/lon coordinates for the port and other sources are unavailable.

```python
# MCP tool: search_tours
# Args:
#   latitude: float   — e.g., 36.3932 for Santorini
#   longitude: float  — e.g., 25.4615 for Santorini
#   radius: int       — search radius in km (default 20, max 100)
#   max_results: int  — max results (default 20, max 50)

# Returns JSON:
# {
#   "status": "success",
#   "source": "amadeus",
#   "total": 15,
#   "activities": [
#     {
#       "source": "amadeus",
#       "id": "...",
#       "name": "...",
#       "short_description": "...",
#       "type": "SIGHTSEEING",
#       "rating": 4.5,
#       "booking_link": "...",
#       "pictures": ["url1", "url2", "url3"],
#       "duration": "3 hours",
#       "price": {
#         "amount": 65.0,
#         "currency": "EUR",
#         "net_usd": "$70.85",
#         "markup_pct": "25%",
#         "client_price_usd": "$88.56",
#         "net_raw": 70.85,
#         "client_raw": 88.56
#       },
#       "geo": {"latitude": 36.39, "longitude": 25.46}
#     }
#   ]
# }
# Note: EUR automatically converted at 1.09 rate. Standard markup 25%, premium 22%.
```

### 2E — Musement (free, European/global catalog)

```python
# MCP tool: search_tours_musement
# Args:
#   city: str           — city name (e.g., "Paris", "Rome", "Tokyo")
#   category: str       — optional: "tours", "museums", "food", "outdoor", "nightlife", "shows"
#   max_results: int    — max results (default 20, max 50)

# Note: Musement API requires partner registration. This tool scrapes the public site
# and returns a content_snippet (up to 6000 chars) from the search results page.
# Use for discovery / content research, not structured pricing.
```

---

## Step 3 — Consumer Price Check (optional but recommended for client quotes)

Shows what the client would pay if booking direct — strengthens the D2M value proposition.

```python
# MCP tool: scrape_consumer_tour_prices
# Args:
#   destination: str    — destination city or region
#   tour_name: str      — specific tour/activity name (optional)
#   site: str           — "expedia", "viator", or "both"
#   screenshot: bool    — True to save screenshot

# Returns JSON with content_snippet from consumer-facing pages.
# Extract prices manually from snippet for comparison.
```

Expert content for quality validation (Fodor's + Rick Steves):

```python
# MCP tool: scrape_tour_content
# Args:
#   destination: str    — destination city or region
#   source: str         — "fodors", "ricksteves", or "both"
#   screenshot: bool    — True to save screenshot

# Returns content_snippet from editorial recommendation pages.
# Use to validate tour quality claims and discover curated picks.
```

---

## Step 4 — Build Comparison (if 2+ options found)

Pass the best 2–10 results from Step 2 into the comparison tool.

```python
# MCP tool: compare_tours
# Input: JSON array of tour objects — each must have:
#   name, source, type, duration, rating,
#   price: { client_price_usd, client_raw }
#   Optional: consumer_price (str "$X") to calculate savings

# Returns JSON:
# {
#   "comparison": [
#     {
#       "option": 1,
#       "name": "...",
#       "source": "viator",
#       "type": "SIGHTSEEING",
#       "duration": "3 hours",
#       "rating": 4.8,
#       "net_price": "$76.00",
#       "client_price": "$95.00",
#       "client_raw": 95.0,
#       "consumer_price": "$110.00",
#       "savings": "$15.00",
#       "badges": ["BEST VALUE"]       # or "HIGHEST RATED"
#     }
#   ],
#   "total_options": 3,
#   "recommendation": {
#     "best_value": 2,          # option number
#     "highest_rated": 1        # option number
#   }
# }
```

---

## Step 5 — Render PDF Quote (client-facing deliverable)

```python
# MCP tool: render_tour_quote_pdf
# Args:
#   client_name: str           — client name for header
#   destination: str           — port/city name
#   travel_dates: str          — human-readable, e.g., "August 31, 2026"
#   travelers: str             — number of travelers (default "2")
#   tours_json: str            — JSON array of tour objects (from Step 2 results)
#                                Each tour needs: name, source, type, duration, rating,
#                                price (with client_price_usd), short_description,
#                                pictures (array of URLs), badges (array of strings)
#                                Optional: consumer_price, savings
#   comparison_json: str       — JSON array from compare_tours (optional)
#                                Each row: option, name, source, duration, rating,
#                                client_price, is_pick (bool)
#   recommendation: str        — recommendation narrative (optional)
#   notes: str                 — disclaimers (default: "Prices valid for 48 hours...")
#   output_filename: str       — optional; auto-generated as [Client]_Tours_[Dest]_[MonYYYY].pdf

# Returns JSON:
# {
#   "status": "success",
#   "pdf_path": "/home/john/Thunderbird/output/[filename].pdf",
#   "html_path": "/home/john/Thunderbird/output/[filename].html",
#   "client_name": "...",
#   "destination": "...",
#   "tours_count": 3,
#   "has_logo": true,
#   "has_headshot": true
# }

# Output lands in: /home/john/Thunderbird/output/
```

Branding auto-applied: D2M logo from `/home/john/Thunderbird/Agency_Logo.png`, John's headshot from `/home/john/Thunderbird/John_Headshot.jpg`, slogan "D2M Travel, Curating the experience of a lifetime."

---

## Step 6 — WF-17 Gate (if emailing to client)

**Wing NEVER sends to client. Commander sends.**

Create Gmail draft in d2mconcierge, label `THUNDERBIRD-Commander-Review`.

```python
# MCP tool: email_tour_quote
# Args:
#   to_email: str           — client email address
#   client_name: str        — client name for greeting
#   destination: str        — port/city
#   travel_dates: str       — human-readable dates
#   summary_json: str       — JSON array of summary objects, each:
#                             { option: int, name: str, duration: str, rating, client_price: str }
#   recommendation: str     — brief recommendation text (optional)
#   pdf_path: str           — path to rendered PDF (optional attachment)
#   subject: str            — custom subject (default: "Tour & Activity Options: [destination]")

# Returns JSON:
# {
#   "status": "draft_created",
#   "draft_id": "...",
#   "to": "client@email.com",
#   "subject": "...",
#   "has_pdf_attachment": true,
#   "message": "Gmail draft ready for review. Open Gmail to review and send."
# }

# IMPORTANT: This creates a DRAFT only. It does NOT send.
# Draft appears in d2mconcierge Gmail → Drafts folder.
```

After draft created: notify Commander — "Tour quote draft for [client] re [destination] is in d2mconcierge drafts, labeled THUNDERBIRD-Commander-Review. PDF attached. Awaiting your review."

---

## Harlan Sign-Off (required before WF-17 if any $ figure in client email)

Before surfacing a tour quote email to Commander, Harlan 6-step verification on every dollar figure:

1. Confirm price traces to API response (not memory or inference)
2. Confirm date of price lookup (prices valid 48 hours)
3. Compare vs dossier if client has prior pricing on file — flag any delta
4. Root cause any delta or mark UNRESOLVED
5. Confirm commission estimate is within stated range for provider
6. Sign-off: "Confirmed: [tour name] $X/pp as of [date], source: [viator/gyg/seg/amadeus]"

---

## Reyes Domain — Excursion Recommendation Layer

When building the recommendation narrative for the PDF, pull from the client dossier first:

```bash
# Find client dossier
ls /home/john/Thunderbird/dossiers/ | grep -i "[client-name]"
cat /home/john/Thunderbird/dossiers/[DOSSIER_FILE]
```

Extract from dossier:
- Adventure/mobility level (active/moderate/relaxed)
- Dining preferences (relevant to food tours, cooking classes)
- Any excursion history or stated interests
- Special occasions (anniversary, birthday — affects tour type recommendation)

Match tour options to client profile. The D2M recommendation should name ONE specific tour and explain why it fits this client. Not "Option 2 is good." Say: "For [client names], I'd go with Option 2 — the [tour name]. Given [dossier detail], this matches their [interest] perfectly and [specific reason]."

---

## Agent Portal (manual login — advanced)

For TAAP (Expedia TA), ProjectExpedition, or Viator TA with agent-only pricing, use the browser portal tool. Requires a visible display session.

```python
# MCP tool: browse_tour_portal
# Args:
#   portal: str           — "projectexpedition", "taap", "viator_ta", or custom URL
#   search_query: str     — tour/activity to search after login (optional)
#   destination: str      — destination to search (optional)
#   login_timeout: int    — max seconds to wait for manual login (default 600)
#   screenshot_steps: bool — take screenshots at each step (default True)

# Opens a VISIBLE browser. Commander logs in manually.
# Tool polls for login confirmation (URL change or DOM auth signals).
# After login, searches and returns page_content (up to 8000 chars).
# Screenshots saved to: /home/john/Thunderbird/screenshots/

# Use this only when API sources return credentials_required AND Commander
# is available to complete the browser login.
```

---

## Quality Checklist

- [ ] At least one API source queried for the port/city
- [ ] Credentials checked first — missing creds skipped gracefully, not an error stop
- [ ] Results include price_per_person_usd for each option
- [ ] Commission estimate present for each result
- [ ] Consumer price check run if building a client quote (strengthens value prop)
- [ ] compare_tours run if 2+ options being presented
- [ ] Dossier checked for client excursion preferences (Reyes layer)
- [ ] D2M recommendation is specific to THIS client — not generic
- [ ] PDF rendered to /home/john/Thunderbird/output/ (if client deliverable)
- [ ] All $ figures in email verified via Harlan 6-step before WF-17
- [ ] Draft created in d2mconcierge ONLY — NEVER johnloucks3
- [ ] Commander notified — never sent by Wing

---

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| `status: credentials_required` | Credential file missing — skip to next source. Do not stop the search. |
| `status: endpoint_not_found` (SEG) | SEG API path may differ from stub. Skip to Viator/GYG fallback. |
| Amadeus 401 | Refresh OAuth: `amadeus_credentials.json` client_id/secret may be test-env only |
| Amadeus returns empty | Test environment has limited coverage. Switch to Viator or GYG. |
| Musement returns content_snippet only | Partner API needs registration. Use for discovery, not structured pricing. |
| Browser portal hangs on login | Commander must complete login manually in the opened browser window |
| PDF render fails (WeasyPrint) | Check `weasyprint` installed: `pip show weasyprint`. Fonts must be available. |
| No photos in PDF | `pictures` array in tours_json must have at least one valid URL per tour |
| Draft not appearing in Gmail | Check `thunderbird_gmail.py` OAuth token — may need refresh |
| EUR prices seem off | EUR_TO_USD rate hardcoded at 1.09 in both scripts — update if rate drifts significantly |
