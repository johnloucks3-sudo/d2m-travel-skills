---
client: McLeod McGlasson
ship: Discovery Princess
voyage: Mexican Riviera (Los Angeles → Los Angeles)
booking: "8X6PGQ"
embark: 2027-03-13
disembark: 2027-03-20
status: active
anchor_type: CRUISE
source_of_truth: "Harlan-verified financials 2026-06-09 (McLeod_McGlasson_Multi.md frontmatter booking_3, Princess confirmation 8X6PGQ dated Mar-21-2025)"
note: "Renders CURRENT state + forward suspense calendar. No dedicated lifecycle doc exists — suspense calendar derived from embark (Mar 13 2027) + FPD (Dec 13 2026) anchors against the standard 6-phase model. Register with scheduler once timing-engine fix lands."
---

# McLEOD — PRINCESS TRIP TRACKER (booking 8X6PGQ of 4)
## Discovery Princess · Mexican Riviera · Los Angeles → Los Angeles · Mar 13–20, 2027
### Wired 2026-06-09 (T-277) · Scandinavia-pattern tracker · ⭐ BEST CLIENT

> No dedicated lifecycle doc exists for this booking — clock anchors are embark Mar 13, 2027 and FPD Dec 13, 2026.
> **No live deadline within 30 days.** First real action: FPD payment sequence early Dec 2026.
> Handoff: instantiate a full lifecycle doc + register with scheduler once timing-engine fix lands.

---

## CLIENTS

| Field | Value |
|---|---|
| **Travelers** | Erik Wiedenbach McLeod + Melissa Etola McGlasson |
| **Cabin** | D727 — S3, Queen, Aft |
| **Air route** | LAX (embark/disembark same port) — air TBD |

---

## 💰 FINANCIAL (Harlan-verified 2026-06-09)

| Field | Value | Source |
|---|---|---|
| **FPD amount (balance)** | **$6,062.00** | hub dossier frontmatter booking_3 (Harlan-verified) — **AUTHORITATIVE per spec** |
| **FPD** | **Dec 13, 2026** | invoice |
| **Deposit paid** | $200 (FCC) | Princess confirmation 8X6PGQ dated Mar-21-2025 |
| **Payment status** | deposit_only | frontmatter |

> ⚠️ **CONFLICT — Harlan to arbitrate (internal dossier self-contradiction):** The hub dossier contradicts itself on this booking:
> - **`booking_3_fpd_amount: 6062.00`** (frontmatter field) — matches spec ("~$6,062"). **Used here as primary.**
> - **Harlan sign-off prose:** *"$200 deposit paid (FCC), gross balance $6,222 due Dec-13-2026"* — states **$6,222 gross**.
> - The $6,222 and $6,062 do not net cleanly via the $200 FCC ($6,222 − $200 = $6,022, not $6,062; $6,222 − $160 = $6,062). **Root cause unresolved.**
> Neither field was modified. $6,062 used per spec + frontmatter field; $6,222 flagged for Harlan reconciliation before any payment reminder or client email carries a dollar figure.
>
> **Note:** the spec also records a separate prior contamination on a different McLeod booking ("a prior $6,462 balance in the sheet was a Princess-total contamination" — that note refers to the **Prestige** booking 3114500, corrected to $14,598; do not conflate with this Princess figure).

---

## PER-ELEMENT STATUS

| Element | Status | Notes |
|---|---|---|
| **Cruise booking** | ✅ CONFIRMED | Cabin D727, S3 Queen Aft |
| **Payment** | 🟡 DEPOSIT ONLY | $6,062 due Dec 13, 2026 — see CONFLICT ($6,222 unreconciled) |
| **Air** | ⏳ NOT STARTED | LAX round-trip — future window |
| **Hotel (pre/post)** | ⏳ NOT STARTED | LA pre/post if needed |
| **Transfers** | ⏳ NOT STARTED | LAX↔port (San Pedro) |
| **Excursions** | ⏳ NOT STARTED | Mexican Riviera ports (Cabo, Puerto Vallarta, Mazatlán typical) — verify itinerary |
| **Dining** | ⏳ NOT STARTED | Princess specialty dining; seafood priority |
| **Documents** | ⏳ NOT STARTED | Passport validity; closed-loop sailing (LAX→LAX) may allow birth-cert + ID — verify |
| **Insurance** | ⏳ OPEN | Own element — not yet addressed for this booking |

---

## 🔴 OPEN ITEMS

| # | Item | Owner | Deadline |
|---|---|---|---|
| 1 | **Resolve $6,062 vs $6,222 figure** (FCC netting unclear) | Harlan | before any payment reminder |
| 2 | **FPD $6,062** — payment sequence | Harlan / Hale | **Dec 13, 2026** |
| 3 | **Verify Princess itinerary** (exact ports/dates) — currently "TBD" in hub | A2 Dembe | discovery window |
| 4 | **Instantiate full lifecycle doc** for this booking | Hale | when scheduler fix lands |

---

## 📅 SUSPENSE CALENDAR (T-277 → departure)
*No lifecycle doc — derived from FPD (Dec 13, 2026) + embark (Mar 13, 2027) against the standard 6-phase model. Dates are planning estimates, NOT portal-confirmed; refine when the lifecycle doc is instantiated.*

| Date (est.) | Event | Type |
|---|---|---|
| **Aug–Oct 2026** | Discovery: air watch, excursion research, itinerary verify | internal |
| **Nov 22, 2026** | Payment Reminder #1 (FPD-21) | client send |
| **Nov 29, 2026** | Payment Reminder #2 (FPD-14) | client send |
| **Dec 6, 2026** | Payment Goal (FPD-7) | client send |
| **Dec 13, 2026** | 🔴 **FINAL PAYMENT DUE — $6,062** (pending $6,222 reconcile) | 🔴 FPD |
| **Dec 20, 2026** | Payment Confirmation (FPD+7) | client send |
| **~Dec 13, 2026** | Princess dining/excursion booking typically opens (~90d) — verify | cutoff |
| **Feb 13, 2027** | AR-3.0 Embarkation gift — ORDER by E-30 (est.) | action |
| **Feb 20, 2027** | TP 3.1 Pre-Voyage Brief (E-21 est.) | client send |
| **Mar 6, 2027** | TP 3.2 Final Confirmation (E-7 est.) | client send |
| **Mar 10, 2027** | TP 3.3 Send-Off (E-3 est.) | client send |
| **Mar 13, 2027** | 🚢 Embark Los Angeles | travel |
| **Mar 20, 2027** | Disembark Los Angeles | travel |
| **Mar 27 → Apr 19, 2027** | Post-voyage (5.1–5.4) | client send |

---

*Wired 2026-06-09 by Sonnet. Financials = Harlan-verified frontmatter ($6,062; $6,222 flagged). No lifecycle doc — suspense dates derived from anchors, marked estimate. Register with scheduler once timing-engine fix lands.*

<!-- EXCURSIONS_STAGED_TRUE | Staged autonomously by Hale Staging Engine -->

<!-- PHASE4_LIFECYCLE_STAGED_V1 | Autonomously enriched by Phase 4 AI Engine -->
