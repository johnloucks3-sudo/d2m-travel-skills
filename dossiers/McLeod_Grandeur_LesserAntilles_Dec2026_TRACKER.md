---
client: McLeod McGlasson
ship: SS Grandeur (Regent Seven Seas)
voyage: Lesser Antilles Journey (Miami → Miami)
booking: '2984034'
embark: 2026-12-19
disembark: 2026-12-29
status: active
anchor_type: CRUISE
source_of_truth: Harlan-verified financials 2026-06-09 (McLeod_McGlasson_Multi.md
  frontmatter, Regent invoice 2984034 dated 23-May-26) + D2M/lifecycle/McLeod_Grandeur_LesserAntilles_Lifecycle.md
  (clock)
note: Renders CURRENT state + forward suspense calendar. 35-TP clock lives in the
  lifecycle doc — not reproduced here. ⛔ CONTACT HOLD until Jul 7 (client on Silver
  Muse Jun 23–Jul 6).
payment_status: confirmed
departure: '2026-12-19'
return: '2026-12-29'
---

# McLEOD — GRANDEUR TRIP TRACKER (booking 2984034 of 4)
## Regent SS Grandeur · Lesser Antilles Journey · Miami → Miami · Dec 19–29, 2026
### Wired 2026-06-09 (T-193) · Scandinavia-pattern tracker · ⭐ BEST CLIENT — GOLD STANDARD

> ⛔ **CONTACT HOLD UNTIL JUL 7.** Erik & Melissa are aboard Silver Muse Jun 23–Jul 6 (their current trip).
> **No client-facing item on this booking may go out before Jul 7, 2026** (Commander directive 2026-06-09).
> Hold-lift Jul 7 → FPD Jul 22 ($11,943.15). 15-day payment window after hold lifts.
> Handoff: register with scheduler once timing-engine fix lands. Competitive risk ELEVATED (Pavlus visibility) — no missed dates.

---

## CLIENTS

| Field | Value |
|---|---|
| **Travelers** | Erik Wiedenbach McLeod + Melissa Etola McGlasson |
| **Suite** | 863, Deck 8 — Concierge Suite E (447 sq ft, UPGRADED) |
| **Home** | 1414 Armstrong, Longmont, CO |
| **Emails** | emcleod@gmail.com · memcglas@gmail.com (CC Melissa on all) |
| **Air route** | DEN ↔ MIA (per lifecycle) |

---

## 💰 FINANCIAL (Harlan-verified 2026-06-09)

| Field | Value | Source |
|---|---|---|
| **Balance due (FPD)** | **$11,943.15** | Regent invoice 2984034 dated 23-May-26 (Harlan sign-off) |
| **FPD** | **Jul 22, 2026** | invoice (portal-confirmed) |
| **Payment status** | deposit_only | hub dossier frontmatter |
| **Regent FCC** | $200 ($100/pp) — Gale Hotel Miami complaint Dec 2025 | **NOT in TESS** (verified 2026-07-16 — see below) |

> ⚠️ **CONFLICT — Commander/Harlan to arbitrate (balance figure):** Two balance figures exist in the record:
> - **$11,943.15** — hub dossier frontmatter, Harlan-verified 2026-06-09, Regent invoice 23-May-26. **AUTHORITATIVE per spec + freshest source. Used in this tracker.**
> - **$12,393.15** — D2M/lifecycle/McLeod_Grandeur_LesserAntilles_Lifecycle.md (created 2026-04-17; total $13,398 / paid $1,004.85). **Stale.**
> The hub dossier prose (~line 339) already logs the **$450 delta** ("portal verified 2026-05-28; root cause pending TESS confirmation"). This is a **known, logged delta**, not a fresh discrepancy. Neither file was modified. Lifecycle-doc payment-reminder amounts ($12,393.15) should be refreshed to $11,943.15 when the lifecycle doc is next revised (route to Harlan — not done here).

**Insurance note (contamination guard):** The Seven Corners $30K/$1,300 policy in the hub dossier is the **Silver Muse** trip's insurance — NOT this Grandeur trip. Grandeur insurance = its own element: pre-existing window closed Jan 16, 2026; standard coverage still available. Do not carry Silver Muse policy into this tracker. (Also: Medallion suite-bid = Silversea context per Commander 2026-05-28 — keep out of Regent comms.)

---

## PER-ELEMENT STATUS

