---
name: flight-price
description: "Multi-source flight price lookup: B2B wholesale via Centrav (Playwright scraper, no API key), consumer via Amadeus API, flight tracking via FlightAware and FlightRadar24, airline route-change monitoring, branded PDF quote generation, and Gmail draft with attachment. Triggers on: flight price, flight quote, airfare, book flights, flight options, flight search, how much to fly, fare quote, centrav, amadeus, B2B flights, wholesale airfare, flight cost, flight comparison, track flight, flight status, airline route change, airline cancel, flight monitor, flight watch, fare watch, run flight watch cycle"
---

# /flight-price — Flight Price Lookup (Centrav B2B + Consumer)

You execute this procedure yourself. This is NOT a handoff to Claude Code.
PII fence: never pass client names or booking refs to DeepSeek/external LLMs.
All $ figures require Harlan 6-step sign-off before any WF-17 gate.
Use /ask-opus only if multi-source results conflict and you need judgment on which price to quote.

## Usage

```
/flight-price [origin] [destination] [date] [passengers] [cabin]
/flight-price DEN FCO 2026-12-17 2 business
/flight-price — run fare watch cycle for all active watches
/flight-price track UA1234
```

---

## Step 1 — Determine Search Mode

| Request type | Method | Script/Function |
|---|---|---|
| Ad-hoc B2B quote (D2M clients) | Centrav Playwright scraper | `run_centrav_search()` |
| Ad-hoc consumer comparison | Amadeus API | `search_flights()` + `verify_flight_price()` |
| Active fare watches (batch) | Centrav watch cycle | `run_centrav_flight_watch_cycle()` |
| Flight tracking (en route) | FlightAware / FR24 | `track_flight_flightaware()` / `track_flight_fr24()` |
| Airline route change monitoring | RSS feed scraper | `run_airline_scan()` |

Default for D2M client flight quotes: **Centrav B2B first**. Centrav = wholesale net rates, not public prices. Always label output as "B2B wholesale" — never share net rates directly with clients.

---

## Step 2 — Centrav B2B Search (Primary for D2M quotes)

### Session check first

```python
import asyncio, sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_centrav_search import check_session_only

result = asyncio.run(check_session_only())
print(result)
# Returns: {valid, cookies_loaded, session_file_exists, checked_at}
```

If `valid: false` — re-authenticate before searching (see Step 2b).

### Run B2B search

```python
import asyncio, sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_centrav_search import run_centrav_search

result = asyncio.run(run_centrav_search(
    origin="DEN",            # IATA code, uppercase
    dest="FCO",              # IATA code, uppercase
    depart_date="2026-12-17",  # YYYY-MM-DD
    adults=2,                # number of travelers
    cabins=["economy", "premium", "business"],  # list — omit "first" unless requested
))
print(result)
```

Key output fields:
- `auth_status` — must be `"authenticated"` or all cabin results will be empty
- `results.economy.lowest_total` — net total for all adults
- `results.economy.lowest_pp` — net per-person
- `results.economy.airlines` — carrier names found
- `results.economy.screenshot` — PNG saved to `/home/john/Thunderbird/core/travel/data/`
- `results.economy.status` — `"ok"` | `"no_prices_found"` | `"error"`

Cabin values accepted: `"economy"` | `"premium"` | `"business"` | `"first"`

### Re-authenticate Centrav (if session expired)

```bash
# Headed browser — run on YOGA machine (requires display)
cd /home/john/Thunderbird
python3 scripts/centrav_flights.py --centrav-login --headless false

# Headless attempt (may hit CAPTCHA)
python3 scripts/centrav_flights.py --centrav-login
```

Session cookies saved to: `/home/john/Thunderbird/core/travel/data/centrav_session.json`
Credentials file: `/home/john/Thunderbird/centrav_credentials.json`
trustId expiry: check `creds/centrav_cookies.json` — re-login when ≤14 days remain.

---

## Step 3 — Consumer / Amadeus Search (sanity gate + client-facing comparison)

