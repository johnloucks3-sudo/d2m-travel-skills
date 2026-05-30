# D2M FARE WATCH REGISTRY
## Dreams2Memories Travel, LLC — Thunderbird Wing
**Created:** 2026-04-04 | **Maintained by:** COS (Hale)
**Total Active Watches:** 15

---

## ALERT LOGIC

| Booking Status | Alert Below | Alert Above | Purpose |
|---|---|---|---|
| PAID / booked | Paid price −10% | none | Refare opportunity |
| NOT BOOKED (flight) | Est. fair price −23% | Est. fair price +45% | Buy signal / urgency |

---

## ACTIVE WATCHES — CHRONOLOGICAL

### 🚢 APRIL 2026

| Watch ID | Client | Itinerary | Travel Date | Price/pp | Total | Alert Below | Status |
|---|---|---|---|---|---|---|---|
| `westbrook-silver-nova-pacific` | Westbrook (Ron+Lindy) | Silver Nova Trans-Pacific, Cabin 7031 (566904-25) | Apr 23, 2026 | $5,400 | $10,800 | $4,860 | PAID ✅ |
| `loucks-silver-nova-pacific` | Loucks Personal (John+Susie) | Silver Nova Trans-Pacific, Cabin 8075 (566910-25) | Apr 23, 2026 | $5,400 | $10,800 | $4,860 | PAID ✅ |

> ⚠️ Both Silver Nova bookings are **non-D2M** (Perx Interline/SkyLux). Info watches only — refare would route through SkyLux (Jenna Woodcock), not D2M channels.

---

### 🚢 JUNE–JULY 2026

| Watch ID | Client | Itinerary | Travel Date | Price/pp | Total | Alert Below | Status |
|---|---|---|---|---|---|---|---|
| `mcleod-silver-muse-med-jun2026` | McLeod/McGlasson | Silver Muse Mediterranean, Suite 617 (298475-25) | Jun 23, 2026 | $7,200 ⚠️ | $14,400 | $6,480 | PAID ✅ |
| `mcleod-flights-den-fco-jun2026` | McLeod/McGlasson | DEN→FCO Jun 18 (Business — booked) | Jun 18, 2026 | $3,500 ⚠️ | $7,000 | $3,150 | BOOKED ✅ |
| `mcleod-flights-vce-den-jul2026` | McLeod/McGlasson | VCE→DEN Jul 6 via Toronto (Business — booked) | Jul 6, 2026 | $3,200 ⚠️ | $6,400 | $2,880 | BOOKED ✅ |

> ⚠️ McLeod prices are **estimates** — TESS auth required for exact fares. Run `tess_get_booking 298475-25` when authenticated. Non-use credit ~$100pp on VCE→DEN on file.

---

### 🚢 AUGUST 2026

| Watch ID | Client | Itinerary | Travel Date | Price/pp | Total | Alert Below | Status |
|---|---|---|---|---|---|---|---|
| `lyons-splendor-athens-ny-cruise` | Lyons (Nancy+Ken) | Regent Splendor Athens→NY, Suite 847 (2979301) | Aug 11, 2026 | $10,625 | $21,250 | $9,562 | PAID ✅ |
| `furlow-grandeur-scandinavia-cruise` | Furlow (John+Missy) | Regent Grandeur Scandinavia, Suite 827 (3071222) | Aug 29, 2026 | $9,618 | $19,236 | $8,656 | PAID ✅ |
| `nichols-grandeur-scandinavia-cruise` | Nichols (Larry+Heidi) | Regent Grandeur Scandinavia, Suite 939 (3078056) | Aug 29, 2026 | $9,448 | $18,896 | $8,503 | PAID ✅ |
| `ely-darrow-grandeur-scandinavia-cruise` | Ely/Darrow (Al+Amy) | Regent Grandeur Scandinavia, Suite 1212 (3096289) | Aug 29, 2026 | $10,320 | $20,640 | $9,288 | PAID ✅ |

---

### 🚢✈️ DECEMBER 2026

