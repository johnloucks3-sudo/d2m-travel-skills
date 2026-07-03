# CI TRINITY — BUILD PLAN 2026-06-29
*Staged by Hale 2026-06-28. Commander directive.*

## Strategic Posture
100% capability on a tight field. Not 85% on everything.
Token constraint: week at 85%, will exhaust. Prioritize free-model build paths.

---

## LEG 1 — CRUISE LINKS + PRICING
**Problem:** cruise tool has 15,354 sailings but links don't resolve to correct per-sailing pages.
**Targets:**
- Per-sailing deep links to cruise line itinerary pages (not price pages)
- Pricing for all sailings (rack rates + interline VTG/Perx where available)

**Work items:**
1. Audit current link schema in cruise DB — what does each cruise_line's `booking_url` field contain?
2. For each of 28 cruise lines: find the URL pattern for a specific sailing by ship + departure date
3. Build link resolver: `sailing_id → direct itinerary URL`
4. Add pricing column: direct line scrape OR VTG/Perx interline (internal only, not public)
5. Wire pricing into the `/cruises` UI — show "from $X" where available

**Priority lines:** Regent, Silversea, Viking, Crystal, Atlas, Explora (our active client lines first)

---

## LEG 2 — AIR (TIGHT FIELD)
**Problem:** No live air links or pricing. Centrav session expired (MISSION-819).
**Tight field — ONLY these needs:**

| Client | Need | Notes |
|---|---|---|
| Loucks (John+Susan) | Grandeur Dec 2026: DEN→embark | Known sailing |
| Loucks (John+Susan) | Silver Nova May 2027: DEN→Athens | Known sailing |
| Kuklinski Group (3 couples) | Viking Mars Dec 2026: DEN→embark | 6 pax, group desk |
| McLeod + McGlasson | Grandeur Dec 2026 | |
| Furlow / Ely / Nichols | Grandeur Aug 2026 | ⚠️ 8 weeks out — urgent |
| Spencer (pro bono) | Grand Tour DEN-FCO | 12 pax, United group |

**Work items:**
1. Restore Centrav session (Commander manual login — MISSION-819)
2. For each need: Centrav search → capture direct link to that flight/itinerary
3. Build air watch: monitor price on those specific routes, alert when fare drops
4. Link display in client dossier: "Best air option as of [date]: [link] $X"

---

## LEG 3 — EXCURSIONS (KUKLINSKI VIKING MARS DEC 2026)
**Model:** Loucks Silver Nova May 2027 — `dossiers/Loucks_SilverNova_May2027_Excursions_v2_SUPPLEMENT.html`
**Commercial sources:** GYG · Tours With Locals · Project Expedition

**Viking Mars Dec 2026 ports (need to confirm itinerary):**
- Route: likely Caribbean or transatlantic based on Dec departure
- Confirm exact ports from Viking booking or website

**Work items:**
1. Pull Kuklinski Viking Mars itinerary → extract port list
2. For each port: GYG Playwright scrape + PE WebSearch + TWL search
3. Build Before/After/Food+Wine/Financial HTML doc (same 6-section schema as Loucks)
4. Persona breakdown: Dembe=research, ELON=tech, Sterling=code, Hale=synthesis+HTML
5. Output: `dossiers/Kuklinski_VikingMars_Dec2026_Excursions.html`

---

## SEQUENCE FOR TOMORROW
1. Leg 3 first (Kuklinski excursions) — most contained, canonical model exists
2. Leg 1 (cruise links + pricing) — highest client-facing impact
3. Leg 2 (air) — gated on Centrav session restore (Commander action needed)

## COMMANDER ACTION NEEDED BEFORE LEG 2
- Log into Centrav portal via yoga Firefox to restore session (MISSION-819)
- Once done: say "Centrav restored" and Leg 2 begins

