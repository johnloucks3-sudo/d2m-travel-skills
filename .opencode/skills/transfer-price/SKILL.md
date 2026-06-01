---
name: transfer-price
description: "Airport and port ground transfer pricing via Kiwitaxi Playwright scraper, with Welcome Pickups as secondary source. Returns per-vehicle prices, pax capacity, vehicle class options, and D2M 25% markup quote. Triggers on: transfer price, ground transfer, airport transfer, port transfer, taxi quote, transfer quote, transfer cost, hotel transfer, cruise port transfer, kiwitaxi, arrival transfer, departure transfer, transfer from airport, transfer to port"
---

# /transfer-price — Ground Transfer Price Lookup

You execute this procedure yourself. This is not a handoff — OC runs the scraper directly.
Use /ask-opus only if a pricing decision requires judgment beyond straight lookup (e.g., conflicting sources, client with unusual group size).

## Usage

```bash
# Pre-mapped route (fastest — static URL, no form-fill needed)
python3 /home/john/Thunderbird/scripts/test_transfer_scrapers.py --route LIS-LISBON --date 2026-09-05 --pax 2

# Custom route (form-fill mode — slower, may require fallback)
python3 /home/john/Thunderbird/scripts/test_transfer_scrapers.py --from "Athens Airport" --to "Piraeus Port" --date 2026-09-05 --pax 4

# List all pre-mapped routes
python3 /home/john/Thunderbird/scripts/test_transfer_scrapers.py --list-routes

# Both sources at once (kiwitaxi + welcomepickups)
python3 /home/john/Thunderbird/scripts/test_transfer_scrapers.py --route ATH-PIRAEUS --date 2026-09-05 --source all
```

**Default source:** `kiwitaxi` (confirmed accessible, static URLs, all vehicle classes, fixed per-vehicle pricing)
**Date format:** YYYY-MM-DD
**Pax default:** 2 — always match actual client group size

---

## Pre-Mapped Route Keys

| Key | Description |
|---|---|
| `LIS-LISBON` | Lisbon Airport → Lisbon city |
| `LISBON-LIS` | Lisbon city → Lisbon Airport |
| `LIS-SINTRA` | Lisbon Airport → Sintra |
| `BCN-BCN_PORT` | Barcelona Airport → Barcelona Port |
| `BCN_PORT-BCN` | Barcelona Port → Barcelona Airport |
| `BCN-CITY` | Barcelona Airport → Barcelona city |
| `FCO-ROME` | Rome Airport (FCO) → Rome city |
| `FCO-CIVITA` | Rome Airport → Civitavecchia Port |
| `CIVITA-FCO` | Civitavecchia Port → Rome Airport |
| `CIVITA-ROME` | Civitavecchia Port → Rome city |
| `ATH-PIRAEUS` | Athens Airport → Piraeus Port |
| `PIRAEUS-ATH` | Piraeus Port → Athens Airport |
| `ATH-ATHENS` | Athens Airport → Athens city |
| `NCE-NICE` | Nice Airport → Nice city |
| `NCE-CANNES` | Nice Airport → Cannes |
| `BGO-BERGEN` | Bergen Airport → Bergen city |
| `KEF-REYKJAVIK` | Keflavik Airport → Reykjavik |
| `POS-PORT` | POS Airport → Port of Spain |
| `HNL-WAIKIKI` | Honolulu Airport → Waikiki |
| `CUN-CANCUN` | Cancun Airport → Cancun Hotel Zone |

If the client's route is not in this table, use `--from` / `--to` form-fill mode.
If form-fill fails → see Common Issues below for adding a new route.

---

## Step 1 — Run the Scraper

```bash
cd /home/john/Thunderbird
python3 scripts/test_transfer_scrapers.py --route [KEY] --date [YYYY-MM-DD] --pax [N]
```

- Match `--pax` to the actual number of travelers in the booking
- Use the client's departure or arrival date for `--date`
- Output JSON saved to: `core/travel/data/transfer_test_{ROUTE}_{DATE}.json`
- Screenshots saved to: `core/travel/data/transfer_kiwitaxi_{route}_{date}.png`

