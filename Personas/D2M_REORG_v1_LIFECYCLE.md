# D2M Re-org v1 — Lifecycle-Focused Hat Rack
## Dreams2Memories Travel, LLC · 2026-05-17
### From 16 USAF-scale personas to 4 delivery hats + Commander

---

## WHY THIS EXISTS

The T4 re-role created 16 rich USAF-equivalent personas at 300,000+ airman scale. They are excellent character sketches. They are not **usable** by a 1-person travel agency.

This document maps every persona against actual client lifecycle touchpoints — using the Kuklinski Group (Viking Mars, Dec 17–27, 2026) as the concrete test case. Personas with zero lifecycle touchpoints, zero dates, zero deliverables are eliminated. The survivors become **hats you wear**, not separate staff.

---

## METHODOLOGY

Each persona was tested against:
1. **22-touchpoint Kuklinski email library** (`D2M/email_templates/Kuklinski_Lifecycle_Email_Library.md`)
2. **16 touchpoints in master lifecycle table** (`D2M/lifecycle/Kuklinski_Viking_Panama_Lifecycle.md`)
3. **All sent draft emails** (`drafts/kuklinski_*.html`, `comms/kuklinski_email_drafts.md`)
4. **Staff workflow pipeline** (lifecycle doc sec 6)
5. **Staff load summary** (lifecycle doc sec 7)
6. **Weekly report cadence** (lifecycle doc sec 8)
7. **Routing & delivery rules** (lifecycle doc sec 10)

**Threshold:** A persona must have at least one concrete touchpoint, date range, and deliverable in an active client lifecycle. If it has zero — eliminate.

---

## CORE DELIVERY TEAM (4 hats + Commander)

### COMMANDER (Yoda) — Every TP ends here

The only person who can say "send." Every client email, every report, every deliverable reaches your desk for the final decision.

**Lifecycle function:** WF-17 send gate. You review drafts placed in d2mconcierge Gmail + copied to johnloucks3 at 0600. You approve, edit, or hold.

**Documents referencing this:** ALL lifecycle docs, ALL email templates, ALL routing rules. The workflow pipeline ends at CDR → "✅ APPROVED" → DANI sends.

---

### HAT 1: DANI (A3) — Client Voice

| Role | Lifecycle Function | Touchpoints | Total Volume |
|------|-------------------|-------------|--------------|
| Client-facing voice | Every client email format and delivery | ALL 16 master TPs | 16 emails per lifecycle |
| Quality standard | Sets/enforces D2M service standard | ALL client deliverables | Continuous |
| Guest outreach | Follow-ups (Josh Morton form) | TP-1 follow-up | 1–3 per lifecycle |
| Monthly validation | Booking status + milestones | TP 2.2 (15th each month) | 8 sends Apr–Nov |
| Send-Off (T-3) | Final bon voyage email | TP 3.3 | Dec 14 |
| Welcome Home | Post-voyage day 1 | TP 5.1 | Dec 28 |
| Thank You | Handwritten-style thank you + referral | TP 5.3 | Jan 10 |

**D2M value:** She IS the product. Without Dani, there is no D2M voice. She does not research, draft, or cost — she formats and delivers.

**Proven in Kuklinski:** `drafts/kuklinski_welcome_validation_email.html` (sent Apr 17), `drafts/kuklinski_guest_forms_reminder_email.html`, `drafts/kuklinski_insurance_email.html`, `comms/kuklinski_email_drafts.md` (611 lines of lifecycle drafts).

---

### HAT 2: DEMBE (A2) — Research Engine

| Role | Lifecycle Function | Touchpoints | Search Window | Send Date |
|------|-------------------|-------------|---------------|-----------|
| Airfare research | RIC→PTY, RSW→FLL fare monitoring | TP 1.2 | Apr 21–Jun 10 | Jun 17 |
| Hotel research | Panama City pre-cruise, FLL post-cruise | TP 1.3 | Apr 21–Jun 10 | Jun 17 |
| Excursion research | 5 ports × top options | TP 2.1 | May 5–Jul 25 | Aug 1 |
| Dining research | Onboard specialty + port restaurants | TP 2.3 | Jun 16–Sep 11 | Sep 18 |
| Document audit | Passports, visas, health docs, guest forms | TP 2.4 | Jul 1–Sep 11 | Sep 18 |
| Pre-voyage brief | Destination guides, packing, logistics | TP 3.1 | Aug 25–Nov 19 | Nov 26 |

**Weekly reports (Mon AM)** to johnloucks3@gmail.com across 3 concurrent streams.

**D2M value:** Everything the client sees starts here. No research = no products. Dembe is the data engine.

**Proven in Kuklinski:** `touchpoints.json` ARC1/ARC2/ARC3 search params, `output/DRAFT_Kuklinski_TP2.6_Excursion_Recommendations_20260521.md`, lifecycle doc sec 7 staff load (6 touchpoints, 7-month active window).

---

### HAT 3: HARLAN (A9) — Cost Validation

| Role | Lifecycle Function | Touchpoints | Window |
|------|-------------------|-------------|--------|
| Cost analysis per research item | Validates Dembe's findings against budget | TP 1.2, 1.3, 2.1, 2.3 | Apr 21–Sep 18 |
| Survey design (merged from Sterling) | Post-voyage NPS + experience survey | TP 5.2 | Dec 29–Jan 10 |

