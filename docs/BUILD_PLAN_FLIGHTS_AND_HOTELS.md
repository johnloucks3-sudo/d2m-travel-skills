# THUNDERBIRD BUILD PLAN: Flight Search + Hotel Compare + Email Quotes
## Dreams2Memories Travel, LLC
### Created: 2026-03-04 | Status: ALL PHASES COMPLETE

---

## Phase 1: Flight Search — COMPLETE

### File: `thunderbird_flight_search.py`

**API:** Amadeus Self-Service API (OAuth2 client credentials)

**MCP Tools:**
| Tool | Purpose |
|------|---------|
| `search_flights` | Search by origin/dest/dates, returns fares with D2M markup |
| `verify_flight_price` | Re-verify pricing before quoting (prices shift constantly) |
| `search_airports` | Autocomplete airport/city IATA codes |

**Credentials:** `~/Thunderbird/amadeus_credentials.json`
```json
{
  "client_id": "YOUR_AMADEUS_API_KEY",
  "client_secret": "YOUR_AMADEUS_API_SECRET",
  "base_url": "https://test.api.amadeus.com"
}
```
Get free API key: https://developers.amadeus.com/ (500 calls/month)

---

## Phase 2: Flight Compare + Quote Email — COMPLETE

### Tools (in `thunderbird_flight_search.py`):
| Tool | Purpose |
|------|---------|
| `compare_flights` | Side-by-side comparison of 2-5 offers with badges (BEST PRICE, FEWEST STOPS) |
| `render_flight_quote_pdf` | Branded D2M PDF via `flight_quote.html.j2` template + WeasyPrint |
| `email_flight_quote` | Gmail draft with branded HTML body + PDF attachment |

### Template: `flight_quote.html.j2`
- D2M brand CSS (navy/gold tokens)
- Flight option cards with segment details
- Side-by-side comparison table
- Recommendation box
- D2M footer with contact info

---

## Phase 3: Hotel Compare + Quote Email — COMPLETE

### Tools (in `thunderbird_hotel_search.py`):
| Tool | Purpose |
|------|---------|
| `compare_hotels` | Side-by-side comparison of 2-3 hotels with pricing, cancellation, markup |
| `render_hotel_quote_pdf` | Branded D2M PDF with hotel comparison table + WeasyPrint |
| `email_hotel_quote` | Gmail draft with branded HTML body + PDF attachment |

---

## All New MCP Tools (12 total)

### Flight (6 tools — `thunderbird_flight_search.py`)
1. `search_flights` — Amadeus flight search
2. `verify_flight_price` — price verification
3. `search_airports` — IATA code lookup
4. `compare_flights` — side-by-side comparison
5. `render_flight_quote_pdf` — D2M branded PDF
6. `email_flight_quote` — Gmail draft + attachment

### Hotel (3 new tools — `thunderbird_hotel_search.py`)
7. `compare_hotels` — side-by-side comparison
8. `render_hotel_quote_pdf` — D2M branded PDF
9. `email_hotel_quote` — Gmail draft + attachment

---

## Architecture

- All USD formatting in Python via `fmt_usd()` — never in templates
- 25% standard markup on net (22% for premium/SLH)
- EUR to USD at 1.09 (configurable)
- Gmail drafts via Google service account with domain delegation
- PDF render via WeasyPrint
- All tools: async, Pydantic Field() params, JSON string returns
- Output directory: `~/Thunderbird/output/`

---

## File Inventory

| File | Status |
|------|--------|
| `thunderbird_flight_search.py` | NEW — 6 MCP tools |
| `flight_quote.html.j2` | NEW — Jinja2 flight quote template |
| `thunderbird_hotel_search.py` | EXTENDED — 3 new MCP tools added |
| `travel_mcp_server.py` | UPDATED — registers flight tools, updated startup log |
| `CLAUDE.md` | UPDATED — documented new module and tool count |
| `amadeus_credentials.json` | USER ACTION — create with Amadeus API keys |
| `BUILD_PLAN_FLIGHTS_AND_HOTELS.md` | This file |

---

## Gmail Setup Note

Email tools use Google service account with domain-wide delegation to
`johnloucks3@gmail.com`. Requires:
1. Service account in `~/Thunderbird/credentials.json` (already exists)
2. Gmail API enabled in Google Cloud Console
3. Domain-wide delegation configured for `gmail.compose` scope
If delegation isn't set up, use the cloud Gmail connector on claude.ai instead.
