# MASTER PORT INDEX — All Active Client Voyages
*Compiled 2026-07-02 · Chronicle Event · Dembe (A2 Research & Market Intelligence)*

## Voyage Roster & Confidence

| # | Client | Ship | Line | Sail | Nights | Route | Port days | Confidence | File |
|---|--------|------|------|------|--------|-------|-----------|------------|------|
| 1 | Furlow / Ely-Darrow / Nichols | Seven Seas Grandeur | Regent | 2026-08-29 | 10 | Stockholm→Oslo (Scandinavia) | Stockholm(o), Warnemünde/Berlin(x2), Copenhagen(o), Kristiansand | **HIGH** ports / MED dates / LOW times | FurlowElyNichols_Grandeur_2026-08-29_ports.md |
| 2 | Kuklinski Group (6) | Viking Mars | Viking Ocean | 2026-12-17 | 10 | Panama City→Ft Lauderdale | Canal transit, Colón, Puerto Limón, Roatán, Belize, Cozumel | **HIGH** | Kuklinski_VikingMars_2026-12-17_ports.md |
| 3 | McLeod & McGlasson | Seven Seas Grandeur | Regent | 2026-12-19 | 10 | Miami RT (Lesser Antilles) | St Thomas, Dominica, Antigua, St Kitts, Tortola | **HIGH** ports / LOW times | McLeod_Grandeur_2026-12-19_ports.md |
| 4 | John & Susan Loucks | Seven Seas Grandeur | Regent | 2026-12-29 | 16 | Miami→Los Angeles (Panama/Pacific) | Grand Cayman, Cartagena, Canal, Puntarenas, Puerto Quetzal, Acapulco, Cabo, San Diego | **HIGH** (full times) | Loucks_Grandeur_2026-12-29_ports.md |
| 5 | McLeod & McGlasson | Discovery Princess | Princess | 2027-03-13 | 7 | LA RT (Mexican Riviera) | Cabo, Mazatlán, Puerto Vallarta | **MEDIUM** (standard pattern, verify Mar-13 specific) | McLeod_DiscoveryPrincess_2027-03-13_ports.md |
| 6 | John & Susan Loucks | Silver Nova | Silversea | 2027-05-05 | 24 (B2B2B) | Venice→Athens | 25+ Adriatic/Ionian/Aegean ports (3 segments) | **HIGH** ports (TA-portal) / LOW times | Loucks_SilverNova_2027-05-05_ports.md |
| 7 | McLeod & McGlasson | Seven Seas Prestige | Regent | 2027-12-18 | 10 | Miami RT (Season to Cheer) | Puerto Plata, San Juan, St Kitts, Dominica, Antigua, Tortola | **HIGH** (full times) | McLeod_Prestige_2027-12-18_ports.md |

*(o) = overnight in port · (x2) = multi-day call*

## Confidence Summary
- **HIGH confidence (6 of 7):** #1 (ports), #2, #3 (ports), #4, #6, #7. All ports sourced from cruise-line dossiers, TA portal, master DB, or corroborated aggregators.
- **MEDIUM confidence (1 of 7):** #5 Discovery Princess Mar 13 2027 — port SET and hours are the standard Discovery Princess Mexican Riviera product (HIGH), but the exact Mar-13-specific published day-by-day was not directly obtained (princess.com fetch failed; DB had no row). Date-mapped onto standard pattern. **Verify on Princess portal before client itinerary delivery.**
- **NO voyages at LOW/unpublished.** All 7 have a usable port sequence.

## Clock-time gaps (arrive/depart)
Exact per-port arrive/depart times are HIGH only where an invoice-grade dossier or aggregator day-by-day exists:
- Full times: #4 Loucks Panama/Pacific, #7 Prestige Season to Cheer, #5 Discovery Princess (standard).
- Times TBD (rssc.com Akamai-walled / Silversea TA portal not re-pulled): #1 Grandeur Scandinavia, #3 McLeod Lesser Antilles, #6 Silver Nova, plus Viking port hours on #2 (embark 3PM and canal 07:00-18:00 confirmed).
- To fill: Commander-assisted rssc.com login (MISSION-214/820) for Regent times; `/silversea-ta` skill for Silver Nova times; Viking portal for #2 hours.

