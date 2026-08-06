# HANDOFF — ITA MATRIX DONE, GOOGLE FLIGHTS + CENTRAV TOMORROW
**Date:** 2026-08-05 · **Author:** HALE-OC · **Commander:** Loucks

## MISSION: Reverse-engineer ITA Matrix (DEN→VCE 05/01 + ATH→DEN 05/30, 2 pax Business)

## RESULT: DELIVERED — URL builder validated, live fares captured

**Live ITA Matrix results (May 2027, Business, 2 pax):**
| Airline | Fare | Note |
|---|---|---|
| American | $6,201 | 1 stop |
| Lufthansa | $7,337 | — |
| Multiple Carriers | $7,337 | — |
| United | $8,230 | — |

**Deliverables:**
- Skill: `.opencode/skills/ita-matrix/SKILL.md` — base64-JSON URL builder (ground-truth validated vs ITA's own generated URL) + results parser + lessons-learned
- Multi-city payload contract captured verbatim from ITA's URL
- Existing engine: `core/travel/ita_matrix.py` (build_url + search_fare)

## COMMANDER VERDICT (direct quote)
> "This is very complicated and NOT AI friendly. Tomorrow we will try Google Flights and Centrav."

## LESSONS RECORDED (in skill)
1. URL-builder path = AI-friendly. UI form = NOT (Angular Material fragility: recent-route autocomplete pollution, chip duplication on Add Flight, shifting input IDs, 2 Commander hand-fixes).
2. Commit technique if UI needed: type 3-letter code → press **Enter** (or click field label). Never click body/h1 (navigates away).
3. Internal batch API (`content-alkalimatrix-pa.googleapis.com/batch`) not directly callable without page session plumbing — URL+render path simpler.
4. ITA Business fares not filed >~330 days out for some carriers; COACH fallback for far dates.

## NEXT MISSION (TOMORROW) — Google Flights + Centrav
- **Google Flights:** use `core/travel/thunderbird_google_flights_search.py` (RapidAPI, 150 req/mo free tier). NOTE: returned **429 Too Many Requests** on 2026-08-05 — quota may be exhausted; check `RAPIDAPI_KEY` usage before relying on it. Reverse-engineering the SPA (FlightsFrontendUi) was started but paused for ITA — the internal endpoint pattern is documented in the session.
- **Centrav B2B:** `core/travel/thunderbird_centrav_search.py` + `search_centrav_flights` MCP tool. B2B wholesale net fares — likely the best Business-class source for this itinerary. Check session validity (`check_centrav_session`).
- **Route for tomorrow:** same Loucks May 2027 — DEN→VCE 05/01 + ATH→DEN 05/30, 2 pax Business.
- **Cross-check:** ITA baseline = $6,201–$8,230/pax (American/Lufthansa/United/Multiple). Compare Google Flights + Centrav against it.

## OPEN
- bsk daemon restarts mid-session cleared stuck "interrupt" latches (documented in evernote-survey skill too).
- Commander approval gate: no client sends, no financial commitments — all fare work is research only.