Amadeus returns public fares with D2M markup auto-applied. Use for:
- Sanity check against Centrav B2B (Centrav should be lower)
- Building client-facing option comparisons
- Round-trip searches (Centrav is one-way only)

```python
# Requires ~/Thunderbird/amadeus_credentials.json — {"client_id": "...", "client_secret": "..."}
# Test tier: 500 calls/month free. Production: switch base_url to https://api.amadeus.com

import asyncio, sys, json
sys.path.insert(0, '/home/john/Thunderbird/core/travel')

# Airport code lookup (if needed)
# search_airports(keyword="Denver") → returns IATA codes

# One-way search
# search_flights(
#     origin="DEN",
#     destination="FCO",
#     departure_date="2026-12-17",
#     return_date=None,          # omit for one-way
#     adults=2,
#     cabin_class="BUSINESS",    # ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST
#     nonstop_only=False,
#     max_results=10,
#     max_price=None,            # per-traveler USD ceiling
#     currency="USD",
# )
# Returns: {total_offers, offers: [{offer_id, itineraries, cabin_class, price: {net_usd, client_price_usd}, ...}]}

# Price verification before quoting:
# verify_flight_price(flight_offer_json=json.dumps(offer_object))
# Returns: {status: "verified", price: {net_usd, client_price_usd, fees}, last_ticketing_date, seats_remaining}

# Side-by-side comparison:
# compare_flights(offers_json=json.dumps([offer1, offer2, offer3]))
# Returns: {comparison: [{option, airline, route, departure, arrival, stops, cabin, net_price, client_price, badges}], recommendation: {best_price, fewest_stops}}
```

Markup constants (from script): economy/premium/first = 25%, business = 22%.
`client_price_usd` = what to quote clients. `net_usd` = D2M cost — never share with clients.

---

## Step 4 — Run Fare Watch Cycle (batch active watches)

```python
import asyncio, sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_centrav_search import run_centrav_flight_watch_cycle

result = asyncio.run(run_centrav_flight_watch_cycle())
print(result)
```

Reads active watches from: `/home/john/Thunderbird/core/travel/data/fare_watches.json`
Writes results to: `/home/john/Thunderbird/OpsCenter/fare_watches/last_check.json`

Output fields:
- `watches_total` — count of active flight-type watches
- `watches_checked` — count that returned a price
- `alerts` — list of `{watch_id, label, alert, price_pp}` for threshold breaches
- `warnings` — session expiry warnings, trustId days remaining
- `errors` — watches that failed (auth, route parse, no price)
- `results` — per-watch: `{status, origin, dest, date, cabin, passengers, lowest_pp, fare_check}`

Also runnable from CLI:
```bash
cd /home/john/Thunderbird
python3 core/travel/thunderbird_centrav_search.py --watch-cycle
```

---

## Step 5 — Flight Tracking (en route / day-of)

### FlightAware (detailed status, gate info, delays)

```python
# Requires ~/Thunderbird/flightaware_credentials.json — {"api_key": "..."}
# track_flight_flightaware(flight_id="UA1234")  # ICAO: UAL1234 or IATA: UA1234
# Returns: {flights: [{ident, status, origin, destination, departure/arrival times, gate, terminal, progress_percent}]}

# search_flights_flightaware(origin="KDEN", destination="KFCO", departure_date="2026-12-17")
# Returns: scheduled + en-route flights with status

# get_airport_info_flightaware(airport_code="DEN")
# Returns: {name, city, timezone, coordinates, delays}
```

### FlightRadar24 (live position, no API key needed)

```python
# track_flight_fr24(flight_number="UA1234")
# Returns: {live: [{lat, lon, alt, speed, heading, aircraft}], scheduled: [...]}

# get_airport_flights_fr24(airport_code="DEN")
# Returns: {arrivals: [...], departures: [...]} — live board
```

Use FlightAware for gate/delay detail. Use FR24 for live in-air position.

---

## Step 6 — Airline Route Change Monitor

