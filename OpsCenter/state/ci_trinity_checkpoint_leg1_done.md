# CI TRINITY — Session Checkpoint 2026-06-29 (After Leg 1)
*Auth: Weapons Free | Ongoing Execution*

## Status

| Leg | Status | Notes |
|-----|--------|-------|
| **LEG 3 — Kuklinski Excursions** | ✅ Done | Commander-marked complete |
| **LEG 1 — Cruise Links + Pricing** | ✅ **DONE** | DB rebuilt, links live, pricing fixed |
| **LEG 2 — Air (Tight Field)** | 🔴 **Starting now** | |

---

## Leg 1 — What Was Built

### Pricing bug fixed ✅
- **File:** `scripts/build_master_cruise_db.py` line 831
- **Root cause:** `r.get('price_ind')` read `price_disc` data but the column was named `price_ind` and the values used `price_disc` as their dict key
- **Fix:** Changed to `r.get('price_disc')`
- **Result:** 2,587 sailings now have prices (was 0)

### Link resolver built ✅
- **File:** `scripts/link_resolver.py`
- **Capability:** Maps `(line, ship, departure_date)` → external URL
- **Tier 1 (deep links):** Line-specific ship/date URLs for Regent, Silversea, Viking, Crystal, Atlas, Explora
- **Tier 2 (universal):** CruiseMapper ship profiles for all 28 lines
- **Ship slug map:** 70+ ship name → URL slug mappings, including aliases (MSC Explora 1 → explora-i, etc.)
- **CLI mode:** `python3 scripts/link_resolver.py "Silversea Cruises" "Silver Nova" 2026-08-15`

### Database schema updated ✅
- **Added columns:** `booking_url TEXT, booking_label TEXT` to cruises.db
- **Rebuilt:** ALL 15,370 sailings now have booking URLs

### API server updated ✅
- **File:** `core/visual_synthesis/dashboard_app/server.py`
- **Updated search query** to SELECT `c.booking_url, c.booking_label`
- **Updated response** to include both fields in search results
- **Server restarted** on port 8901

### Frontend updated ✅
- **File:** `cruises_web/index.html` (served at /cruises/)
- **Result cards** now show "View itinerary ↗" link using per-sailing booking_url
- Falls back to line homepage URL if no sailing-specific link
- Live on dashboard server

### Files Changed
| File | Change |
|------|--------|
| `scripts/build_master_cruise_db.py` | Pricing bug fix (line 831); added link resolution in main flow; added `booking_url,booking_label` cols to SQLite; import from `.link_resolver`; added Link column to HTML table |
| `scripts/link_resolver.py` | **NEW** — full link resolution module for 28 lines |
| `core/visual_synthesis/dashboard_app/server.py` | Added `booking_url, booking_label` to SQL SELECT + response dict |
| `cruises_web/index.html` | Updated result card rendering to show per-sailing "View itinerary" link |
| `output/cruises.db` | Rebuilt (15,370 sailings, 2,587 with pricing, 15,370 with booking URLs) |

---

## Starting Leg 2 — Air/Tight Field

**Priority:** URGENT — Furlow/Ely/Nichols Grandeur Aug 2026 (8 weeks out)

**What needs to happen:**
1. Verify Centrav session is alive (`python3 scripts/centrav_flights.py --check-session`)
2. Build fare watches for priority client airport pairs
3. Run centrav flight search for Grandeur Aug 2026
4. Present options to Commander
5. Build air fare watches for Loucks, Kuklinski, McLeod+McGlasson

**Files:**
- `scripts/centrav_flights.py` — Centrav B2B portal automation
- `core/travel/centrav_serve.py` — Re-auth tool
- Centrav session: was stated as "now live" in the CI Trinity directive