---

## Step 2 — Read and Parse Output

```python
import json
from pathlib import Path

route = "LIS-LISBON"
date_str = "2026-09-05"
out_file = Path(f"/home/john/Thunderbird/core/travel/data/transfer_test_{route}_{date_str}.json")
data = json.loads(out_file.read_text())

kw = data.get("kiwitaxi", {})
print(f"Status: {kw['status']}")
print(f"Duration: {kw.get('duration_min')} min")
for t in kw.get("transfers", []):
    print(f"  {t['vehicle_class']:<22} {t['pax_capacity']} pax  ${t['price_usd']}/vehicle")
```

**Result fields per vehicle option:**
- `vehicle_class` — name (e.g., "Comfort", "Business", "Minibus 7PAX")
- `price_usd` — fixed per-vehicle price (NOT per person)
- `pax_capacity` — max passengers for this vehicle
- `bags_capacity` — max bags
- `vehicle_examples` — example makes/models (Toyota Camry, Mercedes E-class, etc.)
- `badge` — "Best Choice" if flagged by Kiwitaxi, else null
- `duration_min` — estimated trip duration in minutes (top-level in kiwitaxi result)

**Key data note:** Kiwitaxi prices are per vehicle, not per person. Fixed regardless of date.

---

## Step 3 — Build the Client Quote

Standard D2M markup is **25%** on net transfer price.

```python
import json
from pathlib import Path

route = "LIS-LISBON"
date_str = "2026-09-05"
pax = 2

data = json.loads(Path(f"/home/john/Thunderbird/core/travel/data/transfer_test_{route}_{date_str}.json").read_text())
transfers = data["kiwitaxi"].get("transfers", [])
duration = data["kiwitaxi"].get("duration_min")

# Find best option for pax count
eligible = [t for t in transfers if t.get("pax_capacity") and t["pax_capacity"] >= pax]
if eligible:
    best = eligible[0]  # sorted by price ascending
    net = best["price_usd"]
    client_price = round(net * 1.25)
    print(f"Recommended: {best['vehicle_class']} ({best['pax_capacity']} pax)")
    print(f"  Net: ${net}  |  Client quote: ${client_price}  |  Duration: ~{duration} min")
```

**Quote format for client communications:**
```
Ground Transfer: [From] → [To]
Vehicle: [Vehicle Class] (up to [N] passengers)
Duration: approximately [X] minutes
Price: $[CLIENT_PRICE] per vehicle
Cancellation: Free cancellation (Kiwitaxi standard)
```

---

## Step 4 — Harlan Sign-Off (required before any $ figure goes to client)

Any dollar figure in a client email requires Harlan's 6-step verification before WF-17:

1. Confirm net price from scraper output (primary source: `transfer_test_*.json`)
2. Confirm pax eligibility (vehicle capacity >= client group size)
3. Compare vs any prior quote in dossier — flag delta if present
4. Root-cause any discrepancy or note "first quote, no prior record"
5. Verify markup applied: net × 1.25 = client price (spot-check arithmetic)
6. Sign-off: "Confirmed: $[CLIENT_PRICE] as of [date], source: kiwitaxi scraper [route] [date]"

---

## Step 5 — WF-17 Gate

Transfer quotes destined for client emails go through WF-17. Do not send directly.

```python
# Create draft in d2mconcierge — auto-labels THUNDERBIRD-Commander-Review
import sys; sys.path.insert(0, '/home/john/Thunderbird')
from core.email.thunderbird_gmail import gmail_create_draft_sync

result = gmail_create_draft_sync(
    to="client@email.com",
    subject="Your Ground Transfer Options — [City]",
    body=html_body,
    persona_id="CONCIERGE"   # always CONCIERGE — uses d2mconcierge
)
print(result)
```

Notify Commander: "Transfer quote for [client] staged in d2mconcierge. [Route], [pax] pax, $[CLIENT_PRICE]. Awaiting your review."

**Account routing:**
| Product type | Account | Label |
|---|---|---|
| Client transfer quote | d2mconcierge | THUNDERBIRD-Commander-Review |
| Internal brief / research | d2mconcierge → full send to johnloucks3 | none |

