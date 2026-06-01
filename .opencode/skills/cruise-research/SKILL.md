---
name: cruise-research
description: "Cruise research procedure: RSSC agent portal scraping, cruise intel pipeline (10-source luxury market scan), fare watch management, and pricing output. Triggers on: cruise research, rssc scrape, rssc portal, scrape bookings, fare watch, cruise pricing, luxury cruise intel, cruise pipeline, shore excursions, booking detail, cruise rates, silversea pricing, regent pricing, cruise availability, T2 cruise scan, cruise intel, watch cruise price, add fare watch, check fare, price history"
---

# /cruise-research — RSSC Scraping, Cruise Intel Pipeline, Fare Watch

You execute this procedure yourself. This is NOT a handoff to Claude Code.
PII fence is active — never send client names, booking refs, or payment details to DeepSeek/external LLMs.
Use /ask-opus only if strategic judgment is needed on pricing or routing decisions.

## Usage

```
/cruise-research rssc [booking-id]          # Scrape RSSC agent portal (targeted or full)
/cruise-research intel [year] [months]      # Run luxury cruise intel pipeline
/cruise-research fare-watch [subcommand]    # Manage fare watches
/cruise-research report                     # Summarize latest scan outputs
```

---

## Step 1 — Assess: What Is Being Requested?

Before running any script, classify the task:

| Request type | Script to run |
|---|---|
| Existing booking detail (excursions, payments, shore credits) | `rssc_targeted_scrape.py` |
| Full RSSC portal scrape (suites, deck plans, sailings, images) | `rssc_full_scrape.py` |
| Luxury market scan for prospect clients | `cruise_intel/run_pipeline.py` |
| Add / update / check a fare watch | `thunderbird_fare_watch.py` functions directly |
| Run Centrav flight watch cycle | `scripts/fare_watch_centrav.py` |
| Review last scan results | Read `OpsCenter/scan_outputs/` and `core/travel/data/` |

**Chrome debug port prerequisite (RSSC scrapes only):** Both RSSC scripts require Chrome CDP on port 9222. Check first:
```bash
curl -s http://localhost:9222/json/version | python3 -m json.tool | grep -i "browser"
```
If port 9222 is OFFLINE — RSSC scrapes cannot run. Report to Commander: "Chrome CDP offline. RSSC scrape blocked."

---

## Step 2 — RSSC Targeted Scrape (booking detail + excursions)

Use this for existing bookings: payment status, shore excursion summary, shipboard credits, to-do list.

```bash
cd /home/john/Thunderbird
python3 scripts/rssc_targeted_scrape.py
```

**What it does:**
- `extract_booking_full_detail(page, booking_id, url)` — deep extraction from booking page: cruise details, guest details, suite details, to-do list, payments, shore excursion summary by port, beverages, hotel packages, shipboard credits, culinary arts. Returns `fullPageText` + structured JSON.
- `extract_sailings_with_prices(page)` — scrapes `rssc.com/agent/cruises` for all sailing cards + prices. Scrolls 3x to load lazy content.
- `scrape_ship_via_agent_portal(page, ship_slug)` — ship detail via agent portal for `splendor` or `grandeur`. Follows suite/deck sub-links.
- `download_images(page, image_list, prefix)` — downloads up to 25 brochure images per prefix, skips tracking/pixel URLs, deduplicates.

**Current hardcoded bookings in BOOKINGS dict:**
```python
BOOKINGS = {
    "3096289_Ely":     "...",   # Ely-Darrow/Furlow/Nichols Grandeur Scandinavia
    "3078056_Nichols": "...",
    "3071222_Furlow":  "...",
    "2984034_McLeod":  "...",   # McLeod Silver Muse
}
```

**Output directory:** `~/Thunderbird/validations/rssc_scrape/`
Output file: `rssc_targeted_YYYYMMDD_HHMMSS.json`
Screenshots: `rssc_scrape/[booking_id]_detail_full.png`
Images: `rssc_scrape/images/[slug]_NNN.jpg`