| Watch ID | Client | Itinerary | Travel Date | Price/pp | Total | Alert Below | Alert Above | Status |
|---|---|---|---|---|---|---|---|---|
| `kuklinski-viking-panama-dv1` | Kuklinski ×4 (Kyle+Rosalie, Roger+Nick) | Viking Mars Panama Canal, DV1 (9593880+9593873) | Dec 17, 2026 | $3,799 | $15,196 | $3,419 | — | PAID ✅ |
| `kuklinski-viking-panama-v1` | Morton/Dodge (Josh+Erica) | Viking Mars Panama Canal, V1-Veranda (9595029) | Dec 17, 2026 | $3,099 | $6,198 | $2,789 | — | PAID ✅ |
| `kuklinski-flights-ric-pty` | Kuklinski ×4 | RIC→PTY Dec 17 (NOT BOOKED) | Dec 17, 2026 | $550 est | $2,200 | $425 | $800 | NOT BOOKED ⚠️ |
| `morton-dodge-flights-rsw-pty` | Morton/Dodge | RSW→PTY Dec 17 (NOT BOOKED) | Dec 17, 2026 | $420 est | $840 | $320 | $650 | NOT BOOKED ⚠️ |
| `mcleod-regent-grandeur-dec2026` | McLeod/McGlasson | Regent Grandeur Lesser Antilles, Suite 863 (2984034) | Dec 19, 2026 | $7,700 ⚠️ | $15,400 | $6,930 | — | FPD Jul 22 $12,393 |
| `loucks-regent-grandeur-panama-dec2026` | Loucks (John+Susie) | Regent Grandeur Panama Canal, Suite 658 (3122006) | Dec 29, 2026 | $12,899 | $25,798 | $11,609 | — | FPD Aug 1 $24,798 |

---

## OPEN ACTION ITEMS

| Priority | Action | Owner | Deadline |
|---|---|---|---|
| **P1** | Authenticate TESS — pull exact pricing for McLeod Silver Muse (298475-25) and Regent Grandeur Dec 2026 (2984034). Update watches. | COS | Next auth session |
| **P1** | Book Kuklinski flights RIC→PTY (4 pax, Dec 17). Alert already set — buy if ≤$425pp. | Dani/COS | ASAP — prices moving |
| **P1** | Book Morton/Dodge flights RSW→PTY (2 pax, Dec 17). Alert set — buy if ≤$320pp. | Dani/COS | ASAP |
| **P2** | Pull McLeod DEN→FCO and VCE→DEN actual paid fares from PNRs — update watch baselines. | COS | Next McLeod touchpoint |
| **P3** | Monitor Loucks Regent Panama Canal refare — FPD not until Aug 1. | COS | Ongoing |

---

## WATCH COVERAGE — BY CLIENT

| Client | Trips Covered | Flights Covered | Gaps |
|---|---|---|---|
| Westbrook | ✅ Silver Nova cruise | n/a (SkyLux) | None |
| Loucks Personal | ✅ Silver Nova cruise, Regent Panama Canal | None | Loucks Panama flights not booked (COS→MIA, LAX→COS) |
| McLeod/McGlasson | ✅ Silver Muse cruise, Regent Dec cruise | ✅ DEN→FCO, VCE→DEN | Prices estimated — confirm TESS |
| Furlow | ✅ Grandeur Scandinavia | n/a (client-booked) | — |
| Nichols | ✅ Grandeur Scandinavia | n/a (client-booked) | — |
| Ely/Darrow | ✅ Grandeur Scandinavia | n/a (client-booked) | — |
| Lyons | ✅ Splendor Athens→NY | n/a (client-booked) | — |
| Kuklinski | ✅ Viking Mars cruise | ⚠️ RIC→PTY NOT BOOKED | Book flights |
| Morton/Dodge | ✅ Viking Mars cruise | ⚠️ RSW→PTY NOT BOOKED | Book flights |
| McLeran | — | — | PROSPECT — no active booking |

---

## ESTIMATED D2M PORTFOLIO VALUE (WATCHED)

| Category | Total Value |
|---|---|
| Cruise bookings (all clients) | ~$180,000 |
| Flight bookings (all) | ~$20,000 |
| **Total under watch** | **~$200,000** |

---

*Registry maintained by Thunderbird OS — COS Hale. Update after every new booking or price change.*
*Tool: `mcp__thunderbird__fare_watch_add/list/check` — DB: Thunderbird fare watch SQLite*
