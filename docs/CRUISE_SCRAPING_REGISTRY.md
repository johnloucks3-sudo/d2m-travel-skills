# CRUISE SCRAPING REGISTRY — Canonical Runbooks
*Owner: Dembe (A2) · Updated: 2026-06-26 · Commander directive: "Remember and pass to Dembe for nightly searches"*

---

## ACTIVE SCRAPERS

### 1. CruiseMapper
**Script:** `scripts/run_cruisemapper_live.py`
**Output:** `intel/cruisemapper_live.json`
**Auth:** None — public site, no cookies required
**Pattern:** Paginates by ship ID. Ship list at `https://cruisemapper.com/vessels?type=cruise`
**Volume:** ~12,000 sailings (Regent, Silversea, Crystal, Oceania, Cunard + many expedition lines)
**Anti-bot:** Low risk. Rate limit: 1 req/2s safe. No CAPTCHA observed.
**Lines covered:** Hurtigruten, Emerald, Scenic, Celestyal, Azamara, Aurora, HX, Hapag-Lloyd, Fred. Olsen, Saga, Star Clippers, Quark + all luxury lines
**Run cadence:** Monthly (cruise-db-refresh.timer, 1st of month)
**Command:**
```bash
python3 scripts/run_cruisemapper_live.py
```

---

### 2. DeluxeCruises
**Script:** `scripts/run_deluxecruises_live.py`
**Output:** `intel/deluxecruises_live.json`
**Auth:** Session cookies — `_ga`, `_gid`, `chatbase_anon_id`. NO reCAPTCHA. NOT auth-gated.
**Pattern:** Homepage at `https://www.deluxecruises.com/` → collect `/{line}/{ship}/cruises-{year}/calendar.htm` links → parse each calendar table
**Volume:** ~2,000 sailings
**Lines covered:** Silversea, Regent, Cunard, Oceania, Crystal, Paul Gauguin, SeaDream, Ritz-Carlton, Four Seasons, PONANT, Windstar, Lindblad
**SKIP_LINES:** Currently `set()` — all lines included per Commander directive 2026-06-26
**Anti-bot:** Low. Standard GA cookies only. `time.sleep(0.5)` polite delay between pages.
**Run cadence:** Monthly (cruise-db-refresh.timer)
**Cookie refresh:** Grab from browser → update `COOKIES` dict in script header
**Command:**
```bash
python3 scripts/run_deluxecruises_live.py
```

---

### 3. VTG (VacationsToGo) — Ticker API
**Script:** `scripts/parse_vtg_ticker.py` (or inline in builder)
**Output:** `intel/vtg_structured_20260626.txt` (FastDeals text), `intel/oceania_vtg_20260626.json`, `intel/crystal_vtg_20260626.json`
**Auth:** SESSION cookies — browser-export required each session. Cookies expire on browser close.
**Ticker URL pattern:**
```
https://www.vacationstogo.com/ticker.cfm?l={LINE_ID}&r=0&mPct=40&jpw=50&source=cruisemm&csp=L7gL7g&nr=cus_L7g&mmz=1
```
**Known Line IDs:**
| ID | Line |
|---|---|
| 47 | Oceania |
| 13 | Crystal Cruises |
| 29 | Viking Ocean (JS-rendered — Playwright required) |
| 18 | Regent Seven Seas Cruises |
| 20 | Silversea Cruises |
| 35 | Atlas Ocean Voyages |

**Line ID discovery:** Browse `https://www.vacationstogo.com/cruise_lines/` → click line → note `l=NN` in URL
**Volume:** 2,272 FastDeal records (luxury lines) + 1,090 Oceania + 116 Crystal
**Anti-bot:** Medium. VTG uses session cookies tied to browser. Sessions last one browse session.
**Price data:** YES — VTG includes `price_disc` (discounted) and `price_orig` (original). These are interline/TA rates NOT for public display. For internal pipeline tracking only.
**Command:**
```bash
# Oceania:
python3 -c "from scripts.parse_vtg import fetch_vtg; fetch_vtg(line_id=47, out='intel/oceania_vtg_new.json')"
# After getting fresh cookies from Commander's browser
```

---