**Extract from output — what to look for:**
- `data["payments"]` — payment section text with balances and FPDs
- `data["shoreExcursions"]["summary"]` — table rows: port, excursion name, status, price
- `data["shipboardCredits"]` — credit amounts and descriptions
- `data["todoList"]` — outstanding actions on the booking
- `data["culinaryArts"]` — kitchen class availability/status
- `data["fullPageText"]` — 15K-char catch-all if structured fields are empty

---

## Step 3 — RSSC Full Scrape (suites, deck plans, public ship pages, images)

Use this when building itineraries or validating ship content for brochures.

```bash
cd /home/john/Thunderbird
python3 scripts/rssc_full_scrape.py
```

**What it does:**
- `scrape_excursions(page, booking_id, booking_url)` — finds excursion links + CUSTOMIZE tab on booking detail page. Screenshot: `[booking_id]_excursions.png`
- `scrape_sailings_rates(page)` — navigates to `rssc.com/agent/cruises` and `rssc.com/cruises`. Extracts sailing cards, filters, prices.
- `scrape_ship_suites(page, ship_name)` — tries 7 URL patterns for ship suite/deck-plan pages. Collects suite text, images, deck plan images, links.
- `download_images(page, image_urls, prefix)` — downloads up to 30 images per ship, caps per call. Saves to `OUTPUT_DIR/images/`.

**Target ships:** `Seven Seas Splendor`, `Seven Seas Grandeur`
**Sub-pages scraped:** suites, dining, deck-plans, onboard, gallery

**Output directory:** `~/Thunderbird/validations/rssc_scrape/`
Output file: `rssc_full_scrape_YYYYMMDD_HHMMSS.json`
Images: `rssc_scrape/images/[ship_slug]_NN.jpg`

**After full scrape — quality check:**
- [ ] `all_results["ships"]["splendor"]["pages"]` has at least 1 URL with images
- [ ] `all_results["ships"]["grandeur"]["pages"]` has at least 1 URL with images
- [ ] `all_results["sailings"]["sailings_page"]["prices"]` has price strings
- [ ] Images downloaded to `rssc_scrape/images/` — count should be > 10

---

## Step 4 — Luxury Cruise Intel Pipeline (10-source market scan)

Use this for T2 exercises, prospect research, and market awareness. Scans deluxecruises, Perx, OAT, Ponant, HX, SeaDream, Explora, CruiseMapper, CruisesOnly, CruisePlum.

```bash
cd /home/john/Thunderbird/scripts/cruise_intel
# Full run (Oct/Nov 2026, all sources):
python3 run_pipeline.py

# Targeted year/months:
python3 run_pipeline.py --year 2027 --months 6 7 8 --tag 2027-summer

# South Pacific / APAC scope (per Commander re-scope 2026-05-31):
python3 run_pipeline.py --year 2028 --months 5 6 --tag may-june-2028-spac --spac --skip-oat --skip-ponant

# Build-only (no scraping, reassemble from cached JSONs):
python3 run_pipeline.py --build-only

# Skip slow browser scrapers (use cached):
python3 run_pipeline.py --skip-oat --skip-ponant --skip-seadream --skip-cruiseplum

# Merge two period outputs:
python3 merge_periods.py output/T2_MASTER_2026-full.csv output/T2_MASTER_2027-h1.csv
```

**Pipeline function signature:**
```python
run_pipeline(
    year: int,
    months: list,               # e.g. [10, 11]
    tag: str = '',              # output suffix: T2_MASTER_[tag].csv
    skip_perx: bool = False,
    skip_oat: bool = False,
    skip_ponant: bool = False,
    skip_hx: bool = False,
    skip_seadream: bool = False,
    skip_explora: bool = False,
    skip_cruisemapper: bool = False,
    skip_cruisesonly: bool = False,
    skip_cruiseplum: bool = False,
    build_only: bool = False,
    verbose: bool = False,
    cruiseplum_user: str = '',
    cruiseplum_pass: str = '',
)
```

