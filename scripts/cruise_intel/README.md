# Cruise Intel Pipeline

**Dreams2Memories Travel, LLC — T2 Wing Exercise**

Multi-source luxury cruise intelligence scraper for Arctic / Europe / Mediterranean sailings.
**10-source pipeline: 205+ sailings, 13+ cruise lines, 3 waves** (Wave 3 complete 2026-05-24).

---

## Sources

### Wave 1 — Core Sources
| Source | Method | File |
|--------|--------|------|
| **deluxecruises.com** | gstack Chromium, 22 HTML pages | `scrape_deluxecruises.py` — manual run |
| **Perx.com** | Hidden REST API: `sail-personalize.com` | `scrape_perx.py` — fully automated |
| **OAT.com** | gstack browser, 26 pages | `scrape_oat.py` — expedition/small-ship |
| **Ponant.com** | gstack browser | `scrape_ponant.py` — `travel-in/[year]/[month]` |

### Wave 2 — Line-Direct Additions
| Source | Method | File |
|--------|--------|------|
| **HX Expeditions** | Next.js `__NEXT_DATA__` JSON | `scrape_hx.py` |
| **SeaDream Yacht Club** | gstack browser | `scrape_seadream.py` |
| **Explora Journeys** | Sitemap XML | `scrape_explora.py` |

### Wave 3 — Aggregators (most travelers never check these)
| Source | Method | Auth | File |
|--------|--------|------|------|
| **CruiseMapper** | requests + BeautifulSoup (static HTML) | None | `scrape_cruisemapper.py` |
| **CruisesOnly** | gstack browser | None | `scrape_cruisesonly.py` |
| **CruisePlum** | gstack + authenticated form login | Required (see below) | `scrape_cruiseplum.py` |

> **vacationstogo.com**: BLOCKED — interline-only, all endpoints require login.
> **CruisePlum credentials**: Set `~/.config/d2m/cruiseplum.env` with `USER=your@email.com` and `PASS=yourpassword`
> (or env vars `CRUISEPLUM_USER` / `CRUISEPLUM_PASS`)

---

## Quick Start

### Full fresh run (Oct/Nov 2026, all 10 sources)
```bash
cd ~/Thunderbird/scripts/cruise_intel
python3 run_pipeline.py
```

### Wave 3 only (skip W1+W2 cached sources)
```bash
python3 run_pipeline.py \
  --skip-perx --skip-oat --skip-ponant \
  --skip-hx --skip-seadream --skip-explora
```

### Reassemble from cached JSONs (no scraping)
```bash
python3 run_pipeline.py --build-only
```

### Skip slow browser scrapers
```bash
python3 run_pipeline.py --skip-oat --skip-ponant --skip-cruisesonly --skip-cruiseplum
```

### Custom year/months
```bash
python3 run_pipeline.py --year 2027 --months 4 5
```

### CruisePlum with explicit credentials
```bash
python3 run_pipeline.py --cruiseplum-user you@email.com --cruiseplum-pass yourpass
```

---

## Individual Scrapers

### Wave 1
```bash
python3 scrape_perx.py --year 2026 --months 10 11
python3 scrape_oat.py  --year 2026 --months 10 11   # gstack, ~20 min
python3 scrape_ponant.py --year 2026 --months 10 11  # gstack, ~5 min
```

### Wave 2
```bash
python3 scrape_hx.py        --year 2026 --months 10 11
python3 scrape_seadream.py  --year 2026 --months 10 11   # gstack
python3 scrape_explora.py   --year 2026 --months 10 11
```

### Wave 3
```bash
python3 scrape_cruisemapper.py --year 2026 --months 10 11  # ~5 min, polite crawl
python3 scrape_cruisesonly.py  --year 2026 --months 10 11  # gstack, ~10 min
python3 scrape_cruiseplum.py   --year 2026 --months 10 11  # gstack+login, needs creds
```

### Report generation
```bash
python3 generate_report.py   # → output/T2_CRUISE_REPORT.html
```

---

## Output Files