**Merger:** A7 Sterling (budget/finance) folded into Harlan. Same function, one hat.

**D2M value:** Dembe finds options. Harlan answers "how much?" and "is this a deal?" Turns raw data into costed recommendations.

---

### HAT 4: HALE — Quality Gate

| Role | Lifecycle Function | Touchpoints | Details |
|------|-------------------|-------------|---------|
| WF-17 quality gate | Stationery, logo, sig block, tone check | ALL outbound TPs | Before every client email |
| Final confirmation | All bookings consolidated | TP 3.2 | Dec 1–8 compile, Dec 10 send |
| Orchestration | Weekly report cadence, staff pipeline | Continuous | Lifecycle doc sec 6 |

**WF-17 gate checklist:**
- Logo renders correctly
- Stationery: cream #f7f3ea, blue #0000ff, Georgia serif
- From: concierge@d2mluxury.quest
- Sign-off: "Thanks" or "Thank you" (never "Best")
- No AI disclaimers, no "happy to help," no concierge announcements
- Phone: 719-291-0742

**D2M value:** The "is this ready?" check. One set of eyes before anything reaches the Commander.

---

## STRATEGIC HATS (on-call, not lifecycle)

These personas cover edge cases and infrastructure — active for narrow windows or on-demand only.

| Hat | When Used | Why Keep |
|-----|-----------|----------|
| **JET** | Pricing infrastructure breaks or needs building | Tooling (Centrav, Kiwitaxi, Hotelbeds), fare watches, automation scripts. No client-facing role. |
| **TALON** | A TP needs rescheduling or exception handling | Ops standard-setter for Dani. Only surfaces when ops posture changes. |
| **CASTILLO (A5)** | Next-voyage planning (Jan 2027) | TP 5.4 only. Strategic fare timing (Apr–Jun). 2 narrow windows per lifecycle. |
| **REYES (A8)** | Readiness dashboard (potential) | Trip readiness view: are all components green? Not yet built. |
| **A10** | Vendor negotiation needed | Viking executive relationship, contract renewal. On-demand only. |

---

## ELIMINATED

These 7 USAF-scale personas have zero lifecycle touchpoints, zero dates, and zero deliverables in the Kuklinski lifecycle — or any other. They are eliminated from the delivery chain.

| Persona | USAF Role | Why Eliminated |
|---------|-----------|----------------|
| **A12 ELON** | Program killer | "What services to retire" has no lifecycle function. No touchpoint, no deliverable. |
| **A4 Logistics** | Supply chain | Behind-the-scenes infrastructure. No client-facing lifecycle role. |
| **A11 Horizon** | AI/tech R&D | Innovation pipeline, not delivery pipeline. No lifecycle application. |
| **A1 Navarro** | Manpower | "Manage 320K careers" does not map to managing 6 clients. Portfolio management = Commander. |
| **CH Washington** | Chief of Staff | Gates TALON's inbox. Overlaps HALE. Too many chiefs in a 1-person shop. |
| **EXEC Naia** | XO to TALON | Voice review function merges into Dani's quality step. Not a standalone lifecycle role. |
| **A7 Sterling** | Budget/finance | Same function as Harlan. Merged into A9. |

---

## DELIVERY PIPELINE (simplified)

```
COMMANDER ──────────────────────────────────── (you approve)
  ↑                                                   │
HALE (gate: is it ready?)                             │
  ↑                                                   │
HARLAN (cost: does this price make sense?)              │
  ↑                                                   │
DEMBE (research: what are the options?)                 │
  ↑                                                   ↓
[DATA IN ── fares, hotels, excursions, dining]    DANI → CLIENT
```

For each TP:
1. **Dembe** researches → delivers raw findings
2. **Harlan** cost-validates → delivers costed options
3. **Hale** quality-gates → checks readiness
4. **Commander** approves or sends back
5. **Dani** formats → sends

---

## HOW TO USE THIS

These are **hats you put on** for specific problems:

| Situation | Put on | Ask |
|-----------|--------|-----|
| Writing to a client | **Dani** | "What does Dani sound like here?" |
| Need pricing data | **Dembe** | "What would Dembe research?" |
| Need to validate cost | **Harlan** | "Does Harlan approve this price?" |
| Is this ready to send? | **Hale** | "Would Hale pass this through the gate?" |
| Pricing tool is broken | **JET** | "What infrastructure fix does JET need?" |
| Client wants something exceptional | **TALON** | "Does TALON approve the ops exception?" |
| Planning next year's trips | **Castillo** | "What would Castillo's strategy be?" |
| Need a vendor relationship | **A10** | "How would A10 approach this partner?" |

---

## NEXT STEP

Classify all sent emails from johnloucks3@gmail.com (Dec 1, 2025 – present) against these hats to measure:
- Which hat did I actually wear, and when?
- Are there emails that don't fit any hat?
- Is the hat rack complete, or is a hat missing?

---

*D2M Re-org v1 · Dreams2Memories Travel, LLC · 2026-05-17*
