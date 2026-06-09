---
group: Kuklinski — 3 Couples (incl. Morton/Dodge)
ship: Viking Mars
voyage: Panama Canal & Central America (Panama City → Fort Lauderdale)
embark: 2026-12-17
disembark: 2026-12-27
status: active
anchor_type: CRUISE
source_of_truth: "Harlan-verified financials 2026-06-09 (Kuklinski_Viking_Panama.md frontmatter, Viking invoices Feb 2026) + D2M/lifecycle/Kuklinski_Viking_Panama_Lifecycle.md (35-TP clock) + Morton_Dodge_Viking_Panama_Lifecycle.md"
note: "Renders CURRENT state + forward suspense calendar. The instantiated 35-TP clock lives in D2M/lifecycle/Kuklinski_Viking_Panama_Lifecycle.md — this tracker does not reproduce it. Treat as one 3-couple group; Morton/Dodge run a SEPARATE (reset) TP cadence — see note in suspense calendar."
---

# KUKLINSKI GROUP — TRIP TRACKER (3 Couples)
## Viking Mars · Panama Canal & Central America · Panama City → Fort Lauderdale · Dec 17–27, 2026
### Wired 2026-06-09 (T-191) · Scandinavia-pattern tracker

> Anchor locked (cruise paid in full). Clock is the existing 35-TP lifecycle doc.
> **Soonest live deadline across all 5 trips: excursion recs ~Jul 15** (Kuklinski lifecycle TP 2.1 send Aug 1 / Viking window opens Aug 2; the Commander HOLD on the 4 Kuklinski drafts also lifts Jul 15).
> Handoff: **register this tracker with the lifecycle scheduler once the timing-engine fix lands** (per docs/TRIP_ASSEMBLY_MODEL_SPEC.md §8). Until then it is a data artifact only.

---

## COUPLES

| Couple | Booking | Agency Conf | Stateroom | Fare | Balance | SBC | Air route |
|---|---|---|---|---|---|---|---|
| **Kyle & Rosalie Kuklinski** | 9593880 | 1TSWFQR | 4122 (DV1, Deck 4) | OMAFSV26-3 | ✅ PAID | $800 ($200 Viking + $600 D2M) | RIC → PTY |
| **Roger & Dr Nicholas Kuklinski** | 9593873 | LJ2O4YG | 8012 (DV1, Deck 8) | OMAFSV26-3 | ✅ PAID | $200 Viking | RIC → PTY |
| **Joshua Morton & Erica Dodge** | 9595029 | CUW88R8 | 3015 (V1 Veranda, Deck 3) | OMAPSF26-3 | ✅ PAID | $200 Viking | RSW → FLL |

**Financials (Harlan-verified 2026-06-09):** Total **$21,244 PAID IN FULL** (3 bookings, Mar 27). FPD was Mar 31 — passed, paid 4 days early. Payment method: Kyle Kuklinski CC on file for all 3 bookings (CVC 7435). Commission $3,635.14. Source: Viking invoices Feb 2026.