| File | Description |
|------|-------------|
| `output/T2_MASTER_CRUISE_OCTOBER_NOVEMBER_2026.csv` | Master dataset (205+ rows, 10 source flags) |
| `output/T2_STATS.json` | Run statistics |
| `output/T2_CRUISE_REPORT.html` | Interactive HTML report (cards + voyage links + filters) |
| `output/T2_PERX_COMBINED.json` | Perx deduped dataset |
| `output/T2_OAT_SOURCE_DATA.json` | OAT departure records |
| `output/T2_PONANT_CLEAN.json` | Ponant filtered dataset |
| `output/T2_HX_SOURCE_DATA.json` | HX Expeditions dataset |
| `output/T2_SEADREAM_SOURCE_DATA.json` | SeaDream dataset |
| `output/T2_EXPLORA_SOURCE_DATA.json` | Explora Journeys dataset |
| `output/T2_CRUISEMAPPER.json` | CruiseMapper dataset (W3) |
| `output/T2_CRUISESONLY.json` | CruisesOnly dataset (W3) |
| `output/T2_CRUISEPLUM.json` | CruisePlum dataset (W3, out-the-door pricing) |

---

## Standing Procedures (A7 Sterling, 2026-05-24)

| # | Procedure |
|---|-----------|
| SP-T2-1 | Run gstack network inspection before scraping any OTA — document shared backends |
| SP-T2-2 | Cross-source dedup key = `normalized_ship + date ±1 day`. Never route strings. |
| SP-T2-3 | `parse_date()` handles: `%b %d, %Y` / `%d %b %Y` / `%Y-%m-%d` / `%m/%d/%y` / cross-month ranges |
| SP-T2-4 | 3 URL attempts max on any source → declare non-viable → substitute (20 min rule) |
| SP-T2-5 | Post-assembly smoke check: `count(csv[on_source]='Y')` must equal `count(source_json)` |

---

## Architecture

```
Wave 1:
  scrape_deluxecruises.py ──→ T2_EXERCISE_DEMBE_*.json  ─┐
  scrape_perx.py          ──→ T2_PERX_COMBINED.json     ─┤
  scrape_oat.py           ──→ T2_OAT_SOURCE_DATA.json   ─┤
  scrape_ponant.py        ──→ T2_PONANT_CLEAN.json      ─┤
                                                          │
Wave 2:                                                   ├──→ build_master.py
  scrape_hx.py            ──→ T2_HX_SOURCE_DATA.json    ─┤        │
  scrape_seadream.py      ──→ T2_SEADREAM_*.json        ─┤        ├──→ T2_MASTER_*.csv
  scrape_explora.py       ──→ T2_EXPLORA_*.json         ─┤        └──→ T2_STATS.json
                                                          │
Wave 3:                                                   │
  scrape_cruisemapper.py  ──→ T2_CRUISEMAPPER.json      ─┤
  scrape_cruisesonly.py   ──→ T2_CRUISESONLY.json       ─┤
  scrape_cruiseplum.py    ──→ T2_CRUISEPLUM.json        ─┘
```

**Cross-reference logic:**
```python
# Dedup key: norm(ship) + departure_date ±1 day
# NEVER match on route strings — they differ across sources
def find_match(ship_norm, dep_date, entries, tolerance=1):
    for e in entries:
        if e['ship_norm'] == ship_norm:
            if abs((dep_date - e['departure_date_obj']).days) <= tolerance:
                return e
    return None
```

**Price authority chain (W3):**
- CruisePlum (out-the-door) overwrites CruisesOnly price when both exist
- CruisesOnly carries price but doesn't overwrite existing data
- CruiseMapper carries no price data

---

## deluxecruises.com Manual Scrape

deluxecruises.com renders via JavaScript — gstack required. URL pattern:
```
https://www.deluxecruises.com/{line}/cruises/{month}-{year}.htm
```
Lines covered (9): silversea, regent-seven-seas, seabourn, oceania, crystal, azamara, windstar, ponant, paul-gauguin

Run `scrape_deluxecruises.py` and save output to `output/T2_EXERCISE_DEMBE_CRUISE_INTELLIGENCE.json`.

---

## Terminal Display — 256-Color

The pipeline uses ANSI 256-color output (Wave 3 upgrade):