```python
import asyncio, sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_airline_monitor import run_airline_scan, check_client_airport_impact

# Full scan with Telegram alert on client impacts:
result = asyncio.run(run_airline_scan(alert=True))

# Check-only (no alert):
result = asyncio.run(run_airline_scan(alert=False))

# Client impact assessment only (no scan):
impacts = check_client_airport_impact()
# Returns: [{severity: "CRITICAL"|"HIGH", client, airport, airline_match, title, url}]
```

RSS sources monitored: Simple Flying, Routes Online, The Points Guy, Cranky Flier
Tracked airlines: Southwest, United, Delta, American, Alaska, JetBlue, Frontier, Spirit
Severity:
- `CRITICAL` — airline AND client airport both mentioned
- `HIGH` — only airport matched

Also runnable from CLI:
```bash
python3 /home/john/Thunderbird/core/travel/thunderbird_airline_monitor.py
python3 /home/john/Thunderbird/core/travel/thunderbird_airline_monitor.py --check-only
```

Output saved to: `/home/john/Thunderbird/output/airline_scan_YYYYMMDD_HHMM.json`

---

## Step 7 — Branded PDF Quote (client-facing deliverable)

```python
# render_flight_quote_pdf(
#     client_name="Kyle Kuklinski",
#     origin_city="Richmond",
#     destination_city="Panama City",
#     departure_date="December 17, 2026",
#     return_date=None,          # None for one-way
#     travelers="2",
#     flights_json=json.dumps([
#         {
#             "option": 1,
#             "airline": "United Airlines",
#             "cabin": "Business",
#             "client_price": "$2,450.00",
#             "badges": ["BEST PRICE"],
#             "seats_remaining": 4,
#             "legs": [{"label": "Outbound", "segments": [
#                 {"dep_time": "07:15", "dep_airport": "RIC", "arr_time": "15:45",
#                  "arr_airport": "PTY", "duration": "8h 30m", "stops": 1, "flight_num": "UA2341"}
#             ]}]
#         }
#     ]),
#     comparison_json=None,
#     recommendation="Option 1 offers the best value for a business cabin on this route.",
#     notes=None,                # defaults to 24-hour validity notice
#     output_filename=None,      # defaults to ClientName_Origin_Destination_MonYYYY.pdf
# )
# Returns: {status, pdf_path, html_path, client_name, route, options_count}
# Output dir: /home/john/Thunderbird/output/
```

Template: `/home/john/Thunderbird/templates/flight_quote.html.j2`
Requires: `jinja2`, `weasyprint`

---

## Step 8 — Gmail Draft with Quote Attachment

WF-17 rule: Draft ONLY to d2mconcierge. Commander sends. Never Wing.

```python
# email_flight_quote(
#     to_email="client@example.com",
#     client_name="Kyle Kuklinski",
#     origin_city="Richmond",
#     destination_city="Panama City",
#     departure_date="December 17, 2026",
#     return_date=None,
#     summary_json=json.dumps([
#         {"option": 1, "airline": "United", "departure": "07:15 RIC",
#          "arrival": "15:45 PTY", "stops": 1, "cabin": "Business", "client_price": "$2,450.00"}
#     ]),
#     recommendation="Option 1 is our recommendation.",
#     pdf_path="/home/john/Thunderbird/output/Kuklinski_Richmond_PanamaCity_Dec2026.pdf",
#     subject=None,   # defaults to "Your Flight Options: Richmond to Panama City"
# )
# Returns: {status: "draft_created", draft_id, to, subject, has_pdf_attachment}
```

Gmail draft account: `d2mconcierge` (service account delegation — auto-handled).
After draft created: notify Commander. Stop there.

---

## Harlan 6-Step Sign-Off (required before any $ figure reaches WF-17)

Any flight quote containing a dollar figure must clear Harlan verification:

1. Net cost confirmed from Centrav result (`lowest_total`) or verified Amadeus price (`grandTotal`)
2. Per-person breakdown confirmed (`lowest_pp` or verified `grandTotal / adults`)
3. Compare net vs any prior quote in dossier — flag any delta
4. Root cause or unresolved flag if delta exists
5. Markup correctly applied (25% standard / 22% business) for client price
6. Harlan sign-off: "Confirmed: $X net ($Y/pp) as of [date], source: Centrav/Amadeus verified"

