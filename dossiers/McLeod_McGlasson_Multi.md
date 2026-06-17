---
client: McLeod McGlasson
full_name: Erik Wiedenbach McLeod + Melissa Etola McGlasson
relationship: client
status: active
contact_hold: true
contact_hold_until: 2026-07-07
contact_hold_reason: "Commander 2026-06-13 — McLeod/McGlasson aboard Silver Muse (depart 2026-06-23, return ~2026-07-06). NO lifecycle products until return. All blackboard TPs set scheduled->hold. Reactivate post-Jul-7."
note: BEST CLIENT — 4 active bookings across 3 cruise lines

# Booking 1 — CURRENT TRIP (T-9)
booking_1: "298475-25"
booking_1_ship: Silver Muse
booking_1_departure: 2026-06-23
booking_1_fpd: 2026-01-24
booking_1_fpd_amount: 27813.32
booking_1_fpd_amount_verified_date: 2026-06-09
booking_1_fpd_amount_source: invoice
booking_1_payment_status: paid_in_full
booking_1_harlan_signoff: "Confirmed: $27,813.32 PAID IN FULL, source: Silversea final invoice 298475-25 dated 20-Jan-26"

# Booking 2 — FPD ORANGE (43 days)
booking_2: "2984034"
booking_2_ship: SS Grandeur
booking_2_departure: 2026-12-19
booking_2_fpd: 2026-07-22
booking_2_fpd_amount: 11943.15
booking_2_fpd_amount_verified_date: 2026-06-09
booking_2_fpd_amount_source: invoice
booking_2_payment_status: deposit_only
booking_2_harlan_signoff: "Confirmed: balance_due=$11,943.15, FPD Jul-22-2026 (43 DAYS), source: Regent invoice 2984034 dated 23-May-26"

# Booking 3 — Princess Mexico Riviera
booking_3: "8X6PGQ"
booking_3_ship: Discovery Princess
booking_3_departure: 2027-03-13
booking_3_fpd: 2026-12-13
booking_3_fpd_amount: 6062.00
booking_3_fpd_amount_verified_date: 2026-06-09
booking_3_fpd_amount_source: invoice
booking_3_payment_status: deposit_only
booking_3_harlan_signoff: "Confirmed: $200 deposit paid (FCC), gross balance $6,222 due Dec-13-2026, source: Princess confirmation 8X6PGQ dated Mar-21-2025"

# Booking 4 — Regent Prestige Dec 2027
booking_4: "3114500"
booking_4_ship: SS Prestige
booking_4_departure: 2027-12-18
booking_4_fpd: 2027-07-21
booking_4_total: 15098.00
booking_4_balance_due: 14598.00
booking_4_fpd_amount: 14598.00
booking_4_fpd_amount_verified_date: 2026-06-09
booking_4_fpd_amount_source: portal
booking_4_payment_status: deposit_only
booking_4_harlan_signoff: "Confirmed: total=$15,098.00, paid=$500.00, balance_due=$14,598.00, FPD 2027-07-21, source: Regent portal 2026-06-02 + invoice 3114500 dated 11-Jan-26"

# Per-booking completed_tps (multi-booking client — resolve per booking, not trip-level)
booking_1_completed_tps: ["4.1", "4.2", "4.3", "4.4", "4.5"]   # Silver Muse PAID IN FULL ($27,813.32, FPD Jan 24 passed). Payment sequence verifiably done.
booking_2_completed_tps: ["0.5"]   # Grandeur 2984034: 0.5 Booking Validation on record (lifecycle doc); guest reg COMPLETE both. FPD Jul 22 FUTURE → payment TPs NOT done. Contact-held until Jul 7.
booking_3_completed_tps: []   # Princess 8X6PGQ: deposit only, FPD Dec 13 2026 future. Nothing verifiably complete beyond deposit. $6,062 vs $6,222 figure unreconciled.
booking_4_completed_tps: []   # Prestige 3114500: deposit only, FPD Jul 21 2027 future. Nothing verifiably complete beyond deposit.
completed_tps_basis: "Per-booking. Silver Muse paid in full → payment TPs closed. Grandeur 0.5 validation sent + guest reg complete. Princess/Prestige: deposit only, future FPD, no TPs to close. Future-FPD payment TPs deliberately NOT marked complete."
completed_tps: []   # top-level intentionally empty — McLeod is multi-booking; use per-booking keys above
---

# CLIENT DOSSIER — Erik McLeod & Melissa McGlasson
## Multiple Bookings | Dreams2Memories Travel, LLC
### ⭐ BEST CLIENT — 4 Active Bookings Across 3 Cruise Lines

> 🟡 **FPD ALERT: Booking 2984034 (Regent Grandeur Dec 2026) — $11,943.15 DUE JULY 22, 2026**
> ⏸️ **DEFERRED: DO NOT CONTACT UNTIL AFTER JULY 6** — client is on Silver Muse Jun 23–Jul 6. FPD window: Jul 6–Jul 22 (16 days). Commander directive 2026-06-09.

> 📇 **THIS IS THE RELATIONSHIP HUB — NOT the scheduling source (split 2026-06-09).**
> Each trip now has its own engine-scheduled per-booking dossier:
> - Silver Muse (current, departing Jun 23) → `McLeod_Erik_Melissa_SilverMuse_Complete.md`
> - Grandeur Lesser Antilles (Dec 2026) → `McLeod_Grandeur_LesserAntilles_2984034.md`
> - Princess Mexico Riviera (Mar 2027) → `McLeod_Princess_MexicoRiviera_8X6PGQ.md`
> - Prestige Season to Cheer (Dec 2027) → `McLeod_Prestige_SeasonToCheer_3114500.md`
>
> The lifecycle engine reads those per-booking files (one record per file). This hub
> holds cross-trip relationship context, preferences, and the issues log only.

---

## QUICK REFERENCE