**Output:** `scripts/cruise_intel/output/T2_MASTER_[tag].csv`
Default: `scripts/cruise_intel/output/T2_MASTER.csv`
Stats: `scripts/cruise_intel/output/T2_STATS.json`

**CruisePlum credentials (if needed):**
```bash
# Check credentials file:
cat ~/.config/d2m/cruiseplum.env
# Or pass via env: CRUISEPLUM_USER=... CRUISEPLUM_PASS=...
```

**After pipeline — summarize output:**
```bash
python3 -c "
import csv
with open('/home/john/Thunderbird/scripts/cruise_intel/output/T2_MASTER.csv') as f:
    rows = list(csv.DictReader(f))
print(f'Total rows: {len(rows)}')
# Show sources
from collections import Counter
srcs = Counter(r.get('source','?') for r in rows)
for s,n in srcs.most_common(): print(f'  {s}: {n}')
"
```

---

## Step 5 — Fare Watch Management

The fare watch system tracks cruise and flight prices over time, alerts on drops/spikes.

**Data files:**
- Watches: `~/Thunderbird/core/travel/data/fare_watches.json`
- History: `~/Thunderbird/core/travel/data/fare_history.json`

```python
import sys; sys.path.insert(0, '/home/john/Thunderbird')
from core.travel.thunderbird_fare_watch import (
    add_watch, check_fare, list_watches, remove_watch, get_fare_history
)
```

### List active watches:
```python
result = list_watches(active_only=True)
# Returns: {"status": "success", "count": N, "watches": [{id, label, type, provider, travel_date, price_pp, total, vs_baseline, last_checked}]}
```

### Add a watch:
```python
result = add_watch(
    watch_id="lyons-splendor-ath-ny-cruise",     # unique slug
    watch_type="cruise",                           # "flight", "cruise", or "hotel"
    label="Lyons — Splendor Athens→NY Sep 2026",
    provider="Regent Seven Seas",
    route="Athens (Piraeus) → New York (26-night)",
    travel_date="2026-09-06",
    current_price_pp=18995.0,
    passengers=2,
    alert_below=16000.0,      # trigger alert if drops below
    alert_above=22000.0,      # trigger alert if rises above
    notes="Suite category: Deluxe Suite. Included: unlimited flights, excursions, dining.",
)
# Returns: {"status": "created", "watch_id": "...", "label": "...", "price_pp": "$18,995", "total": "$37,990"}
```

### Record a price check:
```python
result = check_fare(
    watch_id="lyons-splendor-ath-ny-cruise",
    new_price_pp=17500.0,   # current observed price
)
# Returns: {"status": "checked", "price_pp": "$17,500", "total": "$35,000", "change_from_baseline": "-7.9%", "change_from_last": "$-1,495/pp (down)", "direction": "down", "alert": "PRICE DROP: ..."}
```

### Get price history:
```python
result = get_fare_history(
    watch_id="lyons-splendor-ath-ny-cruise",
    limit=30,    # max entries
)
# Returns: {"summary": {"min": "$X", "max": "$X", "avg": "$X", "data_points": N}, "history": [{date, price_pp, total, change, alert}]}
```

### Deactivate a watch:
```python
result = remove_watch(watch_id="...", hard_delete=False)  # soft deactivate
result = remove_watch(watch_id="...", hard_delete=True)   # permanent delete
```

### Run Centrav flight watch cycle (automated):
```bash
cd /home/john/Thunderbird
python3 scripts/fare_watch_centrav.py
# Checks all flight-type fare watches against Centrav B2B pricing.
# Outputs JSON summary to OpsCenter/fare_watches/last_check.json
# Auth required: if expired → run login first:
python3 scripts/centrav_flights.py --centrav-login --headless false
```

### Check Centrav last run:
```bash
cat /home/john/Thunderbird/OpsCenter/fare_watches/last_check.json
# Key fields: watches_total, watches_checked, alerts, warnings, errors
```

---

## Step 6 — One-Off Centrav Flight Price Lookup

For ad-hoc flight pricing (not a watch, just a quote):

