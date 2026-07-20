---
client: McLeod McGlasson
full_name: Erik Wiedenbach McLeod + Melissa Etola McGlasson
cruise_line: Regent Seven Seas
ship: SS Grandeur
voyage: Lesser Antilles Journey
booking: "2984034"
departure: 2026-12-19
return: 2026-12-29
cabin: Suite 863, E-Concierge (upgraded)
payment_status: deposit_only
fpd: 2026-07-22
fpd_amount: 11943.15
fpd_amount_verified_date: 2026-06-09
fpd_amount_source: invoice
fpd_verified_date: 2026-06-09
fpd_source: invoice
balance_due: 11943.15
balance_due_verified_date: 2026-06-09
balance_due_source: invoice
harlan_signoff: "Confirmed: balance_due=$11,943.15, FPD Jul-22-2026, source: Regent invoice 2984034 dated 23-May-26. Stale lifecycle-doc figure $12,393.15 superseded ($450 delta was stale)."
status: active
relationship: client
contact_hold_until: 2026-07-07
completed_tps: ["0.5"]
completed_tps_basis: "0.5 booking validation sent + guest registration complete. FPD Jul-22 future → payment TPs NOT done. CONTACT HOLD until Jul 7 (client on Silver Muse Jun 23–Jul 6, Commander directive 2026-06-09)."
draft_pending_tps: ["1.1"]
draft_pending_notes: "TP 1.1 Lesser Antilles Voyage Preview drafted 2026-06-24, staged in johnloucks3 (r4541671196264704806), CONTACT HOLD until Jul 7 — DO NOT SEND before then. Port sequence verified: Miami→St Thomas Dec22→Dominica Dec23→Antigua Dec24→St Kitts Dec25→Tortola Dec26→Miami Dec29."
---

# McLeod / McGlasson — Regent SS Grandeur · Lesser Antilles
## Booking 2984034 · Dec 19–29, 2026 · Suite 863 E-Concierge

> Split from `McLeod_McGlasson_Multi.md` (2026-06-09) so the lifecycle engine
> schedules this trip independently (one record per file).
> ⏸️ **CONTACT HOLD until Jul 7** — client on Silver Muse Jun 23–Jul 6.
> 🟡 **FPD $11,943.15 due Jul 22, 2026.**

Commander Input from Invoice:
Guest Statement
Booking Number: 2984034
Invoice Issue Date: 13-Jul-26
Grand Total
 $12,948.00
Payments
Credit Card Payment (VI 5625) Melissa Mc Glasson
Credit Card Payment (VI 5625) Melisasa Mc Glasson
Total Payments
Date
01-Feb-25
11-Feb-25
Payments
$971.10
$33.75
$1,004.85

**Operational tracker (open items, suspense calendar, per-element status):**
`dossiers/McLeod_Grandeur_LesserAntilles_Dec2026_TRACKER.md`
**Lifecycle (35-TP) doc:** `D2M/lifecycle/McLeod_Grandeur_LesserAntilles_Lifecycle.md`
**Relationship hub (all 4 McLeod trips):** `dossiers/McLeod_McGlasson_Multi.md`

Client: Erik 303-949-0857 · emcleod@gmail.com · Melissa memcglas@gmail.com · Longmont CO.

---

## PRE-CRUISE HOTEL PROGRAM — InterContinental Miami (Commander-confirmed portal 2026-07-19)

**Hotel:** InterContinental Miami — 100 Chopin Plaza, Miami, FL 33131 · 305-577-1000
Downtown Miami financial/business district, Biscayne Bay views.

**Regent Hotel Program status:** 1 night currently **Reserved** (consistent with
tracker's earlier note of a complimentary pre-cruise night, Dec 18 — confirm
that reading, see staged item below). Upgrade options available: 2 nights or
3 nights, at the program's bundled totals.

> ✅ **CONFIRMED 2026-07-20 — Harlan sign-off granted.** Commander confirmed
> he was reading the LIVE Regent portal when he supplied this text on 2026-07-19.
> Per dossier CLAUDE.md source hierarchy (portal > TESS > dossier > memo),
> portal-sourced figures relayed by Commander rank as authoritative (second only
> to direct portal access, which we lack due to stale session cookies).
> - 1 Night (Reserved): **$0.00 — Complimentary**
> - 2 Nights: **$1,776.00** — CONFIRMED
> - 3 Nights: **$2,574.00** — CONFIRMED
> - Source: **portal (Commander relay), 2026-07-19**
> - Harlan sign-off: Confirmed: InterContinental Miami program pricing ($1,776 / 2-night, $2,574 / 3-night, $0/1-night reserved) as of 2026-07-19, source: portal (Commander relay).

---

## EXCURSIONS — ✅ CONFIRMED (A8 Reyes review, 2026-07-19)