| Field | Value |
|-------|-------|
| **Clients** | Erik Wiedenbach McLeod + Melissa Etola McGlasson |
| **Home** | 1414 Armstrong, Longmont, CO |
| **Phones** | Erik: 303-949-0857 |
| **Emails** | Erik: emcleod@gmail.com · Melissa: memcglas@gmail.com |
| **Primary Booking** | Silver Muse Mediterranean, Jun 23–Jul 3, 2026 |
| **Status** | PAID IN FULL ($27,813.32) |

completed_tps: []
---

## ACTIVE BOOKINGS

| Booking | Supplier | Ship | Dates | FPD | Balance | Status | Cabin |
|---------|----------|------|-------|-----|---------|--------|-------|
| 298475-25 | Silversea | Silver Muse | Jun 23–Jul 3, 2026 | Jan 24 ✅ | **PAID** | T-9 ACTIVE | Suite 617, Classic Veranda |
| **2984034** | **Regent** | **SS Grandeur** | **Dec 19–29, 2026** | **🔴 Jul 22** | **$11,943.15** | **DEPOSIT ONLY** | **Suite 863, E-Concierge (UPGRADED)** |
| 8X6PGQ | Princess | Discovery Princess | Mar 13–20, 2027 | Dec 13, 2026 | ~$6,062 | Deposit only | D727, S3, Queen, Aft |
| 3114500 | Regent | SS Prestige | Dec 18–28, 2027 | Jul 21, 2027 | **$14,598.00** | Future | Suite 820, D-Concierge |

---

## ISSUES NEEDING RESOLUTION
**COO Assessment — Col Victoria Hale | Last Updated: Apr 26, 2026**

| Issue | Status | Owner | Target Resolution | Impact |
|-------|--------|-------|-------------------|--------|
| **Silver Muse Transfers (CRITICAL CLIENT PAIN POINT)** | Open | Commander + Dani | May 15, 2026 | Client satisfaction at risk |
| — Melissa frustrated with Silversea inability to cover Rome→ship, ship→Venice legs | Escalated | — | Lock final transfer plan | **PRIMARY irritant** |
| — Silversea confirms: FCO→Baglioni NOT complimentary (awaiting goodwill decision by Mar 30) | Pending Decision | Silversea/Dani | May 1, 2026 | $143–$209 exposure |
| — Baglioni→Civitavecchia transfer: Silversea Group Transfer confirmed; private option researched | In Progress | Dani | May 10, 2026 | Client clarity |
| — Venice Fusina→Hilton Molino Stucky: ✅ CONFIRMED complimentary (Hilton is contracted) | Confirmed | Silversea | — | ✅ Resolved |
| — Venice Hilton→VCE airport Jul 6 12:20 PM: NOT YET CONFIRMED | Open | Dani | May 15, 2026 | Return flight logistics |
| — Private water taxi research (Fusina direct→Stucky dock): Venice Guide & Boat (€200–€225) quoted | In Progress | Dani | May 10, 2026 | Cost optimization |
| **Grandeur Dec 2026 Suite Upgrade Bid** | Pending | — | May 1, 2026 | Revenue opportunity |
| — Clients bid on Medallion Suite upgrade; Regent acceptance status unknown ⚠️ DO NOT REFERENCE IN REGENT CLIENT EMAILS (Commander 2026-05-28: belongs to Silversea context) | Pending | — | — | Track only |
| **Rome Dining Reservations (Melissa Request)** | Open | Dani | May 30, 2026 | Client experience |
| — Four starred options identified: Sistina 52 (5★), Diana's Place (1★), Moma (1★ Michelin), La Pergola (3★ Michelin) | Researched | Dani | Confirm preferences + book | Dining locked |
| — High-demand tables (La Pergola, Moma) require early booking; confirm Melissa's interest before May 15 | Open | Dani | May 15, 2026 | Reservation availability |
| **Venice Dining Research** | Open | Dani | May 20, 2026 | 3-night itinerary |
| — Melissa prioritizes seafood (living in Colorado makes it special). 3 dinners needed for Jul 3–6 | Open | Dani | Research + present options | Experience |

---

## COMMANDER NOTES LOG
**Directive Authority: John Loucks | Standing Order 25 MAR 2026**

| Date | Source | Directive / Note | Status |
|------|--------|------------------|--------|
| **Apr 27, 2026** | Commander | **MELISSA TRANSFER FRUSTRATION — CRITICAL CLIENT PAIN POINT:** Melissa is NOT pleased with Silversea's handling of transportation. Lack of coverage (Rome→hotel, hotel→ship, ship→Venice, Venice→airport) is her primary irritant. All client comms on transfers must be explicitly CONDITIONAL until final confirmations locked. Rome transfers pending Blacklane quote (mid-May). Venice water taxi confirmation required by May 10. **Do NOT present transfers as confirmed in any client-facing email.** | 🔴 Active |
| **Apr 26, 2026** | Commander | Insurance status: ✅ **CONFIRMED** — Seven Corners Insurance, $30K coverage, $1,300 paid. Excellent deal. Update dossier immediately. | ✅ Done |
| **Mar 25, 2026** | Commander (WhatsApp) | **DINING PRIORITIES:** No major dinner requirements in Rome; Venice is the priority. Seafood is the big draw in Venice (they live in Colorado — seafood is special). | ✅ Integrated |
| **Mar 25, 2026** | Commander (WhatsApp) | **TRANSFER ASSESSMENT — DEFINITIVE:** Silversea WILL NOT cover: (1) Airport→hotel (arriving early); (2) Baglioni→ship (not SS hotel); (3) Ship→Stucky effectively (will drop in middle of Venice only); (4) Water taxi Stucky→VCE airport. May be able to "glom onto" Rome hotel→ship transfer if they show up at SS hotel (verbal only, no guarantee). Commander can likely beat Baglioni's quoted transfer price. **Venice is the priority focus.** | ✅ Integrated |
| **Mar 25, 2026** | Commander (WhatsApp) | **Baglioni Rome Transfer Quote:** Mercedes E-class €143 (max 2 bags); Mercedes Minivan €209. Commander believes he can source better. | 🟡 Open |
| **Mar 19, 2026** | Commander (Telegram) | **DOCK VERIFIED — FUSINA, NOT Marghera.** Silver Muse docks at Fusina Cruise Terminal (opened Aug 2024). "Marghera" colloquially used but Fusina is correct. Stucky dock confirmed — private water landing on Giudecca Canal, tactically optimal. | ✅ Integrated |
| **Mar 19, 2026** | Commander (Telegram) | **SUITE BID:** Clients placed bid on Medallion Suite — two separate classes bid. Status pending Regent acceptance. | 🟡 Open |
| **Mar 19, 2026** | Commander (Telegram) | **WIN — SEALED:** Hilton Molino Stucky booked *independently* by clients. Pure attribution. Intel trusted enough they acted without handholding. Grant story confirmed. | ✅ Secured |

