# Cruise Intel Pipeline

**Dreams2Memories Travel, LLC — T2 Wing Exercise**

Multi-source luxury cruise intelligence scraper for Arctic / Europe / Mediterranean sailings.
Proven pipeline: 654-row master CSV, 32 cruise lines, 4 sources cross-referenced (T2 Exercise, 2026-05-24).

---

## Sources

| Source | Method | Notes |
|--------|--------|-------|
| **deluxecruises.com** | gstack Chromium, 22 HTML pages | `scrape_deluxecruises.py` — run manually; 9 luxury lines |
| **Perx.com** | Hidden API: `sail-personalize.com` | `scrape_perx.py` — fully automated; same backend as CruiseDirect |
| **OAT.com** | gstack browser | `scrape_oat.py` — 26 pages, expedition/small-ship |
| **Ponant.com** | gstack browser | `scrape_ponant.py` — `travel-in/[year]/[month]` pages |

> vacationstogo.com: **BLOCKED** — interline-only, all endpoints require login. Do not attempt without credentials.

---

## Quick Start

### Full fresh run (Oct/Nov 2026)
```bash
cd ~/Thunderbird/scripts/cruise_intel
python3 run_pipeline.py
```

### Reassemble from cached JSONs (no scraping)
```bash
python3 run_pipeline.py --build-only
```

### Custom year/months
```bash
python3 run_pipeline.py --year 2027 --months 4 5
```

### Skip slow browser scrapers (use cached OAT + Ponant)
```bash
python3 run_pipeline.py --skip-oat --skip-ponant
```

---

## Individual Scrapers

### Perx (automated, ~2 min)
```bash
python3 scrape_perx.py --year 2026 --months 10 11
```

### OAT (gstack browser, ~20 min)
```bash
python3 scrape_oat.py --year 2026 --months 10 11
```

### Ponant (gstack browser, ~5 min)
```bash
python3 scrape_ponant.py --year 2026 --months 10 11
```

### Build master only (all sources already scraped)
```bash
python3 build_master.py
```

---

## Output Files

| File | Description |
|------|-------------|
| `output/T2_MASTER_CRUISE_OCTOBER_NOVEMBER_2026.csv` | Master 654-row dataset |
| `output/T2_STATS.json` | Run statistics |
| `output/T2_PERX_COMBINED.json` | Perx deduped dataset |
| `output/T2_OAT_SOURCE_DATA.json` | OAT departure records |
| `output/T2_PONANT_CLEAN.json` | Ponant filtered dataset |
| `output/T2_PONANT_PARSED.json` | Ponant raw parse output |

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
scrape_perx.py   ──→ T2_PERX_COMBINED.json     ─┐
scrape_oat.py    ──→ T2_OAT_SOURCE_DATA.json    ─┼──→ build_master.py ──→ T2_MASTER_*.csv
scrape_ponant.py ──→ T2_PONANT_CLEAN.json       ─┘                    ──→ T2_STATS.json
(manual)         ──→ T2_EXERCISE_DEMBE_*.json   ─┘
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

---

## deluxecruises.com Manual Scrape

deluxecruises.com renders via JavaScript — gstack required. URL pattern:
```
https://www.deluxecruises.com/{line}/cruises/{month}-{year}.htm
```
Lines covered (9): silversea, regent-seven-seas, seabourn, oceania, crystal, azamara, windstar, ponant, paul-gauguin

Run scrape_deluxecruises.py and save output to `output/T2_EXERCISE_DEMBE_CRUISE_INTELLIGENCE.json`.

---

## Monetization Vectors

1. **Fiverr gig** — "Luxury Cruise Intelligence Report: All sailings [season], [region], 4 sources" → $150–500/report
2. **Poe.com bot** — Interactive cruise search assistant with live pipeline backend
3. **D2M lead-gen** — Complimentary cruise market scan as booking hook for prospects
4. **OA subscription** — Monthly upcoming-season sweep for Outside Agent network

**Prerequisite for external monetization:** Scripts are now productized. A CLI wrapper for Fiverr delivery and a Poe API endpoint are the next build steps.

---

## Time & Token Economics

| Metric | Value |
|--------|-------|
| Wall clock (full run) | ~3 hours first time |
| Repeatable run (cached sources) | ~30 min |
| Token spend | ~220K Sonnet 4.6 tokens = $0 on MAX |
| Commander active time | ~15 min |

*Dreams2Memories Travel, LLC · Thunderbird Wing · T2 Exercise 2026-05-24*