> ⚠️ **CONFLICT — Commander to arbitrate (Morton/Dodge FPD status):** The Morton/Dodge lifecycle doc (Jun 9) flags FPD as **CONFLICTED** — dossier says PAID Mar 27 in the $21,244 group total, but an Apr 28 financial snapshot showed $6,148 OVERDUE for booking 9595029. Harlan group sign-off says all 3 paid. **Left untouched in both files.** Resolution: Harlan TESS verification (was Kyle's Mar 27 charge for 3 bookings or 2?). Do not raise with client until resolved.

---

## PER-ELEMENT STATUS (group)

| Element | Status | Notes |
|---|---|---|
| **Cruise booking** | ✅ CONFIRMED (all 3) | Staterooms 4122 / 8012 / 3015 |
| **Payment** | ✅ PAID IN FULL ($21,244) | Morton/Dodge FPD flag — see CONFLICT above |
| **Air** | 🔴 NOT BOOKED | RIC→PTY (Kuklinskis ×4) + RSW→FLL (Morton/Dodge). Fare watch active. |
| **Hotel (pre/post)** | 🔴 NOT BOOKED | Panama City pre + FLL post. Morton/Dodge: optional (FL residents, near FLL) |
| **Transfers** | 🔴 NOT BOOKED | PTY airport→pier; FLL pier→airport |
| **Excursions** | ⏳ PENDING | Viking window opens **Aug 2** (Kuklinski) / **Sep 23** (Morton/Dodge, reset cadence). Recs due day prior. |
| **Dining (specialty)** | ⏳ PENDING | ARC4-A preferences ask sent May 15 (Kyle). Reservations open ~Sep 18. |
| **Documents** | 🟡 PARTIAL | Passports (6) NOT VERIFIED. Guest forms: 5/6 — **Josh Morton MISSING**. |
| **Insurance** | ⏸ DEFERRED | Client declined Apr 19 (pre-ex window closed Feb 23). Revisit mid-Jul (TP 0.6 send Jul 28). |
| **Portal activation** | 🟡 QUEUED | Kyle green-lit; was CDP-blocked Mar 20. |

---

## 🔴 OPEN ITEMS (wired-tight — nothing silent)

| # | Item | Owner | Deadline |
|---|---|---|---|
| 1 | ⛔ **Kuklinski 4-draft HOLD lifts Jul 15** (Welcome TP0.5, Specialty Dining TP4.1, Excursion TP4.2, Pre-Dep Checklist TP4.3) — do NOT surface at WF-17 before Jul 15 (Commander order 2026-06-04) | Hale | **Jul 15** |
| 2 | **Excursion recs ready before Viking window** (Kuklinski) | A2 Dembe | **Aug 1** (window opens Aug 2) |
| 3 | **Resolve Morton/Dodge FPD conflict** (TESS verify) | Harlan | before next Morton/Dodge client touch |
| 4 | **Josh Morton guest form** — still missing; follow up via Kyle | Dani | Document audit (Sep 18 / Oct 8) |
| 5 | **Air booking** — RIC→PTY ×4 + RSW→FLL; Dec holiday fare pressure | A2 Dembe | Air decision ~Jul 17 |
| 6 | **Passport verification** — all 6 guests, valid through Mar 2027 | Hale | Document audit window |
| 7 | **Insurance revisit** — mid-July re-offer (declined Apr 19) | Dani | Jul 28 send |

---

## 📅 SUSPENSE CALENDAR (T-191 → departure)
*Dates pulled from D2M/lifecycle/Kuklinski_Viking_Panama_Lifecycle.md (Kuklinski couples) and Morton_Dodge_Viking_Panama_Lifecycle.md (Morton/Dodge reset cadence). Morton/Dodge run LATER windows — kept distinct below.*

| Date | Event | Couple(s) | Type |
|---|---|---|---|
| **Jun 15** | Monthly validation (internal) | All | internal |
| **Jun 17** | TP 1.2 Airfare Watch + TP 1.3 Hotel Options send | Kuklinski ×4 | client send |
| **Jul 15** | ⛔ **HOLD LIFTS** on 4 Kuklinski drafts + monthly validation | Kuklinski ×4 | gate / internal |
| **Jul 28** | TP 0.6 Insurance (deferred) re-offer | Kuklinski ×4 | client send |
| **Aug 1** | TP 2.1 Excursion Recs send (before window) | Kuklinski ×4 | client send |
| **Aug 2** | 🚨 Viking excursion booking window opens | Kuklinski ×4 | cutoff |
| **Aug 22** | TP 1.2 Airfare + TP 1.3 Hotel (optional) send | Morton/Dodge | client send |
| **Sep 18** | TP 2.3 Dining + TP 2.4 Document Audit send | Kuklinski ×4 | client send |
| **Sep 22** | TP 2.1 Excursion Recs send (before window) | Morton/Dodge | client send |
| **Sep 23** | 🚨 Viking excursion window opens | Morton/Dodge | cutoff |
| **Oct 8** | TP 2.3 Dining + TP 2.4 Doc Audit + Guest Forms send | Morton/Dodge | client send |
| **Nov 17** | AR-3.0 Embarkation gift — ORDER by E-30 | All | action |
| **Nov 26 / Nov 27** | TP 3.1 Pre-Voyage Brief send | Kuklinski / Morton-Dodge | client send |
| **Dec 10 / Dec 11** | TP 3.2 Final Confirmation send | Kuklinski / Morton-Dodge | client send |
| **Dec 14** | TP 3.3 Send-Off | All | client send |
| **Dec 17** | 🚢 Embark Panama City (3:00 PM) | All | travel |
| **Dec 27** | Disembark Fort Lauderdale (5:00 AM) | All | travel |
| **Dec 28 → Jan 27** | Post-voyage sequence (5.1–5.4) | All | client send |

---

*Wired 2026-06-09 by Sonnet. Financials = Harlan-verified frontmatter (do not recompute). Clock = existing lifecycle docs. Register with scheduler once timing-engine fix lands.*
