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
| **Hotel (pre/post)** | ⏳ PENDING | Miami pre Dec 18 / post Dec 29 if needed (TP 1.3) |
| **Transfers** | ⏳ PENDING | Airport↔port Miami |
| **Excursions** | ⏳ PENDING | Regent portal; 5 ports (Charlotte Amalie, Roseau, St. John's, Basseterre, Tortola) |
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
| 6 | **Excursion research** — 5 ports, Regent portal | A2 Dembe | per lifecycle window |

> **STAGED FOR SIGN-OFF (2026-07-16, live Regent agent-portal read via CDP, booking 2984034 detail page) — Hale routing, NOT committing per dossier PRODUCTION-LOCK write-authority rules (financial = Harlan, excursions = Reyes):**
> - **Balance due: $11,743.15** (Total Booking Amount $12,748.00, Paid to Date $1,004.85), FPD still Jul 22, 2026 — a THIRD figure distinct from both $11,943.15 (this tracker) and $12,393.15/$13,398 (lifecycle doc). Portal is the highest-authority source per dossier CLAUDE.md's freshness hierarchy (portal > TESS > dossier > memo) — **route to Harlan for sign-off before using in any client-facing figure.**
> - **FCC status correction:** live portal shows "FUTURE CRUISE CREDITS: TOTAL $200, REMAINING $0" — reads as **already applied against this booking**, contradicting the 2026-07-16 TESS-based finding above ("NOT recorded/applied"). TESS and Regent's own system disagree; Regent is the supplier of record. **Route to Harlan to confirm interpretation and reconcile with TESS before touching the McLeod FCC-confirmation draft.**
> - **Excursions CONFIRMED booked** (matches the portal's own "Shore Excursions Booked" checklist item, May 23 2026): Charlotte Amalie — Shipwreck and Turtle Cove; Roseau — River Tubing and Trafalgar Falls; St. John's — Dickenson Bay Beach Break + Catamaran Sunset Cruise; Basseterre — Foodie & Beach; Tortola — Escape to Jost Van Dyke. Plus a free pre-cruise night at the InterContinental Miami (Dec 18). **Route to Reyes** to confirm these are the final selections and note anything client-facing needed (e.g. beach/water-activity level, dietary tie-ins for Foodie & Beach).
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