---

## SILVER MUSE MEDITERRANEAN — COMPLETE TRAVEL PLAN

### ROME PRE-CRUISE (Jun 18–23, 2026)

**Flights — Outbound**
| Leg | Flight | Route | Depart | Arrive | PNR | Seats | Class |
|-----|--------|-------|--------|--------|-----|-------|-------|
| OUT | UA 177 | Denver → Rome Fiumicino | Jun 18, 5:45 PM | Jun 19, 12:20 PM | NFBDP6 | 3D/3F | Business Promo |

**Hotel — Rome**
- **Baglioni Hotel Regina** — Grand Deluxe Room
- Check-in: Fri, Jun 19, 2:00 PM | Check-out: Tue, Jun 23, 12:00 PM
- **4 nights** ($1,800 estimate, client-booked)
- Location: Steps from Trevi Fountain
- Amenities: €143–€209 airport transfer quote (Melissa researched alternatives)

**Pre-Cruise Excursions (All Booked via GetYourGuide)**

| Date | Activity | Time | Duration | Cost | Highlights |
|------|----------|------|----------|------|-----------|
| Jun 20 | Colosseum with Arena Floor, Roman Forum & Palatine Hill — Guided Tour | 10:00 AM | 3h | $301.86 | Arena floor access (most visitors don't see this); full morning in ancient Rome |
| Jun 21 (AM) | Trenitalia Frecciarossa 8502 (Business Class) | 6:45 AM | 1h 45m | Train booking JJQ6Z5 | Rome→Florence |
| Jun 21 (AM) | Uffizi Gallery, Michelangelo's David & Gelato Walk with Art Historian | 9:30 AM | 3h | $257.96–$368.52 | Two of the world's greatest collections + authentic gelato |
| Jun 21 (PM) | Trenitalia Frecciarossa 9431 (Executive Class) | 6:45 PM | 1h 45m | Train return | Florence→Rome |
| Jun 22 | Vatican Museums, Sistine Chapel & St. Peter's Basilica — with Dome Climb | 8:30 AM | 4h | $766.84 | Dome climb is the move; view from the top is unforgettable |

**Rome Dining Options (Research Complete, Reservations Pending)**

| Restaurant | Rating | Style | Location | Contact | Reservation Status |
|------------|--------|-------|----------|---------|-------------------|
| **Sistina 52** ⭐⭐ | 5★ | Modern Italian | Trevi area, 7 min walk from hotel | Researched | **To Book** |
| **Diana's Place** ⭐ | 1★ Michelin | Italian | Trastevere area, 12 min walk | Researched | **To Book** |
| **Colline Emiliane** | Starred pick | Regional | Emilia-Romagna | Researched | **To Book** |
| **La Pergola** | 3★ Michelin | Fine dining | Waldorf Cavalieri (Capitoline Hill) | High demand; weeks/months out | **ACTION:** Reach out now if priority |
| **Moma** | 1★ Michelin | Tasting menu | Central location | ~$130/person | **ACTION:** Reach out now if priority |

**Commander's Assessment:** Melissa's research shows excellent taste. Sistina 52, Diana's Place, and Colline Emiliane should be reachable with shorter notice. La Pergola and Moma book weeks–months out; confirm interest before May 15.

---

### SILVER MUSE CRUISE (Jun 23–Jul 3, 2026)

**Booking Details**
- **Voyage:** SM260623010 | **Suite 617** — Classic Veranda
- **Itinerary:** Civitavecchia (Rome) embark → Fusina (Venice) disembark
- **Duration:** 10 nights | **Status:** ✅ **PAID IN FULL ($27,813.32)**

**Financial Summary**
| Item | Amount |
|------|--------|
| Cruise base (2 pax) | $27,813.32 |
| Specialty dining (La Dame, night of Jun 24 — Erik's birthday) | $120 |
| Shore excursions (Kotor speedboat, Dubrovnik beach) | $596 |
| **Total outstanding for cruise** | **$716** |

**Ports of Call & Excursions**

| Date | Port | Excursion | Time | Duration | Cost | Notes |
|------|------|-----------|------|----------|------|-------|
| Jun 24 | Naples, Italy | Ruins of Herculanum | 08:45 | 3h 30m | Included | UNESCO World Heritage |
| Jun 25 | Giardini Naxos, Sicily | Greek & Roman Taormina | 09:30 | 4h | Included | Ancient history |
| Jun 26 | Siracusa, Sicily | Baroque Town of Noto | 08:45 | 3h 30m | Included | UNESCO town |
| Jun 27 | Valletta, Malta | Game of Thrones locations | 09:15 | 4h | Included | GoT fans + history |
| Jun 28 | Day at Sea | — | — | — | — | Relaxation |
| Jun 29 | Kotor, Montenegro | Speedboat Adventure to Blue Cave ⭐ | 08:30 | 4h | **$318** | Scenic speedboat, Blue Grotto |
| Jun 30 | Dubrovnik, Croatia | Day at the Beach Club ⭐ | 09:00 | 5h | **$278** | Beach access, Club amenities |
| Jul 01 | Split, Croatia | UNESCO World Heritage Sites | 08:45 | 4h 30m | Included | Diocletian's Palace |
| Jul 02 | Zadar, Croatia | Zadar, Nin Salt Works & Royal Vineyards | 08:45 | 5h | Included | Regional culture + wine |
| Jul 03 | Fusina (Venice) | Disembark | AM | — | — | Onward to Hilton Molino Stucky |

**Specialty Dining (Silversea Portal — Booked)**

| Date | Restaurant | Time | Cost (2 pax) | Notes |
|------|-----------|------|--------------|-------|
| Jun 24 | La Dame | 19:30/20:30 | $120 | Fine dining specialty |
| Jun 26 | The Grill | 19:30/20:30 | Complimentary | Main dining alternative |
| Jun 28 | Silver Note | 19:00/20:00 | Complimentary | Main dining |
| Jul 01 | La Terrazza | 19:30/20:30 | Complimentary | Main dining |

**Transfers (Silversea-Arranged)**

| Transfer | Date/Leg | Status | Notes |
|----------|----------|--------|-------|
| Pre-cruise home (Longmont→DEN) | Jun 18 | ✅ CONFIRMED | Blacklane complimentary |
| Airport→hotel (FCO→Baglioni) | Jun 19 | ⚠️ **PENDING GOODWILL** | Awaiting Silversea decision; €143–€209 at cost |
| Hotel→pier (Baglioni→Civitavecchia) | Jun 23 | ✅ CONFIRMED | Silversea group transfer |
| Pier→hotel (Fusina→Hilton) | Jul 3 | ✅ **CONFIRMED COMPLIMENTARY** | Hilton is contracted hotel; Silversea covers |
| Hotel→airport (Hilton→VCE) | Jul 6 | ⏳ **OPEN** | Needs confirmation for 12:20 PM AC817 departure |
| Post-cruise home (DEN→Longmont) | Jul 6 | ✅ CONFIRMED | Blacklane complimentary |

---

### VENICE POST-CRUISE (Jul 3–6, 2026)

**Flights — Return**
| Leg | Flight | Route | Depart | Arrive | PNR | Seats | Class |
|-----|--------|-------|--------|--------|-----|-------|-------|
| RET-1 | AC 817 | Venice → Toronto | Jul 6, 12:20 PM | Jul 6, 3:45 PM | CXNT6Q | 3A/4A | Business |
| RET-2 | AC 1041 | Toronto → Denver | Jul 6, 6:40 PM | Jul 6, 8:22 PM | CXNT6Q | 2A/2C | Business |

**Hotel — Venice**
- **Hilton Molino Stucky Venice** — Executive Suite
- Check-in: Fri, Jul 3, 3:00 PM | Check-out: Mon, Jul 6, 11:00 AM
- **3 nights** ($2,696.35)
- Location: Giudecca island (former flour mill, converted luxury hotel)
- Key Amenity: **Private water dock on Giudecca Canal** — eliminates bridge luggage drag; Silversea pier-to-hotel transfer arrives directly at dock
- Complimentary shuttle: Zattere + San Zaccaria stops, 8 AM–midnight (for city exploration)
- **Skyline Rooftop Bar:** Aperitivo with Venice skyline on arrival evening

**Post-Cruise Activities (Venice Dining Research Needed)**

**Dining Priority:** Melissa prioritizes seafood (living in Colorado makes it special). **3 dinners needed for Jul 3–6.**

*Preliminary Options (to be vetted):*
- **Ai Artisti** — Casual seafood, campo-side
- **Regina Sconta** — Traditional Venetian, seafood-forward
- **Hostaria Castello** — Neighborhood gem, cicchetti + full meals

**Commander Assessment:** Research ongoing. Melissa expects D2M to present curated options with rationale, not raw list.

---

## DOCUMENTS & REQUIREMENTS

**Passport & Entry**
| Document | Traveler | Valid? | Expires | Notes | Status |
|----------|----------|--------|---------|-------|--------|
| Passport | Erik Wiedenbach McLeod | ✅ Yes | TBD (need to verify) | Passport #: ?09468788 | **Verify expiration** |
| Passport | Melissa Etola McGlasson | ✅ Yes | TBD (need to verify) | Passport #: 582543236 | **Verify expiration** |

**Schengen Entry Requirements**
- **US citizens:** Visa-free entry to Italy/Schengen zone
- **Requirement:** Passport valid for **6+ months beyond return date** (return Jul 6 → need valid through Jan 2027 minimum)
- **ETIAS:** EU Entry/Exit System (launching 2025–2026). Currently not required; recommend monitoring EU updates for implementation timeline. **ACTION:** Check Schengen/ETIAS requirements by May 1.
- **Return to US:** Direct flight AC1041 arrives Denver 8:22 PM Jul 6 (same-day return through Toronto connection)

**Insurance**
| Policy | Provider | Coverage | Premium | Status | Notes |
|--------|----------|----------|---------|--------|-------|
| Travel Insurance | Seven Corners Insurance | $30,000 coverage | $1,300 | ✅ **CONFIRMED PAID** | Excellent deal; obtain policy document for records |

**Digital Backups (Recommended)**
- Passport copies (scanned or photo): Store in secure cloud (Google Drive with Commander access)
- Flight confirmations (PNRs NFBDP6, CXNT6Q): Email copies to johnloucks3@gmail.com
- Hotel confirmations (Baglioni, Molino Stucky): Digital copies in D2M drive
- Insurance policy: PDF stored with dossier in Google Drive
- Credit card info: Secure backup separate from this dossier
- Emergency contacts: Digitally accessible while traveling

**Pre-Departure Checklist (Melissa's Planning List)**
- ✅ Passports (validity check required)
- ✅ ETIAS/Schengen confirmation (by May 1)
- ✅ Travel insurance (Seven Corners, confirmed)
- ✅ Hotel confirmations (Baglioni + Molino Stucky received)
- ✅ Flight confirmations (all three legs confirmed)
- ✅ Excursion confirmations (Rome + cruise shore excursions booked)
- ⏳ Rome dining reservations (PENDING — Dani to book by May 30)
- ⏳ Venice dining (PENDING — research + book by May 20)
- ⏳ All transfer confirmations (Rome, Venice, airports)
- ✅ Mail hold (Commander coordinates)
- ✅ Lawn care / home prep (Commander coordinates)
- ✅ Packing (clients manage)

---

## VALIDATION MATRIX — Silver Muse Mediterranean (SM260623010)
**Departure:** Jun 18, 2026 | **FINAL Validation:** Jun 4, 2026
**Monthly Validations:** Mar 25 · Apr 25 · May 25 | **Schedule:** 25th of each month

| # | Category | Item | Required | Status | Details |
|---|----------|------|----------|--------|---------|
| 1 | Documents | Passports valid 6+ months | YES | **PENDING VERIFICATION** | Erik: ?09468788 / Melissa: 582543236 — need to confirm expiration dates |
| 2 | Documents | Visa / ETIAS requirements | YES | **PENDING RESEARCH** | Italy/EU entry; monitor ETIAS implementation; US passport OK |
| 3 | Insurance | Travel insurance policy | YES | **✅ CONFIRMED** | Seven Corners $30K, $1,300 paid |
| 4 | Flights | Outbound (DEN→FCO) | YES | **✅ CONFIRMED** | UA 177 Jun 18 5:45 PM → Jun 19 12:20 PM |
| 5 | Flights | Outbound PNR / e-ticket | YES | **✅ CONFIRMED** | PNR: NFBDP6 |
| 6 | Flights | Outbound seats | Nice-to-have | **✅ CONFIRMED** | 3D/3F |
| 7 | Transfers | Airport→hotel (FCO→Baglioni) | YES | **⚠️ PENDING** | Awaiting Silversea goodwill decision; €143–€209 if at cost |
| 8 | Hotel | Pre-cruise (Rome, 4 nights) | YES | **✅ CONFIRMED** | Baglioni Hotel Regina, Jun 19–23 |
| 9 | Excursions | Pre-cruise Rome/Florence | Optional | **✅ BOOKED** | 3 tours + Trenitalia train booked via GetYourGuide |
| 10 | Dining | Pre-cruise dining | Optional | **⏳ PENDING BOOKING** | 5 Rome options researched; await Melissa confirmation before May 15 |
| 11 | Transfers | Hotel→port (Baglioni→Civitavecchia) | YES | **✅ CONFIRMED** | Silversea group transfer Jun 23 |
| 12 | Transfers | Home→airport pre-cruise | YES | **✅ CONFIRMED** | Silversea Private Executive (Blacklane) Longmont→DEN |
| 13 | Cruise | Booking confirmed | YES | **✅ CONFIRMED** | 298475-25, Suite 617, Silver Muse |
| 14 | Cruise | Suite assignment | YES | **✅ CONFIRMED** | 617 — Classic Veranda |
| 15 | Cruise | Payment status | YES | **✅ PAID IN FULL** | $27,813.32 |
| 16 | Cruise | Embarkation details | YES | **✅ CONFIRMED** | Civitavecchia (Rome), Jun 23 |
| 17 | Dining | Specialty dining | Optional | **✅ BOOKED** | La Dame Jun 24 ($120) — Erik's birthday · Silver Note Jun 28 · The Grill Jun 26 · La Terrazza Jul 1 |
| 18 | Excursions | Shore excursions | Optional | **✅ BOOKED** | Kotor speedboat ($318) + Dubrovnik beach ($278) = $596 |
| 19 | Cruise | Disembarkation | YES | **✅ CONFIRMED** | Fusina (Venice), Jul 3 |
| 20 | Transfers | Pier→hotel (Fusina→Molino Stucky) | YES | **✅ CONFIRMED COMPLIMENTARY** | Silversea group transfer Jul 3 (Hilton is contracted) |
| 21 | Hotel | Post-cruise (Venice, 3 nights) | YES | **✅ CONFIRMED** | Hilton Molino Stucky, Jul 3–6, Executive Suite |
| 22 | Dining | Post-cruise dining | Optional | **⏳ PENDING RESEARCH** | Melissa prioritizes seafood; 3 dinners needed Jul 3–6 |
| 23 | Excursions | Post-cruise activities | Optional | **OPEN** | Venice exploration TBD |
| 24 | Transfers | Hotel→airport (Molino Stucky→VCE) | YES | **⏳ PENDING CONFIRMATION** | Jul 6 for AC 817 12:20 PM departure |
| 25 | Flights | Return leg 1 (VCE→YYZ) | YES | **✅ CONFIRMED** | AC 817 Jul 6 12:20 PM → 3:45 PM |
| 26 | Flights | Return leg 2 (YYZ→DEN) | YES | **✅ CONFIRMED** | AC 1041 Jul 6 6:40 PM → 8:22 PM |
| 27 | Flights | Return PNR / e-ticket | YES | **✅ CONFIRMED** | PNR: CXNT6Q |
| 28 | Flights | Return seats | Nice-to-have | **✅ CONFIRMED** | 3A/4A (leg 1), 2A/2C (leg 2) |
| 29 | Transfers | Airport→home post-cruise | YES | **✅ CONFIRMED** | Silversea Private Executive (Blacklane) DEN→Longmont |
| 30 | Admin | Dossier current | YES | **✅ UPDATED APR 26** | Gold-standard format with full planning data |

**Coverage: 83%** | **Critical Gaps:** Rome transfer (pending goodwill), Venice airport transfer (pending confirmation), Venice dining (pending research), Rome dinner reservations (pending booking)

---

## FUTURE BOOKINGS — GRAND & PRESTIGE

**Grandeur — Lesser Antilles (Dec 19–29, 2026)**
- **Booking:** 2984034 | **Suite:** 863, Deck 8, Concierge E
- **FPD:** Jul 22, 2026 ($11,943.15 balance — portal verified 2026-05-28; $450 delta from prior dossier, root cause pending TESS confirmation)
- **Status:** Suite upgrade bid pending (Medallion Suite); Regent response awaited by May 1
- **⚠️ DO NOT REFERENCE IN CLIENT EMAILS re: Regent Grandeur.** Commander 2026-05-28: Medallion Suite is a Silversea suite category; this bid belongs to Silversea context if/when addressed. Not relevant to Regent Grandeur communications.
- **Regent FCC Status:** $200 outstanding from Dec 2025 Gale Hotel complaint. ACTION: Verify in TESS, apply to this booking.

**Prestige — Year-End (Dec 18–28, 2027)**
- **Booking:** 3114500 | **Suite:** 820, Deck 8, Concierge D
- **FPD:** Jul 21, 2027 ($14,598.00)
- **Status:** Future; no immediate action required

**Princess — March 2027 (Mar 13–20, 2027)**
- **Booking:** 8X6PGQ
- **Status:** Future; details TBD

---

## COMPETITIVE INTELLIGENCE

**Pavlus Travel Visibility**
- Clients have active relationship with Pavlus Travel (another travel agency)
- Dec 2025: Gale Hotel complaint submitted through Pavlus → Regent FCC processed through them
- **Risk Flag:** These clients may be contested/shared. Pavlus has booking visibility.
- **Mitigation:** Dani's direct relationship, strong personal service, and proactive communication lock the relationship.

---

## HISTORICAL INTEL (Dec 2025–Jan 2026)

**Dec 2025 Cruise (Pre-D2M)**
- **Hotel:** Gale Hotel & Residences, Miami
- **Issues:** Loud AC unit, bed smell, noise from neighboring rooms
- **Resolution:** Regent FCC $200 ($100/person) issued unprompted

**Regent FCC ($200 total)**
- **Source:** Gale Hotel complaint
- **Status:** Received per Regent confirmation
- **Application:** Applicable to any future Regent cruise (Lesser Antilles Dec 2026 or Prestige Dec 2027)
- **ACTION:** Verify in TESS system and apply to Lesser Antilles booking (soonest FPD)

**Jan 2026 Pending Items (Resolved)**
- ✅ CC call for final payment — completed prior to Silver Muse FPD (Jan 24)
- ✅ Insurance quote — Seven Corners confirmed $30K for $1,300

---

## ACTION ITEMS — PRIORITIZED

### IMMEDIATE (Complete by May 1, 2026)
- [ ] **Confirm Melissa's top Rome dining choices** — La Pergola, Moma, or Sistina 52/Diana's?
- [ ] **Book Rome dinners** — La Pergola/Moma (if priority) require outreach now; others by May 30
- [ ] **Confirm Grandeur suite upgrade status** — Regent response on Medallion Suite bid
- [ ] **Verify passport expiration dates** — Erik & Melissa; confirm 6+ months valid through Jan 2027
- [ ] **Research ETIAS/Schengen requirements** — Monitor EU timeline; confirm US citizens OK

### MAY 1–15 (Complete by May 15, 2026)
- [ ] **Rome airport transfer decision** — Confirm Silversea goodwill or source private alternative (beat €143–€209)
- [ ] **Venice water taxi confirmation** — Venice Guide & Boat quote (€200–€225); confirm booking
- [ ] **Venice airport transfer** — Secure Hilton→VCE transfer for AC 817 12:20 PM departure
- [ ] **Communicate ALL transfer confirmations to clients** — Explicitly conditional until final; no false assurance

### MAY 15–31 (Complete by May 30, 2026)
- [ ] **Rome dining reservations** — Finalize bookings for all chosen restaurants
- [ ] **Venice dining recommendations** — Research 3–5 seafood options; present with rationale

### ONGOING (Monthly / As Needed)
- [ ] **May 25 validation sweep** — Recheck all confirmations; update status
- [ ] **Grandeur planning** — Begin preliminary research for Dec 2026 booking
- [ ] **Prestige research** — Monitor for 2027 port details, excursion opening dates

---

## DESTINATION KNOWLEDGE — All Cities on Itinerary
*Added 2026-06-12 by Hale (COS) · Per Commander directive: dossier is ground truth for Dani Oracle knowledge*

### ROME (Jun 19–23 · 4 nights · Base city)
**Hotel area:** Via Veneto — walkable to Trevi Fountain (7 min), Spanish Steps (10 min), Piazza del Popolo (15 min)
**Key sights:** Colosseum/Arena Floor/Forum/Palatine (booked Jun 20, GYG) · Vatican/Sistine/Dome Climb (booked Jun 22, GYG) · Trevi Fountain (free, go at dawn) · Pantheon (small fee, no queue at open) · Piazza Navona (free, evening stroll) · Borghese Gallery (book ahead, Bernini masterworks)
**Neighborhoods:** Trastevere (medieval, best for dinner, 20 min walk) · Testaccio (food market, local pizza al taglio) · Prati (near Vatican, quieter residential)
**Dining (researched, status: pending booking):**
- Sistina 52 — 5-star modern Italian, Trevi area, 7 min walk, reachable with 1-2 days notice
- Diana's Place — 1 Michelin star, Trastevere, 12 min walk, book 1 week ahead
- Colline Emiliane — traditional Emilia-Romagna, near Spanish Steps, book 3-4 days ahead
- Aroma at Palazzo Manfredi — 1 Michelin star, rooftop with Colosseum view at night, ~€180-220/pp, books months ahead
- Glass Hostaria (Trastevere) — 1 Michelin star, Chef Cristina Bowerman, ~€100-140/pp
- La Pergola (Waldorf Cavalieri) — 3 Michelin stars, €250+/pp, books 2-3 months ahead
**Transport:** Walk in centro storico · Metro A (red line) connects Via Veneto to Vatican/Termini · Fixed taxi rate Termini→centro ~€15 · Trenitalia Frecciarossa departs Roma Termini (30 min taxi/Metro from Baglioni)

### FLORENCE (Jun 21 · Day trip from Rome)
**Access:** Trenitalia Frecciarossa 8502 · 6:45 AM · Roma Termini → Firenze S.M.N. · 1h 45m · Ref JJQ6Z5
**Key sights:** Uffizi (Botticelli's Birth of Venus, da Vinci, Raphael, Titian) · Accademia (Michelangelo's David, 5.17m marble, 1504) · Duomo/Brunelleschi's Dome (exterior free) · Ponte Vecchio (gold/silver shops on medieval bridge) · Piazza della Signoria (outdoor museum)
**Gelato:** Gelateria dei Neri (near Uffizi, art historians' favorite) · Gelateria del Campanile (near Accademia)
**Quick lunch:** Buca Mario (oldest restaurant in Florence, near Piazza della Signoria) · Trattoria Mario (cash only, communal tables, lunch only, ribollita)
**Station tip:** Luggage storage at SMN station ~€6/bag — leave bags and explore hands-free
**Return:** Frecciarossa 9431 (Executive Class) · 6:45 PM · Firenze S.M.N. → Roma Termini · arrives ~8:30 PM

### NAPLES (Jun 24 · Port call · Excursion: Herculaneum)
**Herculaneum vs Pompeii:** Better preserved (pyroclastic surge sealed it instantly, wood and fabric survived), smaller, less crowded, no Vesuvius climb required
**If time after excursion:** Spaccanapoli (straight cut through city) · Quartieri Spagnoli (street art, coffee)
**Pizza:** Da Michele (Via Cesare Sersale 1, cash only, 2 options only, legendary, expect queue) · Sorbillo (Spaccanapoli, longer menu)
**Coffee tip:** Naples espresso is the best in Italy — stand at any bar, €1, never sit
**Transport:** Port → Herculaneum station by Circumvesuviana train (20 min) or Silversea bus

### GIARDINI NAXOS / TAORMINA (Jun 25 · Port call · Excursion: Greek & Roman Taormina)
**Taormina access:** 204m above sea level · cable car (Funivia) from Giardini Naxos €3/way · tour bus included
**Greek Theatre (Teatro Greco):** Built 3rd century BC · Mount Etna backdrop is most photographed view in Sicily · summer concerts performed here
**Streets:** Via Teatro Greco (boutiques, views) · Corso Umberto (main café/shopping street) · Villa Comunale gardens (free, panoramic views)
**Food:** Pasticceria Etna — granita con brioche, essential Sicilian breakfast
**Etna:** Visible from virtually everywhere — ask guide for best photo angle

### SIRACUSA / NOTO (Jun 26 · Port call · Excursion: Baroque Town of Noto)
**Noto:** 32km from port (excursion bus) · UNESCO Baroque World Heritage · rebuilt after 1693 earthquake in pure golden limestone Baroque
**Cathedral of San Nicolò:** Baroque masterpiece, facade best at 10 AM when light hits it directly
**Caffè Sicilia (Via Vittorio Emanuele 125, Noto):** Best granita in Sicily (pistachio, almond) · Chef Corrado Assenza has international reputation
**Ortygia (Siracusa island, if time after tour):** Greek Temple of Athena columns absorbed into Norman cathedral · Arethusa Spring (papyrus grows, only place outside Africa) · Piazza del Duomo (one of Europe's finest Baroque squares)

### VALLETTA (Jun 27 · Port call · Excursion: Game of Thrones Filming Locations)
**Walking city:** 800m × 600m inside walls, everything reachable on foot
**St. John's Co-Cathedral:** Caravaggio's only signed painting (The Beheading of St. John) · most ornate cathedral in the Mediterranean
**Upper Barrakka Gardens:** Free · best Grand Harbour panorama in Malta
**GoT sites:** City walls = King's Landing · Mdina (nearby) = Red Keep in early seasons · Fort Ricasoli = Dragonstone scenes
**Food:** Is-Suq tal-Belt (city market, best in Valletta) · Trabuxu Bistro (wine + Maltese food) · Pastizzeria (€0.50 ricotta or mushy pea pastry, street snack)
**Transport:** Port is 10 min walk to city gate

### KOTOR (Jun 29 · Port call · Excursion: Speedboat Adventure to Blue Cave)
**Bay of Kotor:** Southernmost fjord in Europe · UNESCO World Heritage · dramatic karst mountains drop into enclosed sea
**Old Town:** Venetian-era walled city · Cathedral of St. Tryphon (1166) · Piazza d'Armi · famous for cats (Cat Museum)
**City Walls hike (if not on excursion):** 1,350 steps to San Giovanni Fortress · 1.5 hrs up · spectacular views · go before 8 AM or after 4 PM (heat)
**Blue Cave (excursion):** Only accessible by water · bioluminescent, best light at mid-morning · speedboat allows swimming
**Transport:** Old town 10 min walk from pier · entrance fee at some gates ~€3

### DUBROVNIK (Jun 30 · Port call · Excursion: Day at the Beach Club)
**City Walls walk:** 2km loop · sea on one side, terracotta rooftops on the other · €35 (skip today — beach club day)
**GoT:** Most of King's Landing was filmed in Dubrovnik · Cersei's Walk of Shame = Stradun · Purple Wedding = Rector's Palace courtyard · Red Keep exterior = Fort Lovrijenac
**Cable car:** Mount Srđ, panoramic view of walled city and islands, €30 return (highly recommended if time allows)
**Lokrum island:** 10 min boat (€20 return) · Game of Thrones Iron Throne replica · peacocks · botanical garden
**Transport:** Port 3km from old town — shuttle bus or taxi ~€10

### SPLIT (Jul 1 · Port call · Excursion: UNESCO World Heritage Sites)
**Diocletian's Palace:** Built AD 305 · entire living city center occupies its walls · ~3,000 residents live inside a Roman palace
**Peristyle:** Open-air courtyard at center · once the emperor's reception hall · now hosts summer concerts
**Riva Promenade:** Wide waterfront esplanade, palm trees, cafes, ship visible from here
**Food:** Zora Restaurant (fresh fish, near palace) · Konoba Matejuška (Varoš neighborhood, tiny fishing harbor, locals eat here)
**Note:** Less touristy than Dubrovnik — a real working city with a real population

### ZADAR (Jul 2 · Port call · Excursion: Nin Salt Works & Royal Vineyards)
**Sea Organ (Morske orgulje):** 35 stone steps with pipes underneath · Adriatic waves produce ambient music · unique in the world · free
**Sun Salutation:** Adjacent to Sea Organ · 300 glass plates, light show at dusk · worth seeing if evening
**Roman Forum:** One of largest in the Roman Empire outside Italy · 1st century BC
**Nin Salt Works (excursion):** Hand-harvested fleur de sel · chefs in Dubrovnik and Venice pay premium for it · 18km north (excursion bus)
**Church of St. Donat:** 9th-century Byzantine pre-Romanesque cylinder · unusual shape, summer concerts

### VENICE / FUSINA (Jul 3–6 · 3 nights · Post-cruise)
**Hotel:** Hilton Molino Stucky · Giudecca Island · private water dock · Silver Muse arrives at Fusina → water taxi to hotel dock (Order 14878, €350)
**Neighborhoods:** Giudecca (hotel — quiet, residential, authentic) · Dorsoduro (artsy, Zattere promenade, Accademia) · Cannaregio (least touristy, Jewish Ghetto) · San Polo/Rialto (market, cicchetti bars) · San Marco (tourist center) · Castello (quiet residential)
**Must-see:** St. Mark's Basilica (free, go before 9:30 AM, no bags allowed — leave at hotel) · Doge's Palace (adjoining) · Rialto Bridge and market (closes noon) · Accademia (Titian, Bellini, Veronese) · Peggy Guggenheim (20th-century art, Dorsoduro)
**SEAFOOD (Melissa's priority — 3 dinners Jul 3–6):**
- Osteria Alle Testiere (Castello): 22 seats, best seafood in Venice, Chef Bruno Gavagnin — past booking window; call day-of or arrive at 6 PM opening
- Trattoria Altanella (Giudecca): 5 min walk from hotel, legendary fritto misto, cash only, book 1-2 days ahead
- La Palanca (Giudecca): Steps from hotel, canal-side, locals only, lunch only (closes 3 PM), cash preferred, €15
- Zanze XVI (Cannaregio): Local neighborhood favorite, lagoon fish, no tourists, same-day reservation
- Trattoria da Romano (Burano island): Family-run since 1919, 45 min vaporetto, legendary fritto misto
**Cicchetti (Venetian tapas):** All'Arco (near Rialto market) · Cantinone già Schiavi (Dorsoduro, wine walls) · Bacaro Jazz (San Marco area, late night)
**Day trips:** Murano glass (30 min) · Burano lace/colors (45 min) · Torcello (quiet Byzantine mosaics, oldest settlement)
**Transport:** Vaporetto Line 2 — Molino Stucky → San Marco in 15 min (€9.50/trip or €25 day pass) · free hotel shuttle to Zattere + San Zaccaria · water taxi ~€80-100 · gondola ~€100/30 min (set rate)
**Tips:** Go early to St. Mark's · Rialto market closes noon weekdays · dress modestly at churches · acqua alta (flooding) rare in June

---

## NOTES

**Grant Narrative Asset (Commander 2026-03-19):**
Hilton Molino Stucky booking demonstrates D2M's recommendation credibility. Clients booked independently based on D2M research + Commander's tactical assessment of the dock/Giudecca logistics. Pure attribution win.

**Commander Assessment (Apr 27, 2026):**
Melissa's transfer frustration is the critical client pain point. Silversea's inability to cover Rome→ship→Venice legs has eroded trust. All future communications must be explicitly conditional; no false assurance. This is the make-or-break item for June trip satisfaction.

**Voice/Tone (D2M Standard):**
Melissa is thorough, detail-oriented researcher. Erik delegates to Melissa for planning. Both appreciate expert curation over raw options. Lead with "here's what I recommend and why" not "here are your choices."

---

**Dossier Owner:** Col Victoria Hale, COS  
**Last Updated:** Jun 12, 2026, 22:30 MT — Added: destination knowledge for all 11 cities (SO-REVERIE-QC-20260612)  
**Next Validation:** Jun 23, 2026 (departure day)

---
## SILVERSEA — Special-Occasion Request (logged 2026-06-16, Commander directive "add to dossier and monitor")
- **Context:** Melissa McGlasson special-occasion request on the Silver Muse (Med, depart Jun 23). Commander emailed her this AM to establish a record; offered to arrange a special dessert at **La Dame** that evening.
- **Commander's words:** "Sent email this AM. I like to send an email to establish a record, I will follow-up on Weds if no answer. At the very least, I am certain you could order a special dessert to be served at La Dame that night."
- **MONITOR:** Follow up **Wed 2026-06-18** if no reply from Melissa. Owner: Hale.