## SHARED PORTS — Cross-voyage research reuse value
Research one port, apply across multiple client products.

### Caribbean — Lesser/Greater Antilles cluster (voyages #3, #7)
| Port | McLeod Grandeur Dec 2026 (#3) | McLeod Prestige Dec 2027 (#7) |
|------|:---:|:---:|
| **Basseterre, St. Kitts** | ✅ Dec 25 | ✅ Dec 22 |
| **Roseau, Dominica** | ✅ Dec 23 | ✅ Dec 23 |
| **St. John's, Antigua** | ✅ Dec 24 | ✅ Dec 24 |
| **Road Town, Tortola** | ✅ Dec 26 | ✅ Dec 25 |
| St. Thomas | ✅ Dec 22 | — |
| Puerto Plata / San Juan | — | ✅ Dec 20 / 21 |
→ **4 shared ports, SAME CLIENT (McLeod/McGlasson), consecutive Decembers.** Excursion research for St Kitts, Dominica, Antigua, Tortola done once serves both trips. Note both fall on Christmas week — holiday-hours caveat applies to both.

### Panama / Pacific-Caribbean cluster (voyages #2, #4)
| Port / feature | Kuklinski Viking Mars (#2) | Loucks Grandeur (#4) |
|------|:---:|:---:|
| **Panama Canal Transit** | ✅ Dec 18 | ✅ Jan 3 |
| **Costa Rica** | ✅ Puerto Limón (Caribbean side) | ✅ Puntarenas (Pacific side) |
| Colón, Panama | ✅ | — |
| Cartagena | — | ✅ |
| Cabo San Lucas | — | ✅ (also #5) |
→ Panama Canal transit narrative + Costa Rica context reuse across both. Note the two Costa Rica calls are on OPPOSITE coasts (Limón = Caribbean rainforest; Puntarenas = Pacific) — different excursion sets.

### Mexico Pacific cluster (voyages #4, #5)
- **Cabo San Lucas** appears on both Loucks Grandeur (#4, Jan 11) and McLeod Discovery Princess (#5, Mar 15). Same-port excursion research reusable.

### Regent Seven Seas Grandeur — same ship, 3 voyages (#1, #3, #4)
Ship-level content (suites, dining venues Prime 7 / Chartreuse / Pacific Rim / Compass Rose, service standards, deck plans) is identical across all three Grandeur voyages. Photos: `reference_grandeur_photos.md` ship_732.

## Standing gaps / next collection
1. **Discovery Princess Mar 13 2027 (#5)** — verify exact sailing on Princess portal (voyage X634) before client delivery. Only MEDIUM item.
2. **Arrive/depart clock times** for Regent (#1, #3) and Silversea (#6) — need portal access (rssc walled; Silversea TA skill).
3. **Update source dossiers** with corrected routes: Prestige (#7) is Puerto Plata/San Juan/StKitts/Dominica/Antigua/Tortola, NOT generic "Lesser Antilles TBD"; Grandeur Scandinavia (#1) confirm Kristiansand day/times when rssc accessible.

## Source authority ranking used
1. Cruise-line portal (rssc.com / Silversea TA / Viking) — Akamai-walled for Regent this session
2. TESS / invoice-grade dossier
3. Master cruise DB (`output/cruises.db`, 15,368 sailings) — endpoints + voyage names
4. Non-walled aggregators (pureholidays, cruisebound, regentcruisessale, icruise) — day-by-day tables, reconciled against dossier ground truth

*— Dembe, A2 · 2026-07-02*