| Element | Status | Notes |
|---|---|---|
| **Cruise booking** | ✅ CONFIRMED | Suite 863, E-Concierge (upgraded) |
| **Payment** | 🟡 DEPOSIT ONLY | $11,943.15 due Jul 22 — see HOLD + CONFLICT |
| **Air** | ✅ **CENTRAV PRICED 2026-06-30** | DEN→MIA Dec 18 biz **$1,807** ($904 pp) | MIA→DEN Dec 29 biz **$1,819** ($910 pp) | **RT biz $3,626** ($1,813 pp) |
| **Hotel (pre/post)** | 🟡 STRUCTURAL CONFIRMED, PRICING UNVERIFIED | InterContinental Miami, 1 night Reserved (Dec 18); 2/3-night upgrade pricing — Harlan DECLINED sign-off 2026-07-19 (TESS empty, no portal access) |
| **Transfers** | ⏳ PENDING | Airport↔port Miami |
| **Excursions** | ✅ CONFIRMED | 6 excursions, 5 ports (Miami none — city days), confirmed against source PDF `Pre-Purchased Shore excursions and Onboard Items_2984034.pdf` (7/13/2026) + 2026-06-23 portal scrape + built itinerary — cross-agree. 04:00 cart-export artifact resolved (Catamaran Sunset Cruise = 4:00 PM confirmed). $0.00 = Regent-complimentary confirmed (Concierge Suite E tier). Full table + notes: `McLeod_Grandeur_LesserAntilles_2984034.md` § EXCURSIONS. Written by general-purpose stand-in for A8 Reyes (agent-access bug this session) — flag for Reyes re-review once seat restored. |
| **Dining** | ⏳ PENDING | Culinary Arts classes ~Aug 21; reservations open ~Sep 20. Seafood priority. |
| **Documents** | ⏳ PENDING | Guest reg COMPLETE (both). Passport validity check pending. Guest info forms E-150 (~Jul 22). |
| **Insurance** | ⏳ OPEN | Pre-ex window closed Jan 16; standard coverage available. Own element (see guard above). |
| **FCC** | 🔴 NOT APPLIED | $200 Regent FCC — TESS-verified 2026-07-16 NOT recorded against 2984034 (see EMAIL LOG / OPEN ACTION ITEMS below) |

---

## 🔴 OPEN ITEMS

| # | Item | Owner | Deadline |
|---|---|---|---|
| 1 | ⛔ **CONTACT HOLD — no client item before Jul 7** (client on Silver Muse) | Hale | hold lifts **Jul 7** |
| 2 | **FPD $11,943.15** — payment sequence after hold lifts | Harlan / Hale | **Jul 22** |
| 3 | **Resolve $450 balance delta** ($11,943.15 vs $12,393.15) — known/logged; close root cause | Harlan | before payment reminders |
| 4 | ~~Verify~~ **Apply $200 Regent FCC** to booking 2984034 — verification done 2026-07-16, NOT applied, needs Harlan action with Regent/Pavlus | Harlan | before FPD (Jul 22) |
| 5 | **Refresh lifecycle-doc payment amounts** to $11,943.15 (route, do not edit here) | Harlan / Sterling | next lifecycle revision |
| 6 | ~~**Excursion research** — 5 ports, Regent portal~~ **CLOSED 2026-07-19** — confirmed against source PDF (7/13/2026), portal scrape (6/23/2026), and built itinerary; all three agree. See dossier § EXCURSIONS. | A8 Reyes (stand-in) | ✅ done 2026-07-19 |