### 4a. Perx (Cruise Competition Intelligence — Fare Watch)
**Script:** `scripts/perx_intel_monitor.py`
**Output:** `data/perx_intel_history.json`, `data/perx_eod_queue.json`
**Auth:** Django `sessionid` cookie (~30-day expiry) + `csrftoken`
**Cookie file:** `creds/perx_cookies.json` — GITIGNORED
**API status:** `sail-personalize` endpoint returns 400 since ~May 2026 — DEAD
**Working method:** HTML heuristic — scrapes fare watch pages for price signal indicators only
**What it produces:** Price trend signals, sale alerts, competitor positioning intel
**NOT for DB prices** — Perx prices are TA-interline, not consumer-facing
**Fare watches active:** 8 (as of 2026-06-26)
**Run cadence:** Nightly (`perx-intel-monitor.timer` or Dembe overnight sweep)
**Command:**
```bash
python3 scripts/perx_intel_monitor.py
```
**Session refresh:** When sessionid expires → Commander re-authenticates at perx.com → export cookies → update `creds/perx_cookies.json`

---

### 4b. Perx (Sailing DB Feed — Luxury Lines)
**Script:** `scripts/fetch_perx_sailings.py` ← NEW 2026-06-28
**Output:** `intel/regent_perx_YYYYMMDD.json`, `intel/silversea_perx_YYYYMMDD.json`, `intel/atlas_perx_YYYYMMDD.json`
**Auth:** Same `creds/perx_cookies.json` as 4a (Django sessionid)
**Cookie file:** `creds/perx_cookies.json` — GITIGNORED — expires ~Jul 26
**Endpoint:** `https://www.perx.com/cruises/search/?cruise_line_id={id}&size=200&order_by=cabin_b%3A%3Adeparture_date`
**Line IDs (confirmed 2026-06-28):** Regent=1595 · Silversea=1589 · Atlas=3921
**Parse method:** BeautifulSoup `div.cruise-search-result[id]` — skips price-only sub-rows
**Fields extracted:** line, ship (from URL slug), departure (from href), nights, from_port, to_port, route_name (h3), region (inferred), price_orig (list-price span), price_disc (your-price span), itinerary_id, detail_url
**Source badges:** `regent_perx` (RP gold) · `silversea_perx` (SP gold) · `atlas_perx` (AP gold)
**Records per run:** Regent ~17 · Silversea ~41 · Atlas ~7 = ~65 total
**NOT for client pricing** — TA-interline rates, internal pipeline only
**Timer:** ExecStartPre step 1b in `cruise-db-refresh.service` (runs monthly before DB rebuild)
**Command:**
```bash
python3 scripts/fetch_perx_sailings.py [--lines regent silversea atlas]
```
**Session refresh:** When `< 3 cards` returned → Telegram alert fires → Commander copies fresh cookies from perx.com (logged in) → saves to `creds/perx_cookies.json` as JSON array format

---

## PENDING / PARTIAL SCRAPERS

### 5. Viking Ocean (VTG Line 29)
**Status:** PARTIAL — VTG ticker for Viking is JS-rendered, cannot fetch without Playwright
**Existing DB records:** 838 "Viking" records from CruiseMapper (ships: Viking Mars, Venus, Jupiter, etc.)
**Gap:** No confirmed Viking Ocean pricing/deal data
**Next step:** Playwright session → `https://www.vacationstogo.com/ticker.cfm?l=29&...` → parse JS-rendered HTML
**Owner:** ELON (A12) to automate; Dembe to provide intelligence

### 6. Consumer Site Pricing — Crystal Cruises (LIVE ✅)
**Script:** `scripts/fetch_consumer_prices.py` → `fetch_crystal()`
**Status:** LIVE — 276 voyages scraped, prices loading into DB nightly
**Pipeline:**
1. `GET https://www.crystalcruises.com/sitemap-0.xml` → 276 cruise slugs
2. `GET https://www.crystalcruises.com/_next/data/{BUILD_ID}/cruises/{slug}.json?slug={slug}`
3. Extract `min(priceSum for currency=='USD')` from `price` array
4. Match DB row by `line='Crystal Cruises' AND ship LIKE ? AND departure LIKE ?`
5. `UPDATE cruises SET price_ind=?, price_ts=?, price_src='crystalcruises.com'`