---

## Adding a New Route

If a needed route is not in the pre-map:

1. Visit kiwitaxi.com and search the route manually
2. Copy the result URL — pattern: `kiwitaxi.com/en/{country}/{from-slug}-{to-slug}`
3. Add to `KIWITAXI_ROUTES` dict in `/home/john/Thunderbird/scripts/test_transfer_scrapers.py`:

```python
"KEY":  ("Description",  "https://kiwitaxi.com/en/country/from-slug-to-slug"),
```

4. Re-run with the new key to verify extraction works
5. Commit the updated route map

---

## Source Reference

| Source | File | Status | Best for |
|---|---|---|---|
| Kiwitaxi | `scripts/test_transfer_scrapers.py` | Confirmed accessible | All pre-mapped routes, static URL, per-vehicle fixed price |
| Welcome Pickups | `scripts/test_transfer_scrapers.py --source welcomepickups` | Form-fill, partial | European cruise ports, premium tier |
| Welcome Pickups API | `core/travel/thunderbird_transfers.py` → `search_welcome_pickups()` | Requires API key | Mediterranean/European partner API |
| Mozio API | `core/travel/thunderbird_transfers.py` → `search_mozio_transfers()` | Requires API key | Global aggregator, US airports |
| Blacklane API | `core/travel/thunderbird_transfers.py` → `search_blacklane_transfers()` | Requires API key | Luxury chauffeur worldwide |

**API availability check:**
```bash
ls /home/john/Thunderbird/welcome_pickups_credentials.json 2>/dev/null && echo "WP: configured" || echo "WP: no credentials"
ls /home/john/Thunderbird/mozio_credentials.json 2>/dev/null && echo "Mozio: configured" || echo "Mozio: no credentials"
ls /home/john/Thunderbird/blacklane_credentials.json 2>/dev/null && echo "Blacklane: configured" || echo "Blacklane: no credentials"
```

---

## PII Fence

Never send client names, booking references, or payment data to DeepSeek or any external LLM.
Transfer price lookups contain no PII — route, date, pax count only. Safe for all models.

---

## Quality Checklist

- [ ] Correct pax count matches client group size
- [ ] Route matches client's actual port/airport (not generic city)
- [ ] Kiwitaxi scraper returned status `ok` (not `route_not_found` or `bot_blocked`)
- [ ] Vehicle class capacity >= pax count
- [ ] Net price extracted from JSON, not estimated
- [ ] D2M markup applied: net × 1.25 = client price
- [ ] Duration noted for client context
- [ ] Harlan 6-step sign-off complete if $ in client email
- [ ] Draft in d2mconcierge, labeled THUNDERBIRD-Commander-Review
- [ ] Commander notified — Wing does not send

---

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| `status: route_not_found` | URL slug changed — search kiwitaxi.com manually, update `KIWITAXI_ROUTES` with new slug |
| `status: bot_blocked` | Rare on Kiwitaxi. Try once more; if persistent, use Welcome Pickups form-fill as fallback |
| `status: no_results` | Cards not rendered — increase `asyncio.sleep(4)` to `asyncio.sleep(8)` in `scrape_kiwitaxi_url()` |
| Form-fill mode fails at autocomplete | Route not autocomplete-matchable — add to pre-map via static URL instead |
| Welcome Pickups returns `ambiguous` | Normal for WP scraper — it reached the site but vehicle selectors didn't match. Manual check the screenshot at `core/travel/data/transfer_welcomepickups_{date}.png` |
| Playwright not installed | `pip install playwright && python3 -m playwright install chromium` |
| Output JSON missing | Check `core/travel/data/` directory exists: `mkdir -p /home/john/Thunderbird/core/travel/data` |
| Price is `null` | JS extractor found no `$N` price pattern — screenshot the page and check card structure changed on kiwitaxi.com |
| Mozio/Blacklane/WP API returns `credentials_required` | Create credentials file per instructions in `core/travel/thunderbird_transfers.py` header |

---

*Then: If transfer quote is part of an itinerary → feed into `/itinerary` or `/email-draft` as a line item.*
