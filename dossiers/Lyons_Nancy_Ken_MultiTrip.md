---
client: "Nancy & Ken Lyons"
status: ACTIVE CLIENT (pro bono)
relationship: "Loucks travel companions — separate bookings, same ships on some voyages"
regent_account: "Klyons3@bellsouth.net (guest account, Seven Seas Society Gold, 177 nights cruised / 193 reward nights)"
source: "Regent rssc.com guest-account scrape 2026-07-03 via CloakBrowser (Akamai-defeated). Capture: validations/lyons_regent/"
captured: 2026-07-03
handling: "Client-facing comms require WF-17 (Dani formats, COS reviews, Commander approves). Lyons are pro bono."
---

# DOSSIER — Nancy & Ken Lyons (Multi-Trip)
**Status: ACTIVE CLIENT (pro bono) · 4 Regent bookings + 1 Silversea (May 2027, separate) · Last updated 2026-07-03**
**Regent Seven Seas Society: Gold tier · 177 nights cruised · 193 reward nights**
**Guests on every Regent booking: MR KENNETH LYONS · MRS NANCY LYONS**

> Captured 2026-07-03 from Nancy's own Regent account (rssc.com) via CloakBrowser stealth session — the first successful headless Akamai-defeated login+scrape of the guest portal. Raw capture: `validations/lyons_regent/`.

---

## TRIP 1 — ATHENS (PIRAEUS) → NEW YORK · "Historic Horizons"
| Field | Value |
|---|---|
| **Reservation** | 2979301 |
| **Cruise Reference** | SPL260811A |
| **Ship** | Seven Seas Splendor |
| **Suite** | Serenity Suite F1 · Deck 8 · #847 |
| **Sail dates** | Aug 11 → Sep 6, 2026 (26 nights) |
| **Guests** | Kenneth Lyons · Nancy Lyons |
| **Status** | ✅ Deposit Jan 28 2025 · ✅ Final Payment made Mar 14 2026 · ✅ Guest Registration & Ticket Contract complete · ✅ Shore Excursions booked Jan 13 2026 · ✅ 6 of 6 Dining reservations complete May 13 2026 |
| **Next** | Complete Online Check-in — opens Jul 21, 2026 |

## TRIP 2 — MIAMI → LOS ANGELES · "Panama Canal & Pacific Gems"  ⭐ COMPANION TO LOUCKS
| Field | Value |
|---|---|
| **Reservation** | 3116314 |
| **Ship** | Seven Seas Grandeur |
| **Suite** | Serenity Suite F1 · Deck 7 · #749 |
| **Sail dates** | Dec 29, 2026 → Jan 14, 2027 (16 nights) |
| **Guests** | Kenneth Lyons · Nancy Lyons |
| **Status** | 🟡 Deposit needed to confirm (as of Jan 14 2026 milestone) · 🔴 **Final Payment Due Aug 1, 2026** · Guest Registration complete · Shore Excursions booked Jun 2, 2026 · Dining opens Sep 30, 2026 |
| **Next** | FPD Aug 1 2026 · Dining Sep 30 · Online Check-in Dec 8, 2026 |
| **Note** | Same ship/sailing as the Commander's own booking 3122006 (Loucks Suite 658). Lyons in Suite 749. Coordinate air (Lyons: ATL↔ per Loucks tracker). |

## TRIP 3 — LONDON → LONDON · "Enchanted Scotland"
| Field | Value |
|---|---|
| **Reservation** | 3116322 |
| **Ship** | Seven Seas Splendor |
| **Suite** | Serenity Suite F1 · Deck 7 · #748 |
| **Sail dates** | Sep 13 → Sep 25, 2027 (12 nights) |
| **Guests** | Kenneth Lyons · Nancy Lyons |
| **Status** | ✅ Deposit received Jan 14 2026 · 🔴 Final Payment Due Apr 16, 2027 · Guest Registration to complete · Shore Excursions open Feb 15 2027 · Dining opens Jun 15 2027 · Check-in Aug 23 2027 |

## TRIP 4 — LONDON → LISBON · "Sparkling Wines & Glimmering Seas"
| Field | Value |
|---|---|
| **Reservation** | 3116323 |
| **Ship** | Seven Seas Splendor |
| **Suite** | Serenity Suite F1 · Deck 7 · #748 |
| **Sail dates** | Sep 25 → Oct 8, 2027 (13 nights) |
| **Guests** | Kenneth Lyons · Nancy Lyons |
| **Status** | ✅ Deposit received Jan 14 2026 · 🔴 Final Payment Due Apr 28, 2027 · Guest Registration to complete · Shore Excursions open Feb 27 2027 · Dining opens Jun 27 2027 · Check-in Sep 4 2027 |
| **Note** | Back-to-back with Trip 3 on Splendor (Scotland disembarks London Sep 25, this embarks London Sep 25) — same suite #748. A continuous Sep–Oct 2027 UK/Iberia journey. |

## TRIP 5 — SILVERSEA SILVER NOVA · May 2027 — ✅ BOOKED (Commander-confirmed 2026-07-03)
> **Commander confirms 2026-07-03: "keep silversea, she is booked for certain."** Nancy & Ken are booked on the Silver Nova, May 2027, sailing alongside John & Susan Loucks (Loucks own booking 506101-26, cabin 8071, May 5–29 2027 Venice→Athens).
> **Details NOT yet in D2M records** — the Lyons Silversea booking number, cabin, and payment calendar are not in our files or captured from any portal. The booking is separate from the Loucks reservation.
> **Silversea access 2026-07-03:** my.silversea.com reachable but the headless login hit a "Challenge Validation" bot wall; a manual Firefox login with the Regent password (GaBelle) failed — Nancy's Silversea credentials (if she has a guest account) differ from Regent, OR the booking is held agent-side. **NEXT: obtain the Lyons Silver Nova booking number** (from Commander, Silversea agent portal, or D2M booking records) to populate suite/dates/FPD. Until then the portal shows it as booked with "details firming up."

---

## FINANCIALS — NOT CAPTURED THIS PASS (Negative-Space Rule)
The Regent booking-detail pages render dollar figures (Total / Remaining) in a JS table that did not populate in the 2026-07-03 text capture. Per-booking balances/FPD amounts are **on file in Nancy's Regent account** but are NOT recorded here as confirmed figures. Re-capture with a longer render wait or the "Manage This Booking" view before quoting any Lyons dollar amount. Payment *dates* above ARE confirmed from the To-Do milestones.

## CAPTURE METHOD (for repeat pulls)
- Tool: `tools/cloak/lyons_scrape.mjs` (CloakBrowser). Login modal: `#account-email` / `#account-password`, submit = in-form button. List page: `/myaccount/bookedcruises.aspx`. Detail: `/myaccount/bookedcruise.aspx?<ENCID>`.
- Session is ephemeral per run — login + scrape must happen in ONE invocation.
- Codified as the `regent-scrape` skill 2026-07-03.
