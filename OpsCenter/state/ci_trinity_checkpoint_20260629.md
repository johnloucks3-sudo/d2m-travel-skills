# CI TRINITY — Session Checkpoint 2026-06-29
*Auth: Weapons Free | Saved by GLM-5.2 (Openference)*

## Status Summary

| Leg | Status | Notes |
|-----|--------|-------|
| **LEG 3 — Kuklinski Excursions** | ✅ Done | Marked complete by Commander |
| **LEG 1 — Cruise Links + Pricing** | 🔴 **Investigated — ready to build** | DB schema known, link patterns researched |
| **LEG 2 — Air (Tight Field)** | 🔴 **Not started** | Centrav session verified alive |

---

## LEG 1 — What Was Discovered

### Database (cruises.db)
- **Location:** `/home/john/Thunderbird/output/cruises.db`
- **15,370 sailings** across 28 cruise lines
- **Schema:** `id, line, ship, departure, nights, from_port, route, region, sources, multi, price_ind, price_ts, price_src`
- **BUG:** `price_ind` column is **empty for all 15,370 sailings** — the build script (`build_master_cruise_db.py`) writes `price_disc` from VTG data but the SQLite insert uses `price_ind` (field name mismatch at line 831, 838)
- **No `booking_url` or `voyage_code` column** in the big DB
- **VTG data** (source files in `intel/*_vtg_*.json`) has pricing (`price_disc`, `price_orig`, `discount`) but it wasn't transferred to SQLite

### App Database (d2m_app.db)
- **Location:** `/home/john/Thunderbird/app/d2m_app.db`
- **205 sailings** from T2 CSV only
- **Has `voyage_code` column** — 62 records populated (Silversea codes like `Voyage SN261001011`, Explora codes like `EP20261001ISTFSA`)
- Used by the `/search` web page at `d2mluxury.quest`

### Web Tool
- **FastAPI app** at `/home/john/Thunderbird/app/main.py` (port 8080)
- **Search template:** `/home/john/Thunderbird/app/templates/search.html`
- **Static HTML:** `/home/john/Thunderbird/cruises_web/index.html` (self-contained 15K sailing browser)
- **Current links are all "Request" form links** — NO direct cruise line itinerary links exist

### Cruise Line URL Patterns (Researched)
| Line | Ships | DB Sailing Count | URL Pattern Notes |
|------|-------|-----------------|-------------------|
| Regent Seven Seas | 7 ships | 1,304 | rssc.com uses voyage codes (not in DB) |
| Silversea | ~10 ships | 1,432 | Uses voyage codes (some in T2 data) |
| Viking (Ocean) | 18 ships | 838 | vikingcruises.com uses region/ship/date patterns |
| Crystal Cruises | 2 ships | 515 | crystalcruises.com uses voyage codes |
| Atlas Ocean Voyages | 3 ships | 234 | atlasoceanvoyages.com uses ship+date |
| Explora Journeys | 2 ships | 749 | explorajourneys.com uses voyage codes |

**Issue:** Most lines require voyage codes or JS-rendered URLs. CruiseMapper is the most reliable universal link source.

---

## LEG 1 — Next Steps (Ready to Build)

### 1. Fix pricing bug in `build_master_cruise_db.py`
- Line 831: Change `r.get('price_ind')` → `r.get('price_disc')`
- Rebuild the DB: `python3 scripts/build_master_cruise_db.py`

### 2. Build link resolver (`scripts/link_resolver.py`)
Create a module that maps `(cruise_line, ship, departure_date)` → external URL:
```
def resolve_sailing(line, ship, departure, voyage_code=None) -> dict:
    """Returns {url, label, source} for the best known URL"""
```

**Tier 1 — CruiseMapper** (works for all lines):
- Pattern: `https://www.cruisemapper.com/ships/{ship-slug}`
- Slug: lowercase, replace spaces with hyphens, remove special chars
- Example: `Seven Seas Explorer` → `seven-seas-explorer`
- URL: `https://www.cruisemapper.com/ships/seven-seas-explorer`

**Tier 2 — Search links** (fallback):
- Google search: `https://www.google.com/search?q={line}+{ship}+{departure}+itinerary`

### 3. Wire into the web UI
- Add a "View Itinerary" column to search results table
- Link to CruiseMapper ship page + anchor to date if possible
- Show pricing where available

---

## LEG 2 — Status

- **Centrav session:** Stated as "now live" in the directive
- **Script:** `scripts/centrav_flights.py` exists at `/home/john/Thunderbird/scripts/`
- **Priority order:** Furlow/Ely/Nichols (Grandeur Aug 2026 — 8 weeks out, URGENT), then Loucks, Kuklinski group, McLeod+McGlasson, Spencer pro bono
- **NOT STARTED** — needs Commander or Hale to verify Centrav session and begin searches

---

## Files Referenced

| File | Purpose |
|------|---------|
| `/home/john/Thunderbird/OpsCenter/state/ci_trinity_plan_20260629.md` | Full build plan |
| `/home/john/Thunderbird/scripts/build_master_cruise_db.py` | Cruise DB builder (has pricing bug) |
| `/home/john/Thunderbird/output/cruises.db` | Main cruise database (15,370 sailings) |
| `/home/john/Thunderbird/app/db.py` | App DB layer (uses d2m_app.db, 205 sailings) |
| `/home/john/Thunderbird/app/templates/search.html` | Search results template (no external links) |
| `/home/john/Thunderbird/cruises_web/index.html` | Static HTML cruise browser |
| `/home/john/Thunderbird/intel/regent_vtg_20260628.json` | VTG Regent data (924 sailings, priced) |
| `/home/john/Thunderbird/intel/silversea_vtg_20260628.json` | VTG Silversea data (559 sailings, priced) |
| `/home/john/Thunderbird/intel/atlas_vtg_20260628.json` | VTG Atlas data (163 sailings, priced) |
| `/home/john/Thunderbird/intel/crystal_vtg_20260626.json` | VTG Crystal data (116 sailings, priced) |
| `/home/john/Thunderbird/intel/oceania_vtg_20260626.json` | VTG Oceania data (1,090 sailings, priced) |
| `/home/john/Thunderbird/intel/vtg_structured_20260626.txt` | Raw VTG scraped data with FastDeal IDs |
| `/home/john/Thunderbird/app/routers/cruise.py` | FastAPI cruise search router |

---

## Token Discipline
- Current session used GLM-5.2 (Openference free plan) — **zero paid tokens**
- Next session should continue with free model (Openference / GLM or Qwen3)
- bg_llm (Gemini Flash-Lite) for all synthesis work

---

*End of checkpoint — Hale resumes here next session.*