---

## Quality Checklist

- [ ] Centrav session valid before search (`valid: true` from `check_session_only()`)
- [ ] Price extracted (`lowest_pp` not null) — if null, re-check screenshot for CAPTCHA
- [ ] Auth status confirmed `"authenticated"` in Centrav result
- [ ] Net prices labeled as B2B/internal — not exposed to client
- [ ] If $ figure in any client output: Harlan 6-step complete
- [ ] trustId expiry checked — warn Commander if ≤14 days
- [ ] If PDF quote: verify PDF renders at `/home/john/Thunderbird/output/`
- [ ] If email draft: created in d2mconcierge ONLY — never johnloucks3
- [ ] Commander notified of draft location — Wing stops at WF-17

---

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| `auth_status: "session_expired"` | Run `python3 scripts/centrav_flights.py --centrav-login --headless false` on YOGA |
| CAPTCHA blocking auto-login | Headed browser required — cannot headless past reCAPTCHA |
| `lowest_pp: null` on a cabin | Centrav may have returned no fares for that date/route — check screenshot in `core/travel/data/` |
| Amadeus `config_error` | Create `~/Thunderbird/amadeus_credentials.json` with `client_id` + `client_secret` |
| Amadeus 401 | Token refresh failed — check credentials file, verify Amadeus app is active |
| `playwright_missing` error | `pip install playwright && playwright install chromium` |
| FlightAware 403 | AeroAPI key expired or rate-limited — check `flightaware_credentials.json` |
| FR24 `fr24_error` | `pip install FlightRadarAPI` — unofficial lib may need update |
| PDF render error | `pip install jinja2 weasyprint` — also check template exists at `templates/flight_quote.html.j2` |
| Watch cycle `route_parse_error` | Fix `route` field in `fare_watches.json` — must contain 2 valid IATA codes (e.g. `"DEN → FCO"`) |
| `no_flight_watches` on watch cycle | No active watches with `watch_type: "flight"` in `fare_watches.json` |
| trustId warning in watch cycle | Re-login at centrav.com before trustId expires — check `creds/centrav_cookies.json` expiry |

---

## File Reference

| File | Purpose |
|---|---|
| `/home/john/Thunderbird/core/travel/thunderbird_centrav_search.py` | Centrav B2B scraper — `run_centrav_search()`, `check_session_only()`, `run_centrav_flight_watch_cycle()` |
| `/home/john/Thunderbird/core/travel/thunderbird_flight_search.py` | Amadeus API — `search_flights()`, `verify_flight_price()`, `compare_flights()`, `render_flight_quote_pdf()`, `email_flight_quote()` |
| `/home/john/Thunderbird/core/travel/thunderbird_airline_monitor.py` | Route change monitor — `run_airline_scan()`, `check_client_airport_impact()` |
| `/home/john/Thunderbird/core/travel/data/centrav_session.json` | Playwright session cookies (auto-refreshed) |
| `/home/john/Thunderbird/core/travel/data/fare_watches.json` | Active fare watch definitions |
| `/home/john/Thunderbird/OpsCenter/fare_watches/last_check.json` | Last watch cycle results |
| `/home/john/Thunderbird/centrav_credentials.json` | Centrav email/password |
| `/home/john/Thunderbird/creds/centrav_cookies.json` | Alt cookie source — check trustId expiry |
| `/home/john/Thunderbird/amadeus_credentials.json` | Amadeus client_id + client_secret |
| `/home/john/Thunderbird/flightaware_credentials.json` | FlightAware AeroAPI key |
| `/home/john/Thunderbird/scripts/centrav_flights.py` | CLI re-auth script — use for headed browser login |
| `/home/john/Thunderbird/templates/flight_quote.html.j2` | Jinja2 template for PDF quotes |
| `/home/john/Thunderbird/output/` | All generated PDFs and scan output |
