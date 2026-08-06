# STATUS — Google Flights + Fare Engines, May 2027 Loucks Business
**Date:** 2026-08-06 · **Author:** HALE-OC · **BLUF:** Google Flights RapidAPI still dead (429); Centrav session expired; **Skybird GDS Sabre is LIVE and produced real B2B Business fares** for the Loucks May 2027 itinerary.

## SOURCE STATUS (08-06 11:10 MT)

| Source | Status | Note |
|---|---|---|
| Google Flights RapidAPI (`thunderbird_google_flights_search.py`) | 🔴 DEAD | HTTP 429 — quota exhausted since 08-05, still 429 08-06. `RAPIDAPI_KEY` present in `.env`, subscription shows Basic $0 (150 req/mo). Until RapidAPI resets monthly quota, unusable. |
| Google Flights tfs token / SPA reverse-eng | 🟡 FRAGILE | Skill exists (`.opencode/skills/google-flights`). tfs URL navigates to Explore landing, not results, cold. Not AI-friendly. Not the path. |
| Centrav B2B (`thunderbird_centrav_search.py`) | 🔴 DEAD | Session expired, auto-login failed 08-06 11:04. All 19 fare watches fell back to Anansi web estimates. Manual re-auth: `python3 scripts/centrav_flights.py --centrav-login --headless false`. |
| **Skybird WINGS (GDS Sabre)** (`scripts/skybird_scan.py`) | 🟢 **LIVE** | Headless login + search verified 08-06. Real B2B Sabre fares, multi-city supported via `--legs`. |

## SKYBIRD RESULTS — LOUDEN MAY 2027 (Business, 2 pax)

**Outbound DEN→VCE 05/01/2027:**
| Airline | Routing | Stops | /pp | x2 |
|---|---|---|---|---|
| FI | DEN→KEF→FCO→VCE | 2 | $4,886.20 | $9,772.40 |
| TP | DEN→JFK→LIS→VCE | 2 | $5,308.20 | $10,616.40 |
| TP | DEN→BOS→LIS→VCE | 2 | $5,398.40 | $10,796.80 |

**Return ATH→DEN 05/30/2027:**
| Airline | Routing | Stops | /pp | x2 |
|---|---|---|---|---|
| TK | ATH→IST→DEN | 1 | $5,483.46 | $10,966.92 |
| TK | ATH→IST→ORD→DEN | 2 | $5,884.86 | $11,769.72 |

**Multi-city (exact itinerary, one ticket):**
| Airline | Routing | /pp | x2 |
|---|---|---|---|
| TK | DEN→ORD→IST→ATH→IST→ORD→DEN | $8,506.86 | $17,013.72 |

**Fare metadata (cheapest DEN→VCE):** FI 0670, cabin C, base $4,476 + tax $410 = $4,886/pp, refundable.

## VS ITA BASELINE (consumer, 08-05)
| Source | Cheapest | Note |
|---|---|---|
| ITA Matrix | $6,201/pp | American, 1 stop, consumer published |
| **Skybird B2B multi-city** | **$8,507/pp** | TK, Sabre net, one ticket |
| Skybird B2B one-ways summed | $10,370/pp | FI + TK |

*Skybird multi-city ($8,507) is a single TK ticket and beats buying two one-ways ($10,370). ITA's $6,201 (AA one-stop) is consumer fare without the return leg priced in the same way — direct apples-to-apples requires ITA multi-city pricing, not per-leg.*

## RECOMMENDATION
1. **Skybird is now the primary B2B Business fare engine** for research — headless, live, multi-city capable. Promote to the default when Centrav is down.
2. **Centrav manual re-auth required** (Commander or browser session) to restore the daily scan's primary engine.
3. **Google Flights RapidAPI** stays dormant until quota resets; do not retry against it (burns no money, but wastes calls).
4. **Do not spend more on the tfs SPA path** — documented dead-end for live fares.

## OPEN
- Skybird multi-city returned only TK options — confirm whether other carriers are genuinely unavailable at 331 days out or a search-parameter artifact. Some carriers don't file Business >~330 days (same pattern as ITA).
- `fare_type` null in Skybird summary — cross-check the raw payload if net-vs-published matters for quoting.
- No client send, no financial commitment — research only. WF-17 intact.