**Next.js build ID:** `3.11.3` (update `CRYSTAL_BUILD_ID` in script if Crystal redeploys — 404 = stale ID)  
**Ships:** Crystal Serenity (CSE), Crystal Symphony (CSY), Crystal Grandeur (CGR)  
**Auth:** None — plain HTTP GET, no Cloudflare blocking  
**Rate limit:** 1 req/s (polite delay hardcoded in script)  
**Anti-bot:** Low. No CAPTCHA. User-Agent header sufficient.  
**Price structure:** `price[]` → `{currency, priceSum, portCharge}` × 30 cabin categories  
**Sample prices (2026-06-26):** Symphony Dec 30 →$5,800 pp · Serenity Aug 21 → $2,700 pp  
**Nightly timer:** `cruise-price-refresh.timer` → fires 02:00 MT → `fetch_consumer_prices.py --all`  
**Harlan caveat (REQUIRED on all displayed prices):**
> "Indicative fares sourced from public booking engines as of [date/time]. Actual pricing varies by cabin category, availability, and promotions. Your D2M advisor will confirm live rates within 2 business hours."

### 7. Consumer Site Pricing — Regent Seven Seas (PENDING)
**Status:** PENDING — Playwright needed
**Risk:** HIGH — Cloudflare 403 on all plain HTTP probes
**Script:** Add `fetch_rssc()` to `scripts/fetch_consumer_prices.py` when endpoint captured
**Discovery path:** Playwright session → rssc.com booking flow → DevTools network intercept → find fare JSON endpoint

### 8. Consumer Site Pricing — Silversea (PENDING)
**Status:** PENDING — JS-rendered, Playwright required
**Script:** Add `fetch_silversea()` to `scripts/fetch_consumer_prices.py` when endpoint captured

### 9. Consumer Site Pricing — Atlas Ocean Voyages (PENDING)
**Status:** PENDING — Playwright needed (403/404 on plain HTTP)

### 10. Consumer Site Pricing — Explora Journeys (PENDING)
**Status:** PENDING — Playwright needed (site unreachable on plain HTTP)

### 11. Consumer Site Pricing — Oceania (LOWER PRIORITY)
**Status:** Deferred — not a D2M partner line
**Note:** Line IDs l=47 (VTG) available; plain HTML scrape feasible via Playwright if needed for broader DB coverage

---

## BUILDER PIPELINE

```
[CruiseMapper JSON] ──┐
[VTG FastDeals TXT]  ──┤
[VTG Oceania JSON]   ──┤→ build_master_cruise_db.py → output/cruises.db (SQLite FTS5)
[VTG Crystal JSON]   ──┤                            → output/cruises_legacy.html (archive)
[DeluxeCruises JSON] ──┘                            → output/MASTER_CRUISE_DB_*.json
```

**Consumer price overlay (future):**
```
output/cruises.db ──→ scripts/fetch_consumer_prices.py ──→ UPDATE cruises SET price_ind=?, price_ts=?, price_src=?
```

---

## LINE CANONICAL MAP
*Applied in `build_master_cruise_db.py` `LINE_CANONICAL` dict. Normalize all scrapers to these names:*

| Raw name | Canonical | Source |
|---|---|---|
| Atlas | Atlas Ocean Voyages | VTG FastDeals |
| Crystal | Crystal Cruises | VTG FastDeals / CruiseMapper |
| Ponant | PONANT | CruiseMapper |
| Paul Gauguin | Paul Gauguin Cruises | DeluxeCruises |
| Regent | Regent Seven Seas Cruises | VTG FastDeals |
| Silversea | Silversea Cruises | VTG FastDeals / CruiseMapper |
| Ritz-Carlton Yacht Club | Ritz-Carlton Yacht Collection | CruiseMapper |

---

## DEMBE NIGHTLY SWEEP CHECKLIST

*Minimum nightly run (Dembe autonomous, no Commander gate):*

1. `python3 scripts/perx_intel_monitor.py` — Perx fare watch signals (if sessionid valid)
2. Review `data/perx_eod_queue.json` — surface P0 alerts
3. Check `intel/` directory for stale JSON (>30 days) → flag for re-scrape
4. Monthly (1st): full CruiseMapper + DeluxeCruises rebuild → `python3 scripts/build_master_cruise_db.py`

*When VTG cookies expire:* Flag to Commander for browser re-export. Do not block on this — CruiseMapper continues nightly.

---

*Full intelligence architecture: `docs/AGENTS_HEADLESS_DISPATCH_ARCHITECTURE.md` · Memory: `project_master_cruise_db.md` · Framework: `project_travel_search_framework.md`*