> **STAGED FOR SIGN-OFF (2026-07-16, live Regent agent-portal read via CDP, booking 2984034 detail page) — Hale routing, NOT committing per dossier PRODUCTION-LOCK write-authority rules (financial = Harlan, excursions = Reyes):**
> - **Balance due: $11,743.15** (Total Booking Amount $12,748.00, Paid to Date $1,004.85), FPD still Jul 22, 2026 — a THIRD figure distinct from both $11,943.15 (this tracker) and $12,393.15/$13,398 (lifecycle doc). Portal is the highest-authority source per dossier CLAUDE.md's freshness hierarchy (portal > TESS > dossier > memo) — **route to Harlan for sign-off before using in any client-facing figure.**
> - **FCC status correction:** live portal shows "FUTURE CRUISE CREDITS: TOTAL $200, REMAINING $0" — reads as **already applied against this booking**, contradicting the 2026-07-16 TESS-based finding above ("NOT recorded/applied"). TESS and Regent's own system disagree; Regent is the supplier of record. **Route to Harlan to confirm interpretation and reconcile with TESS before touching the McLeod FCC-confirmation draft.**
> - ✅ **Excursions CLOSED 2026-07-19 (A8 Reyes stand-in — real agent seat had a tool-access bug this session, flag for re-review once fixed):** matches the portal's own "Shore Excursions Booked" checklist item (May 23 2026), the Commander's 2026-07-19 cart-export paste, AND the source document `Pre-Purchased Shore excursions and Onboard Items_2984034.pdf` (status as of 7/13/2026) — all three agree. Charlotte Amalie — Shipwreck and Turtle Cove (Dec 22, 8:30AM); Roseau — River Tubing and Trafalgar Falls (Dec 23, 11:00AM); St. John's — Dickenson Bay Beach Break (Dec 24, 10:30AM) + Catamaran Sunset Cruise (Dec 24, **4:00PM confirmed** — the Commander's paste rendered this as "04:00," a cart-export artifact, resolved against source PDF and the built itinerary, which both read 4:00 PM); Basseterre — Foodie & Beach (Dec 25, 10:30AM); Tortola — Escape to Jost Van Dyke (Dec 26, 9:30AM). All six priced $0.00, **confirmed Regent-complimentary** (source PDF footnote: "Free Unlimited Shore Excursions will reflect a Retail Price of 0.00," matching this suite's Concierge Suite E tier) — not treated as unpriced/TBD. Accessibility/dietary notes (tubing/mobility bar, snorkeling, Foodie & Beach dietary tie-in ahead of Sep 20 dining window) logged in the dossier § EXCURSIONS. Full table + source citations: `McLeod_Grandeur_LesserAntilles_2984034.md`. Plus a free pre-cruise night at the InterContinental Miami (Dec 18, tracked separately above under Hotel).
> - **Naming discrepancy RESOLVED:** `Pre-Selected_Tours_MC GLASSON2984034.pdf` calls the Dec 24 St. John's beach stop "Runaway Bay Beach Break"; the newer, dated `Pre-Purchased Shore excursions and Onboard Items_2984034.pdf` (status as of 7/13/2026 — the confirmed/purchased document, both guests, SJH-003) calls it "Dickenson Bay Beach Break." The 7/13 confirmed document is authoritative — **Dickenson Bay Beach Break** is correct, already used in the built itinerary.

> - **Pre-cruise hotel program (Commander-supplied, 2026-07-19):** InterContinental
>   Miami, 100 Chopin Plaza, 305-577-1000. 1 night currently Reserved (Dec 18).
>   Upgrade pricing shown: 2 nights $1,776.00, 3 nights $2,574.00. **Harlan
>   checked TESS 2026-07-19 — declined sign-off:** `Itemizations` empty, no
>   line-item hotel data, no direct portal access. Regent portal is
>   next-authority source; Hale's session cookies stale since Jul 14 (keepalive
>   failing since Jul 8, proxy errors). **UNVERIFIED — do not use in any
>   client-facing product.** Next step: confirm Commander was reading live
>   portal when he supplied this text (Harlan could then accept as
>   `portal (Commander relay)`), or fresh Regent login needed (Commander's
>   login/CAPTCHA step). Full detail in `McLeod_Grandeur_LesserAntilles_2984034.md`.