| Wave | Color | ANSI Code | Example |
|------|-------|-----------|---------|
| W1 | Electric cyan | `\033[38;5;51m` | Perx, OAT, Ponant, deluxe |
| W2 | Vivid blue | `\033[38;5;33m` | HX, SeaDream, Explora |
| W3 | Amber orange | `\033[38;5;214m` | CruiseMapper, CruisesOnly, CruisePlum |

Terminal must support 256-color ANSI (virtually all modern terminals do).

---

## HTML Report

`generate_report.py` produces an interactive single-page report with:
- **Stats bar**: total sailings, Oct/Nov split, line count, multi-source count, source count
- **By-Cruise-Line cards**: each card shows ships + Oct/Nov pill counts + clickable voyage links
- **Voyage links**: each link anchors directly to the row in the table below (`href="#v-{idx}"`)
- **Table**: sortable, filterable by text/month/line, multi-source checkbox
- **Source badges**: 10 letter badges (D/P/O/N/H/S/E/M/C/L) color-coded by source
- **Price column**: populated from CruisesOnly/CruisePlum when available

---

## Competitive Value

Our edge is **source depth**, not just source count. We cross-reference:
- Direct line sites (Ponant, HX, SeaDream, Explora)
- Travel agencies (deluxecruises.com, OAT)
- Fare aggregators (Perx, CruisesOnly)  
- Itinerary databases (CruiseMapper — 15 luxury lines)
- True-cost pricing (CruisePlum — member-only)

When a voyage appears on 3+ sources, it carries confidence. When pricing differs 20%+ between sources, that's actionable intelligence.

---

## Monetization Vectors

1. **D2M lead-gen** — Complimentary cruise market scan as booking hook for prospects
2. **OA subscription** — Monthly upcoming-season sweep for Outside Agent network
3. **Fiverr gig** — "Luxury Cruise Intelligence Report: All sailings [season], [region], 10 sources" → $250–750/report
4. **Poe.com bot** — Interactive cruise search assistant with live pipeline backend

---

## Time & Token Economics

| Metric | Value |
|--------|-------|
| Wall clock (full 10-source run) | ~4 hours first time |
| Repeatable run (W1+W2 cached, W3 live) | ~45 min |
| Token spend | ~$0 on Claude MAX (unlimited) |
| Commander active time | ~20 min |

---

*Dreams2Memories Travel, LLC · Thunderbird Wing · T2 Wave 3 Complete 2026-05-24*

---

## T2 Re-scope — South Pacific / APAC Luxury (May/June 2028)

**New scope (Commander directive 2026-05-31):**
- Period: May + June 2028
- Filter: any sailing touching **at least one** of: Papeete (Tahiti), Auckland, Sydney, Melbourne, Singapore (+ reasonable regional context)
- Lines: luxury + ultra-luxury only (see `LUXURY_ULTRA_LINES` in `config.py`)

**Recommended run:**
```bash
cd ~/Thunderbird/scripts/cruise_intel
python3 run_pipeline.py \
  --year 2028 --months 5 6 \
  --tag may-june-2028-spac \
  --spac \
  --skip-oat --skip-ponant --skip-cruiseplum   # start with fast sources; add back as needed
```

**Direct build with filter (after manual/ cached scrapes):**
```bash
python3 build_master.py --spac --output output/T2_MASTER_may-june-2028-spac.csv
```

**Artifacts produced:**
- `T2_MASTER_may-june-2028-spac.csv`
- `T2_CRUISE_REPORT_may-june-2028-spac.html`
- Per-source JSONs (reuse with --build-only on subsequent runs)

**Notes:**
- 2028 schedules will be sparse early; re-run periodically as inventory opens (12–18 mo horizon).
- Aggregators (CruiseMapper, CruisesOnly, CruisePlum) are the highest-yield for this geography.
- Old Europe/Med pipeline remains untouched (use without `--spac` and original tags).
- Filter logic lives in `utils.py:has_target_port()` + `is_luxury_ultra_line()` + assembly in `build_master.py`.

**Standing order:** When re-running for this scope, always use `--tag` and `--spac` to keep datasets separate.
