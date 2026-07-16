# Port Data — Furlow / Ely-Darrow / Nichols Group | Seven Seas Grandeur | 2026-08-29
**Voyage:** Storied Scandinavia (Regent voyage code GRA260829)
**Duration:** 10 nights
**Embarkation:** Stockholm, Sweden — August 29, 2026
**Disembarkation:** Oslo, Norway — September 8, 2026
**Group:** 3 couples — John & Missy Furlow (3071222) · Al Ely & Amy Darrow (3096289) · Larry & Heidi Nichols (3078056)

## Itinerary

| Day | Date | Port | Country | Arrive | Depart | Notes |
|-----|------|------|---------|--------|--------|-------|
| 1 | Aug 29 (Sat) | Stockholm | Sweden | Embark | eve | EMBARKATION. Overnight in port.* |
| 2 | Aug 30 (Sun) | Stockholm | Sweden | — | pm | Overnight — full day in Stockholm* |
| 3 | Aug 31 (Mon) | At Sea | — | — | — | Sea day* |
| 4 | Sep 1 (Tue) | Warnemünde (for Berlin) | Germany | am | — | Berlin gateway — day 1 of 2* |
| 5 | Sep 2 (Wed) | Warnemünde (for Berlin) | Germany | — | eve | ✅ RSSC-ANCHORED. Berlin gateway (extra Berlin day added; Rostock removed). Confirmed via RSSC excursion day-5 WAR-004 "Berlin On Your Own" dated Sep 2. |
| 6 | Sep 3 (Thu) | Copenhagen | Denmark | am | — | Overnight in port (moved to Sep 3 per Jan 23 2026 dossier change)* |
| 7 | Sep 4 (Fri) | Copenhagen | Denmark | — | pm | Overnight — full day* |
| 8 | Sep 5 (Sat) | At Sea | — | — | — | Sea day* — day-slot shifts here now that Kristiansand is confirmed Sep 6, not Sep 5. |
| 9 | Sep 6 (Sun) | Kristiansand | Norway | ~09:45 (inferred) | TBD | ✅ **DAY-SLOT CORRECTED 2026-07-16** — was Sep 5 (inferred), now confirmed Sep 6. Source: Furlow RSSC portal excursion reservation "Explore Kristiansand on Foot" dated Sep 06, 2026 10:00 (`validations/rssc_scrape/3071222_Furlow_deep.json`, live-captured 2026-06-02); cross-confirmed by Nichols/Ely-Darrow bookings both showing "Kristiansand (1 Day(s) in Port)" immediately preceding their Sep 7 Oslo excursions. Arrive time is inferred from the 10:00 excursion start, not a direct dock-arrival timestamp. Depart time still TBD (rssc-walled). |
| 10 | Sep 7 (Mon) | Oslo | Norway | am | — | ✅ RSSC-ANCHORED. Overnight in port. RSSC excursion day-10 OSL-020 dated Sep 7. |
| 11 | Sep 8 (Tue) | Oslo | Norway | — | Disembark | DISEMBARKATION. Ely/Darrow return OSL→LHR→DFW same day (dossier flight matrix). |

> ⚠️ PER-CELL CONFIDENCE — READ BEFORE BUILDING CLIENT COPY (MISSION-802):
> - **✅ RSSC-ANCHORED rows (Day 5 Warnemünde/Sep 2, Day 9 Kristiansand/Sep 6, Day 10 Oslo/Sep 7):** line-confirmed from rssc.com excursion-reservation dates (Kristiansand confirmed 2026-07-16 — see Day 9 row).
> - **`*` rows (Stockholm overnight, remaining sea day, Copenhagen 2-day):** structure carried from the pureholidays GRA260829 aggregator table, which is the STALE pre-change version (it does NOT include Kristiansand). Day/overnight placement is RECONSTRUCTED by applying the dossier's Jan 2026 changes over that stale structure — NOT independently line-confirmed. Do not present a `*` cell to a client as verified; verify against rssc.com first (per Pipeline Rule 1: no unconfirmed fact in client copy).
> - **Kristiansand (Day 9, Sep 6):** day-slot now RSSC-anchored (corrected 2026-07-16, was previously inferred as Sep 5). Exact dock arrive/depart clock times still not directly captured — only the 10:00 excursion start time is known.
> - Exact arrive/depart clock times for ALL ports: not on non-Akamai sources; rssc.com (Akamai-walled, MISSION-214/820) holds them.

## Port Quick Notes
**Stockholm:** Sweden's capital across 14 islands. Overnight allows Gamla Stan (old town), Vasa Museum, City Hall. Two-day embark call.
**Warnemünde (Berlin):** Baltic port ~3 hrs from Berlin by rail/coach. The Berlin day-trip (Brandenburg Gate, Museum Island, WWII/Cold War sites) is the marquee excursion. Two port days give flexibility.
**Copenhagen:** Overnight port. Nyhavn, Tivoli, Amalienborg, Little Mermaid; strong food scene. Bike-friendly.
**Kristiansand:** Southern Norway coastal town — Posebyen old quarter, Kristiansand Zoo, fjord scenery. Softer-tempo call.
**Oslo:** Disembark port. Viking Ship / Fram museums, Vigeland Park, Opera House. WWII-history excursions available (OSL-020).

## Data Sources
- Dossier `DOSSIER_Grandeur_Scandinavia_Aug2026.md` (authoritative for route + Jan 2026 changes)
- Master DB `output/cruises.db`: Aug 29 2026, Stockholm→Oslo, 10 nights (confirmed)
- pureholidayscruises.co.uk GRA260829 (port structure — STALE, no Kristiansand)
- rssc.com excursion URLs (day-5 WAR-004 Sep 2 Berlin; day-9 Furlow "Explore Kristiansand on Foot" Sep 6; day-10 OSL-020 Sep 7 Oslo) — confirms day-slot dates
- RSSC official port catalog (`validations/rssc_scrape/ports_catalog_full.json`, `extracted_port_details.json`) — has official destination copy for Warnemünde/Copenhagen/Kristiansand/Oslo, captured live 2026-07-14/15. NOTE: the Kristiansand (KRS) entry's official description text itself says "Kristiansund" (a different, more northerly Norwegian city) — appears to be a copy-editing error on rssc.com's own port page, not a scrape defect (port code KRS/name/longName all correctly say Kristiansand). Do not copy that description verbatim into client materials without correcting the city name.
- Confidence: **HIGH** on ports/embark/disembark/route, including Kristiansand day-slot (corrected 2026-07-16); **LOW** on exact arrive/depart clock times for all ports except the one known 10:00 Kristiansand excursion start (TBD, rssc-walled)
- Last verified: 2026-07-16