**Client-facing itinerary BUILT** (2026-07-16): `cruises_web/itinerary_grandeur_mcleod.html` — 5 ports, original romance copy, 6 viewed+verified images, confidential-data-clean (no home address/insurance/competitor/dollar figures), guest surnames kept distinct (McLeod/McGlasson) per the "AI-tell to avoid" given this couple's documented AI-skepticism. **WF-17 HELD — not sent.**
| 7 | ⚠️ **STRUCTURAL — Commander/scheduler-owner to decide.** The TP scheduler (`core/booking/thunderbird_tp_scheduler.py`) reads ONE record per dossier file via TOP-LEVEL `departure`/`fpd`/`completed_tps`. `McLeod_McGlasson_Multi.md` is a 4-booking hub with only `booking_N_*` keys → engine sees no top-level dates → all 23 TPs resolve **BLOCKED** (not OVERDUE), so McLeod currently fires zero false-overdues but is also **unscheduled**. The `booking_N_completed_tps` keys I added are INERT (engine doesn't read them). Flattening to one top-level `completed_tps` is unsafe (would false-complete the 3 deposit-only bookings). **Fix requires either split per-booking dossiers OR an engine change to handle multi-booking hubs** — out of my data-artifact scope. | Commander / scheduler owner | structural |

---

## 📅 SUSPENSE CALENDAR (T-193 → departure)
*Dates from D2M/lifecycle/McLeod_Grandeur_LesserAntilles_Lifecycle.md. ⛔ Nothing client-facing before Jul 7.*

| Date | Event | Type |
|---|---|---|
| **Jun 23 – Jul 6** | ⛔ Client aboard Silver Muse — NO CONTACT this booking | hold |
| **Jul 7** | ⛔ **CONTACT HOLD LIFTS** — Grandeur comms may resume | gate |
| **Jul 8–9** | Payment Reminder #1 (FPD-14 equiv, post-hold) | client send |
| **Jul 15** | Payment Goal (FPD-7) + Monthly Validation Jul | client send / internal |
| **Jul 22** | 🔴 **FINAL PAYMENT DUE — $11,943.15** + E-150 guest info forms | 🔴 FPD |
| **Jul 29** | Payment Confirmation (FPD+7) | client send |
| **Aug 15** | Monthly Validation Aug | internal |
| **Aug 21** | Culinary Arts classes open (Regent) | cutoff |
| **Sep 15** | Monthly Validation Sep | internal |
| **Sep 20** | Dining reservations open (Regent) — TP 2.3 send | client send |
| **Oct 15 / Nov 15** | Monthly Validation Oct / Nov | internal |
| **Nov 19** | AR-3.0 Embarkation gift — ORDER by E-30 | action |
| **Nov 28** | TP 3.1 Pre-Voyage Brief + Online check-in opens | client send |
| **Dec 12** | TP 3.2 Final Confirmation (E-7) | client send |
| **Dec 16** | TP 3.3 Send-Off (E-3) | client send |
| **Dec 19** | 🚢 Embark Miami | travel |
| **Dec 29** | Disembark Miami | travel |
| **Jan 5 → Jan 28, 2027** | Post-voyage (5.1–5.4) + commission audit | client send |

---

*Wired 2026-06-09 by Sonnet. Financials = Harlan-verified frontmatter ($11,943.15; do not recompute). Jul-7 hold encoded. Clock = existing lifecycle doc. Register with scheduler once timing-engine fix lands.*


### EMAIL LOG

**Jul 13 — Erik McLeod** (Re: Fwd: Regent Hotel - 2853147)
> Jul 13 06:42 MT: Erik proactively forwarded Gale Hotel complaint resolution (Jan 16, 2026 close) with $200 Regent FCC ($100/pp) documentation. Requested confirmation of application to Grandeur booking 2984034. High-intent client managing account proactively. Routed to Harlan for TESS verification and application confirmation. ETA: pre-FPD (Jul 22).


### OPEN ACTION ITEMS
- [x] **TESS VERIFICATION COMPLETE (2026-07-16):** Checked booking 2984034 (TESS internal BookingID 2256103) via `tess_get_booking` + `tess_get_trip`. `PaymentsAndItemizations.Itemizations` = `[]` (empty), `ReceiptCount`=0, `PaymentCount`=0, `ActualPackagePrice` == `PackagePrice` ($13,398.00 — no discount/credit applied anywhere on the booking). **Finding: the $200 Regent FCC is NOT recorded or applied against this booking in TESS.** The FCC exists on the Regent/Pavlus side per Erik's Jul 13 forwarded documentation, but no one has entered it into TESS or confirmed it's linked to 2984034. Side note for Block 2/Harlan: TESS `PackagePrice` ($13,398.00) also doesn't match the Jul 13 invoice Grand Total ($12,948.00) referenced above — a $450 gap consistent with the already-logged balance-delta pattern, flagged here for Harlan's commission-recon pass, not resolved by this check.
- [ ] **NEXT STEP (still open, FPD Jul 22 — 6 days out):** Harlan (or whoever holds the Pavlus/Regent contact) needs to either (a) book the $200 FCC into TESS against 2984034, or (b) get written Regent/Pavlus confirmation that it's linked to this booking, before the staged FCC confirmation draft can truthfully tell Erik it's applied. TESS re-checking will not resolve this — it needs the credit actually entered or confirmed externally.
- [x] Contact hold verified cleared: hold was tied to client travel (aboard Silver Muse Jun 23–Jul 6), lifted Jul 7 as scheduled — confirmed cleanly cleared, not an open-ended unresolved hold (verified 2026-07-15/16).
- [x] Response draft confirmed READY, staged in johnloucks3 (draft r6302915235413543112, 2026-07-13): confirms $200 FCC awareness, promises verification "no later than mid-July" and application before Dec 19 embarkation. Content verified solid and client-voice-appropriate — gated only on Harlan's TESS check above before send (WF-17, Commander-send gate).
- [ ] Response team: Send confirmation email to emcleod@gmail.com (CC memcglas@gmail.com) with FCC application confirmation once Harlan verifies (auto-intel Jul 13)
- [x] Separate post-cruise feedback survey (Silver Muse Mediterranean/Venice, unrelated to this Dec Grandeur booking) also drafted and ready in johnloucks3 (r7751380314964613848, 2026-07-13) — lower urgency, no FPD tie.