```bash
cd /home/john/Thunderbird
python3 scripts/centrav_flights.py \
  --origin RIC --dest PTY \
  --date 2026-12-17 \
  --travelers 4 \
  --cabin economy \
  --output /home/john/Thunderbird/core/travel/data/airline_test_RIC_PTY_2026-12-17.json

# Cabin options: economy | premium | business
# Headless default: true (set --headless false for interactive CAPTCHA)
```

**If Centrav auth fails:**
```bash
# Re-authenticate interactively:
python3 scripts/centrav_flights.py --centrav-login --headless false
# Session saved to: ~/Thunderbird/core/travel/data/centrav_session.json
```

---

## Step 7 — Pricing Output for Staff / WF-17

After gathering pricing data:

**Format for Harlan 6-step sign-off (any $ figure going into a client email):**
1. Source: portal / TESS / fare_watches.json — state which
2. FPD confirmed from portal (not from watch data alone)
3. Compare watch baseline vs dossier figure — flag any delta
4. Root cause if delta > 2%
5. Credits and perks verified (included flights, excursions, OBC)
6. Harlan sign-off: "Confirmed: $X/pp ($Y total, N pax) as of [date], source: [fare_watches.json / portal]"

**Negative-Space Rule applies:** If a price cannot be confirmed from a primary source, it does not appear in a client email. Silence is correct when status is unknown.

**Pipeline output summary (for staff memo):**
```bash
python3 -c "
import json
from pathlib import Path
# Last Centrav check:
last = json.loads(Path('/home/john/Thunderbird/OpsCenter/fare_watches/last_check.json').read_text())
print('Centrav last check:', last['completed_at'][:16])
print('Watches total:', last['watches_total'])
print('Alerts:', last['alerts'])
print('Warnings:', [w[:80] for w in last['warnings']])
"
```

---

## Step 8 — Quality Checklist

Before surfacing any cruise research output to Commander:

- [ ] Chrome CDP port 9222 status confirmed (for RSSC scrapes)
- [ ] Output JSON saved to correct directory (not temp)
- [ ] Pricing data tagged CONFIRMED / INFERRED / UNKNOWN per SO-PIPELINE-INTEGRITY-20260528
- [ ] Any $ figures intended for client email have Harlan 6-step sign-off
- [ ] PII (client names, booking refs) NOT passed to DeepSeek/external LLMs
- [ ] Alert triggers reviewed — if alert fired, flag to Commander immediately
- [ ] If Centrav auth expired — flag before Commander expects flight pricing
- [ ] RSSC booking detail screenshots saved for audit trail

---

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| `ConnectionRefusedError: [Errno 111]` on CDP | Chrome CDP offline. Start debug Chrome or flag to Commander. Cannot run RSSC scrapes. |
| `centrav: session expired — attempting auto-login` | Run `python3 scripts/centrav_flights.py --centrav-login --headless false` to re-authenticate |
| `Watch 'X' not found` on `check_fare` | Watch ID does not exist. Run `list_watches()` to see actual IDs. |
| Pipeline hangs on gstack sources | Add `--skip-oat --skip-ponant --skip-seadream` to use cached JSONs |
| `T2_MASTER.csv` missing after `--build-only` | One or more source JSONs missing. Run without `--build-only` or check `cruise_intel/output/` for existing JSONs. |
| CruisePlum login fails | Set credentials in `~/.config/d2m/cruiseplum.env` as `USER=email` / `PASS=password`, then add `--skip-cruiseplum` to run without it |
| RSSC scrape returns empty booking data | Session may have expired. Navigate manually in Chrome CDP browser to verify login, then re-run. |
| Fare watch JSON malformed on read | `_load_watches()` returns `{}` on parse error. Check `fare_watches.json` with `python3 -m json.tool core/travel/data/fare_watches.json` |
| Images not downloading | `download_images()` skips images < 1KB and tracking URLs. Check that Chrome CDP is live and target URLs are accessible. |

---

*Then: `/email-draft` if pricing output feeds a lifecycle touchpoint or client proposal.*