> ⚠️ **Stand-in disclosure:** the dedicated `a8-reyes` subagent had a tool-access
> bug this session (two dispatches returned zero working tools, frontmatter fix
> didn't take effect). This section was written by a general-purpose agent
> standing in for Reyes's function/judgment criteria per Hale's routing note,
> **not** a silent bypass of PRODUCTION-LOCK excursion write-authority. Flag
> for Reyes to re-review once the real agent seat is restored.

**Source (primary, supersedes the Commander's 2026-07-19 cart-export paste and
the 2026-07-16 CDP portal read — all three now cross-confirm identically):**
`dossiers/regentsevenseascruisesinvoice2984034guestmcglasson/Pre-Purchased Shore
excursions and Onboard Items_2984034.pdf` — Regent's own "Status on booking as
of 7/13/2026 at 9:52:25AM" export, itemized per guest (Melissa McGlasson + Erik
McLeod, identical selections both guests). Cross-checked against
`validations/rssc_scrape/2984034_McLeod_Dec2026.json` (live portal read,
2026-06-23) and the built client itinerary
`cruises_web/itinerary_grandeur_mcleod.html`, which already carries these exact
names/times.

| Code | Port | Excursion | Date | Time | Duration | Price (both guests) |
|---|---|---|---|---|---|---|
| — | Miami | *None selected* — 2 pre/post-cruise city days, not a touring day | — | — | — | — |
| STT-004 | Charlotte Amalie (St. Thomas) | Shipwreck and Turtle Cove | Dec 22, 2026 | 8:30 AM | 3.0 hrs | $0.00 |
| DOM-007 | Roseau (Dominica) | River Tubing and Trafalgar Falls | Dec 23, 2026 | 11:00 AM | 4.5 hrs | $0.00 |
| SJH-003 | St. John's (Antigua) | **Dickenson Bay Beach Break** | Dec 24, 2026 | 10:30 AM | 4.0 hrs | $0.00 |
| SJH-012 | St. John's (Antigua) | Catamaran Sunset Cruise | Dec 24, 2026 | **4:00 PM** | 2.5 hrs | $0.00 |
| STK-016 | Basseterre (St. Kitts) | Foodie & Beach | Dec 25, 2026 | 10:30 AM | 4.0 hrs | $0.00 |
| TRT-012 | Tortola (Jost Van Dyke) | Escape to Jost Van Dyke | Dec 26, 2026 | 9:30 AM | 5.0 hrs | $0.00 |
| — | Cart total / Amount due | — | — | — | — | **$0.00** |

**Flag resolutions (per routing ticket, confirmed against source — not guessed):**

1. **"Catamaran Sunset Cruise" 04:00 → RESOLVED, was a data-export artifact.**
   The Commander's cart-export paste rendered **4:00 PM as "04:00,"** i.e. the
   PM was dropped/mis-rendered — exactly the artifact the ticket flagged as
   likely. The source PDF (SJH-012) states the time plainly: **"4:00PM."** The
   built client itinerary independently confirms the same reading: *"the
   Catamaran Sunset Cruise sails at 4:00 PM."* **Time is 4:00 PM, confirmed —
   no correction needed to the itinerary, only to the cart-export artifact.**

2. **$0.00 pricing → RESOLVED, Regent-complimentary confirmed by primary source, not assumed.**
   The source PDF carries Regent's own footnote: *"Free Unlimited Shore
   Excursions will reflect a Retail Price of 0.00."* The live portal scrape
   (2026-06-23) independently states under this booking's "Customize Your
   Voyage" section: *"Your trip includes: Unlimited Shore Excursions."* Both
   are Regent-sourced, not memo-level, and both directly explain the $0.00 —
   this is the Concierge Suite E (upgraded) tier's complimentary-excursions
   inclusion, not unpriced/missing data. **CONFIRMED $0.00 = Regent-included,
   not TBD.** (Still — do not carry this line as a generic "free excursions"
   claim into any *other* booking; it's tier-specific to this suite category.)

3. **Naming: "Dickenson Bay Beach Break" confirmed correct**, matches the
   7/13/2026 source PDF (SJH-003) and the already-built client itinerary.
   "Runaway Bay Beach Break" (older `Pre-Selected_Tours` PDF) is superseded —
   do not reintroduce it.

4. **Miami — no excursions selected**, confirmed expected (2 pre/post-cruise
   city days, not a cruise touring day).

**Experience-layer notes for client itinerary / accessibility-dietary pass:**
- **River Tubing and Trafalgar Falls** (Dominica) and **Escape to Jost Van
  Dyke** (Tortola beach day) both carry a moderate physical/mobility bar —
  tubing requires getting in/out of a river tube and some walking on uneven
  terrain; flag if either guest has mobility limitations (none noted in this
  dossier currently).
- **Shipwreck and Turtle Cove** (St. Thomas) is a snorkeling excursion — water
  comfort/swim-ability relevant; no medical/dietary flags on file for either
  guest to cross-reference.
- **Dickenson Bay Beach Break** + **Catamaran Sunset Cruise** are both
  lower-exertion beach/boat excursions — no accessibility concerns expected.
- **Foodie & Beach** (St. Kitts) — dietary considerations relevant; no
  allergy/restriction on file for Erik or Melissa in this dossier (Dietary
  field elsewhere marked `NONE`/pending) — flag to confirm with guests before
  Sep 20 dining-reservation window opens, since a food-tasting excursion is a
  natural moment to also capture dietary prefs for onboard dining.
- Dec 24 is a double-excursion day (beach AM, catamaran PM) — no conflict,
  4 hours between end of one (10:30 AM + 4.0 hrs = ~2:30 PM) and start of next
  (4:00 PM); comfortable turnaround, no logistics flag.
