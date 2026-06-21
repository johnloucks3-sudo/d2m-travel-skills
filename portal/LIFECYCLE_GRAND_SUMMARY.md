# THUNDERBIRD LIFECYCLE — GRAND SUMMARY
## Dreams2Memories Travel, LLC | Thunderbird Wing
### Version 1.0 | Owner: Col Victoria Hale, COS | Created 2026-04-19

> **Document Purpose:** Universal reference for the D2M client lifecycle — readable by humans, AI agents, and automated systems.
> This document is **not** booking-specific. It describes the canonical framework applied to all bookings.
> For booking-specific lifecycle plans, see `D2M/lifecycle/`.

---

## TABLE OF CONTENTS

1. [For Humans: Client Perspective](#1-for-humans-client-perspective)
2. [For Staff: Wing Perspective](#2-for-staff-wing-perspective)
3. [For AI: Machine Perspective](#3-for-ai-machine-perspective)
4. [The 6 Phases](#4-the-6-phases)
5. [The Staff Pipeline Flow](#5-the-staff-pipeline-flow)
6. [Weekly Report Cadence](#6-weekly-report-cadence)
7. [WF-17 Quality Gate](#7-wf-17-quality-gate)
8. [Key External Deadlines](#8-key-external-deadlines)
9. [Machine-Readable Summary](#9-machine-readable-summary)

---

## 1. FOR HUMANS: CLIENT PERSPECTIVE

### What the Journey Feels Like

From the moment a booking is confirmed, a client of Dreams2Memories Travel, LLC is never left to wonder what comes next. The lifecycle is a continuous, proactive sequence of value touches — research delivered before it's asked for, reminders sent before deadlines loom, and a concierge voice (Dani) that always knows exactly where they stand.

---

### Phase 0 — Onboarding (First Week After Booking)

The client receives a warm welcome email confirming every detail of their booking — ship, suite, dates, total paid, shipboard credits, and balance due. Any open items (guest registration, guest forms, insurance) are flagged immediately with clear next-step guidance.

Within 7-14 days, a dedicated insurance discussion follows — travel protection options sized to the client's ages, destinations, and risk profile.

**What the client feels:** "They already know everything about my booking. They're on top of it."

---

### Phase 1 — Discovery (2-6 Months Before Embarkation)

Before the client has started thinking about the details, the wing has already been working for weeks. They receive:

- A **Voyage Preview** — a destination guide covering every port of call, written with narrative richness, not just facts.
- **Airfare Watch** — current fare options, routing recommendations, and booking timing strategy for their specific origin cities.
- **Hotel Options** — pre-cruise and post-cruise stay recommendations near embarkation/disembarkation ports, with names, links, and pricing.

**What the client feels:** "They found options I never would have thought to look for."

---

### Phase 2 — Momentum (5-3 Months Before Embarkation)

The trip starts to become real. Research deepens into experiences:

- **Excursion Recommendations** — curated port-by-port excursion options, delivered *before* the cruise line's booking window opens so the client can move the moment the portal goes live.
- **Monthly Validation** — a brief, friendly check-in each month confirming booking status, upcoming milestones, and any action items.
- **Dining Research** — specialty dining options aboard the ship, plus port restaurant recommendations.
- **Document Audit** — a comprehensive check of passports, visas, guest registration, and health documentation.

**What the client feels:** "They're thinking ahead of things I wouldn't have remembered to check."

---

### Phase 3 — Pre-Departure (3 Weeks to 3 Days Before Embarkation)

The final stretch. Three coordinated touchpoints close out the pre-voyage sequence:

- **Pre-Voyage Brief (E-21)** — a comprehensive trip packet: confirmed excursions, dining, weather forecasts, packing guidance, app reminders, emergency contacts, and logistics for every leg of travel.
- **Final Confirmation (E-7)** — every booking, reservation, and transfer locked and confirmed in a single scannable document.
- **Send-Off (E-3)** — a warm bon voyage with last-minute tips, embarkation logistics, and the wing's genuine enthusiasm for their voyage.

**What the client feels:** "I'm ready. Everything is handled."

---

### Phase 4 — Payment (Conditional: Bookings with Balance Due)

For clients with outstanding final payment dates, the wing runs a dedicated payment sequence:

- Three reminders at FPD-21, FPD-14, and FPD-7 days — each with clear payment instructions and escalating urgency.
- Post-payment confirmation verifying the balance cleared and all shipboard credits remain intact.

**What the client feels:** "I never missed a deadline. They made sure of it."

---

### Phase 5 — Post-Voyage (1-4 Weeks After Disembarkation)

The voyage ends; the relationship does not. Within a week of returning home, the client receives a warm welcome-home message. Over the following three weeks:

- A **post-voyage survey** captures what worked and what didn't — used to sharpen future recommendations.
- A **personalized thank-you** reinforces the relationship and opens a door to referrals.
- A **next voyage plant** seeds the next adventure based on preferences, interests, and patterns the wing has learned throughout the lifecycle.

**What the client feels:** "This wasn't a transaction. They care about the next chapter too."

---

## 2. FOR STAFF: WING PERSPECTIVE

### How the Wing Runs a Lifecycle

Every booking assigned to the Thunderbird Wing follows the same canonical framework. Hale (COS) owns orchestration from booking confirmation through post-voyage close. Staff assignments are pre-determined per touchpoint. No one waits to be tasked — the lifecycle document is the tasking order.

---

### Phase 0 — Onboarding

**Trigger:** Booking confirmed, payment received (or deposit received + final payment date set).

**Actions:**
1. Hale creates/updates the client dossier (`core/booking/thunderbird_dossier.py`).
2. Hale updates `THUNDERBIRD_MASTER_PLAN.md` and the Booking Master Google Sheet.
3. **TP 0.5 — Welcome/Validation:** Hale drafts the welcome/validation email. Dani formats. Hale runs WF-17 gate. Commander approves. Sent to client within 7 days of booking.
4. **TP 0.6 — Insurance:** A9 Harlan pulls insurance quotes (Allianz, Travel Guard, IMG Global). Hale + A9 build the recommendation. Dani formats. WF-17 gate. Sent within 14 days of booking.
5. Guest forms monitored via `core/booking/thunderbird_guest_forms.py` — gaps flagged in weekly report.

**Staff load:** Hale (lead), A9 (insurance quotes), Dani (formatting + send).

---

### TP 3.5 — Insurance Guidance (T-250) *(Formalized 2026-06-12 — Commander directive)*

**Trigger:** 250 days before embarkation. Fires automatically when T-250 milestone is reached. Positioned between Welcome/Validation (TP 0.5) and Specialty Dining reminder.

**Purpose:** Proactive insurance guidance at the optimal enrollment window. Covers: (1) insurance option comparison (Allianz vs. Seven Corners vs. Travel Guard); (2) pre-existing condition waiver reminder — most waivers require enrollment within 14–21 days of *initial* deposit, but T-250 serves clients with long booking windows who haven't yet committed to a policy; (3) coverage gap analysis vs. credit card coverage (e.g., Chase Sapphire Reserve caps at $10K/pp — not sufficient for luxury cruise cancellation).

**Chain:** Luna (voice) → Naia (brand) → Dani (client register) → WF-17 gate → Commander approval.

**Staff load:** A9 Harlan (insurance quotes + gap analysis), A6 Luna (voice), Naia (brand), Dani (client-facing email), Hale (routing + WF-17 gate).

**Note:** This is the repeatable insurance template for all clients. Replaces ad hoc insurance emails that previously bypassed the creative chain.

---

### Phase 1 — Discovery

**Trigger:** Search windows open automatically based on embarkation date. Airfare and hotel windows open approximately E-180 to E-120. Voyage preview sent approximately E-150 to E-90.

**Actions:**
1. **TP 1.1 — Voyage Preview:** A2 Dembe researches all ports of call — history, highlights, practical logistics. A6 Luna writes narrative copy and selects imagery. Hale reviews. Dani formats and sends after WF-17 gate and Commander approval.
2. **TP 1.2 — Airfare Watch:** A2 Dembe researches fare options for all origin/destination city pairs. A5 Viper adds booking strategy and timing recommendation. Delivered to Commander as weekly intel report (full send, no WF-17 gate). Client-facing summary via Dani after Commander approval.
3. **TP 1.3 — Hotel Options:** A2 researches pre/post-cruise hotel options near embarkation and disembarkation ports. A6 polishes descriptions. A9 costs the options. Dani formats the client email. WF-17 gate + Commander approval before send.

**Weekly report stream (Discovery period):** Airfare + Hotel combined, sent Monday AM to johnloucks3@gmail.com as full send.

**Staff load:** A2 Dembe (heavy — all research), A6 Luna (voyage preview + hotel copy), A5 Viper (airfare strategy), A9 Harlan (hotel cost comparison), Hale (QC + weekly reports), Dani (client-facing emails).

---

### Phase 2 — Momentum

**Trigger:** Approximately E-120 to E-45. Research windows determined by cruise line portal opening dates (immovable hard anchors).

**Actions:**
1. **TP 2.1 — Excursion Research:** A2 researches every port — cruise-line excursions vs. independent options, pricing, capacity, booking urgency. A6 writes curated descriptions. Delivered to client *before* the cruise line's excursion booking window opens. Commander approval required before sending to client. **Hard constraint: excursion research must be complete before portal opens.**
2. **TP 2.2 — Monthly Validation:** Hale sends a rolling monthly check-in to Commander (full send). Content: booking status, payment status, upcoming milestones, open guest form gaps, flagged risks. Sent on the 1st or 15th of each month depending on booking.
3. **TP 2.3 — Dining Research:** A2 researches onboard specialty dining and port restaurant options. Timed to arrive before the cruise line's dining reservation window opens. Dani formats client email.
4. **TP 2.4 / 2.5 — Document Audit:** Hale runs a structured document check — passports, visas, guest registration completion, health documentation, emergency contacts. Gaps escalated to P0 if within 90 days of embarkation.

**Weekly report stream (Momentum period):** Excursion research, Dining intel — Monday AM full sends.

**Staff load:** A2 Dembe (excursion + dining research), A6 Luna (excursion descriptions), Hale (monthly validation + document audit), A9 Harlan (cost comparisons), Dani (all client-facing emails).

---

### Phase 3 — Pre-Departure

**Trigger:** E-30 to E-3. Three fixed sends. EXEC Naia Solberg-Vega enters for voice review on high-touch emails (Pre-Voyage Brief, Final Confirmation, Send-Off).

**Actions:**
1. **TP 3.1 — Pre-Voyage Brief (E-21):** A2 compiles the full trip packet — confirmed bookings, weather, packing, logistics, excursion schedule, dining reservations, app reminders. A6 polishes tone and imagery. Hale reviews and coordinates. Naia runs voice review. Dani formats. WF-17 gate + Commander approval.
2. **TP 3.2 — Final Confirmation (E-7):** Hale compiles every booking confirmation, reservation, and transfer into a single lockdown document. Naia voice review. Dani formats. WF-17 gate + Commander approval.
3. **TP 3.3 — Send-Off (E-3):** A6 Luna leads copy with Hale oversight. Warm, personalized bon voyage. Naia voice review. Dani formats. WF-17 gate + Commander approval.

**Staff load:** Hale (compilation + QC), A2 (research + trip packet), A6 (creative copy), Naia (voice review — all 3 TPs), Dani (formatting + send).

---

### Phase 4 — Payment (Conditional)

**Trigger:** Only for bookings with outstanding balance. Activates at FPD-21.

**Actions:**
1. **TP 4.1 — Reminder #1 (FPD-21):** A9 prepares the payment summary. Hale sends to Commander as a report (full send). If client-facing reminder needed: Dani formats, WF-17 gate.
2. **TP 4.2 — Reminder #2 (FPD-14):** Escalated tone. Confirm payment method on file. Card expiration check.
3. **TP 4.3 — Payment Goal (FPD-7):** Urgency. Target: pay this week, not on deadline day.
4. **TP 4.4 — Final Payment Due (FPD):** A9 monitors. Hale confirms receipt. If not received by end of business: escalate to Commander immediately.
5. **TP 4.5 — Payment Confirmation (FPD+7):** A9 verifies balance cleared. Dossier updated. Master Plan updated. Commander informed via full send.

**Staff load:** A9 Harlan (all payment tracking), Hale (oversight + Commander reports), Dani (client-facing payment reminders if needed).

---

### Phase 5 — Post-Voyage

**Trigger:** Disembarkation date + rolling calendar (E+7, E+14, E+21, E+30).

**Actions:**
1. **TP 5.1 — Welcome Home (E+7):** Dani sends warm welcome-home. A6 may contribute a highlight phrase. Naia voice review on high-value clients.
2. **TP 5.2 — Post-Voyage Survey (E+14):** A7 Gauge designs the survey. Hale deploys via `core/client/thunderbird_survey.py`. Results go to Commander for review.
3. **TP 5.3 — Thank You + Referral (E+21):** Dani with A6 input. Personalized, handwritten tone. Referral ask embedded naturally. Naia voice review.
4. **TP 5.4 — Next Voyage Plant (E+30):** A5 Viper develops next-voyage strategy based on preferences learned. A2 begins preliminary research. Dani delivers the seed email. Dossier captures next-voyage interest.

**Staff load:** Dani (all client-facing), A6 (copy input), A7 Gauge (survey), A5 Viper (next-voyage strategy), Naia (voice review on 5.1 + 5.3), Hale (orchestration + final dossier close).

---

## 3. FOR AI: MACHINE PERSPECTIVE

### How an AI Agent Executes a Touchpoint

Each touchpoint follows the same execution sequence. An AI agent receiving a lifecycle task should:

1. **Load context:** Read the client dossier from `~/Thunderbird/dossiers/`. Load client context from `~/Thunderbird/storage/cache/client_context/<client>_context.json`.
2. **Identify the TP:** Match to the canonical touchpoint ID (e.g., `1.2`) and confirm the search window is open based on today's date vs. embarkation date.
3. **Execute the staff pipeline in order:** A2 research → (A6 creative | A9 financial) → A5 strategy (if applicable) → Hale review → Dani format → Commander approval → Send.
4. **Write outputs to correct paths:** Research findings to `~/Thunderbird/intel/`. Draft emails to `~/Thunderbird/drafts/`. Final dossier updates via `core/booking/thunderbird_dossier.py`.
5. **Run WF-17 gate** (for all client-facing emails) via `core/email/thunderbird_presend_evaluator.py` before surfacing to Commander.
6. **Post completion:** Update dossier, update `THUNDERBIRD_MASTER_PLAN.md`, update Booking Master Sheet.

### Per-Touchpoint Machine Reference Table

| TP ID | Phase | Name | T-Minus Window | Staff Pipeline (ordered) | Primary .py Entry | MCP Tool |
|-------|-------|------|---------------|--------------------------|-------------------|----------|
| 0.5 | Onboarding | Welcome / Validation | E-∞ to E-∞ (send within 7 days of booking) | Hale → Dani → WF-17 → Commander | `thunderbird_dossier.py` | `gmail_create_draft` |
| 0.6 | Onboarding | Insurance Discussion | Send within 14 days of booking | A9 → Hale → Dani → WF-17 → Commander | `thunderbird_quote_render.py` | `gmail_create_draft` |
| 1.1 | Discovery | Voyage Preview | E-180 to E-90 (research); E-90 (send) | A2 → A6 → Hale → Dani → WF-17 → Commander | `thunderbird_ship_intel.py` | `gmail_create_draft` |
| 1.2 | Discovery | Airfare Watch | E-180 to E-90 (research); E-120 (send) | A2 → A5 → Hale (full send to Commander) | `thunderbird_price_monitor.py` | `flight_price_tool` |
| 1.3 | Discovery | Hotel Options | E-150 to E-90 (research); E-90 (send) | A2 → A6 → A9 → Hale → Dani → WF-17 → Commander | `thunderbird_ship_intel.py` | `hotel_price_tool` |
| 2.1 | Momentum | Excursion Recs | E-120 to E-60 (research); before portal open | A2 → A6 → Hale → Dani → WF-17 → Commander | `thunderbird_ship_intel.py` | `tour_price_tool` |
| 2.2 | Momentum | Monthly Validation | Rolling: 1st or 15th of each month | Hale → Commander (full send) | `thunderbird_validation.py` | `gmail_send_email` (within-wing) |
| 2.3 | Momentum | Dining Research | E-90 to E-60 (research); before dining portal | A2 → A6 → Hale → Dani → WF-17 → Commander | `thunderbird_ship_intel.py` | `gmail_create_draft` |
| 2.4 | Momentum | Document Audit | E-90 to E-75 | Hale → Commander (full send) | `thunderbird_validation.py` | `gmail_send_email` (within-wing) |
| 3.1 | Pre-Departure | Pre-Voyage Brief | E-30 to E-22 (compile); E-21 (send) | A2 → A6 → Hale → Naia → Dani → WF-17 → Commander | `thunderbird_dani_engine.py` | `gmail_create_draft` |
| 3.2 | Pre-Departure | Final Confirmation | E-14 to E-8 (compile); E-7 (send) | Hale → Naia → Dani → WF-17 → Commander | `thunderbird_dani_engine.py` | `gmail_create_draft` |
| 3.3 | Pre-Departure | Send-Off | E-5 to E-4 (draft); E-3 (send) | A6 → Hale → Naia → Dani → WF-17 → Commander | `thunderbird_dani_engine.py` | `gmail_create_draft` |
| 4.1 | Payment | Reminder #1 (FPD-21) | FPD-22 to FPD-22 | A9 → Hale → Commander (full send) | `thunderbird_commission_recon.py` | `gmail_send_email` (within-wing) |
| 4.2 | Payment | Reminder #2 (FPD-14) | FPD-15 to FPD-15 | A9 → Hale → Dani → WF-17 → Commander | `thunderbird_commission_recon.py` | `gmail_create_draft` |
| 4.3 | Payment | Payment Goal (FPD-7) | FPD-8 to FPD-8 | A9 → Hale → Dani → WF-17 → Commander | `thunderbird_commission_recon.py` | `gmail_create_draft` |
| 4.4 | Payment | Final Payment Due | FPD (day of) | A9 → Hale (monitor + escalate if missed) | `thunderbird_commission_recon.py` | `gmail_send_email` (within-wing alert) |
| 4.5 | Payment | Payment Confirmation | FPD+6 to FPD+7 | A9 → Hale → Commander (full send) | `thunderbird_reconciliation.py` | `gmail_send_email` (within-wing) |
| 5.1 | Post-Voyage | Welcome Home | E+6 to E+7 | A6 → Dani → (Naia if high-value) → WF-17 → Commander | `thunderbird_dani_email.py` | `gmail_create_draft` |
| 5.2 | Post-Voyage | Post-Voyage Survey | E+13 to E+14 | A7 → Hale → deploy | `thunderbird_survey.py` | `gmail_send_email` |
| 5.3 | Post-Voyage | Thank You + Referral | E+20 to E+21 | A6 → Dani → Naia → WF-17 → Commander | `thunderbird_dani_email.py` | `gmail_create_draft` |
| 5.4 | Post-Voyage | Next Voyage Plant | E+29 to E+30 | A5 → A2 → Dani → WF-17 → Commander | `thunderbird_dani_engine.py` | `gmail_create_draft` |

**All .py entries are relative to `~/Thunderbird/core/`. Full paths:**
- `core/booking/thunderbird_dossier.py`
- `core/booking/thunderbird_guest_forms.py`
- `core/booking/thunderbird_commission_recon.py`
- `core/booking/thunderbird_reconciliation.py`
- `core/client/thunderbird_validation.py`
- `core/client/thunderbird_quote_render.py`
- `core/client/thunderbird_survey.py`
- `core/email/thunderbird_dani_engine.py`
- `core/email/thunderbird_dani_email.py`
- `core/email/thunderbird_presend_evaluator.py` (WF-17 gate)
- `core/email/thunderbird_gmail.py` (all Gmail operations)
- `core/intel/thunderbird_ship_intel.py`
- `core/intel/thunderbird_price_monitor.py`
- `core/mcp/travel_mcp_server.py` (120+ tools — gateway for flight/hotel/tour/transfer lookups)

---

## 4. THE 6 PHASES

> **Note on phase numbering:** The Thunderbird canonical lifecycle uses 6 phases numbered 0–5. Phase 4 (Payment) only activates for bookings with a final payment date (FPD). Fully pre-paid bookings skip Phase 4 and proceed directly from Phase 3 to Phase 5.

| # | Phase Name | Color Code | Timing | Touchpoints | Staff Lead |
|---|-----------|------------|--------|-------------|------------|
| **0** | Onboarding | ![Green](https://via.placeholder.com/10/22c55e/22c55e.png) Green | Within 14 days of booking | TP 0.5, TP 0.6 | Hale (COS) |
| **1** | Discovery | ![Blue](https://via.placeholder.com/10/3b82f6/3b82f6.png) Blue | E-180 to E-90 | TP 1.1, TP 1.2, TP 1.3 | A2 Dembe |
| **2** | Momentum | ![Gold](https://via.placeholder.com/10/f59e0b/f59e0b.png) Gold | E-120 to E-45 | TP 2.1, TP 2.2 (rolling), TP 2.3, TP 2.4 | A2 Dembe / Hale |
| **3** | Pre-Departure | ![Navy](https://via.placeholder.com/10/1e3a5f/1e3a5f.png) Navy | E-30 to E-3 | TP 3.1, TP 3.2, TP 3.3 | Hale + Naia |
| **4** | Payment | ![Red](https://via.placeholder.com/10/ef4444/ef4444.png) Red | FPD-21 to FPD+7 | TP 4.1–4.5 | A9 Harlan |
| **5** | Post-Voyage | ![Purple](https://via.placeholder.com/10/8b5cf6/8b5cf6.png) Purple | E+7 to E+30 | TP 5.1, TP 5.2, TP 5.3, TP 5.4 | Dani + Hale |

### Phase Detail

**Phase 0 — Onboarding**
- Opens: Booking confirmed
- Closes: Insurance discussion sent + guest forms link delivered
- Hard constraint: TP 0.5 must send within 7 days of booking confirmation

**Phase 1 — Discovery**
- Opens: Immediately after Phase 0, but active research begins ~E-180
- Closes: Hotel options sent (~E-90)
- Hard constraint: Airfare search should begin 4-6 months before embarkation (sweet spot for pricing)

**Phase 2 — Momentum**
- Opens: Excursion research begins ~E-120 to E-90
- Closes: Document audit sent (~E-75)
- Hard constraint: **Excursion research must be complete before cruise line portal opens** — this is the most time-sensitive hard anchor in the entire lifecycle
- Monthly validation TPs run continuously throughout Phases 1-3

**Phase 3 — Pre-Departure**
- Opens: E-30
- Closes: Send-Off sent at E-3
- Hard constraint: All logistics (flights, hotels, transfers, excursions, dining) must be confirmed before Pre-Voyage Brief

**Phase 4 — Payment (Conditional)**
- Activates: FPD-21 (only if balance remains outstanding)
- Closes: FPD+7 (payment confirmation)
- Hard constraint: **FPD is non-negotiable — missed FPD = booking cancellation**
- Phase 4 runs in parallel with Phases 1-3 when applicable

**Phase 5 — Post-Voyage**
- Opens: Disembarkation day (E+0)
- Closes: Next voyage plant sent (E+30)
- Soft close: Lifecycle does not formally end until next voyage is seeded

---

## 5. THE STAFF PIPELINE FLOW

### Canonical Flow: Research → Creative → Finance → Strategy → QC → Client → Commander

The D2M staff pipeline is a sequential hand-off chain, not a parallel free-for-all. Each function adds value at a specific stage. No one jumps a step.

```
A2 DEMBE (Research & Intel)
│
│  A2 is always first. She researches destinations, ports, fares, hotels, excursions,
│  dining options, and ship intelligence. She produces raw findings, not client copy.
│  Primary tools: thunderbird_ship_intel.py, thunderbird_price_monitor.py,
│                 travel_mcp_server.py (flight/hotel/tour/transfer lookups)
│
├──► A6 LUNA (Creative Director)
│    │  Luna receives A2's raw research and transforms it into narrative travel copy —
│    │  emotionally resonant descriptions, imagery selection, brand voice. She is the
│    │  difference between a fact sheet and a piece of writing that makes a client
│    │  excited to travel.
│    │  Engaged for: TP 1.1, 1.3, 2.1, 2.3, 3.1, 3.3, 5.1, 5.3
│    │
│    └──► (feeds into Hale review)
│
├──► A9 HARLAN (Finance & Process)
│    │  A9 receives A2's pricing data and produces cost analysis — cost per guest,
│    │  D2M markup, client-facing price options, commission tracking, payment status.
│    │  Never client-facing directly. Outputs go to A5 or Hale.
│    │  Engaged for: TP 0.6, 1.2, 1.3, 4.1–4.5
│    │
│    └──► A5 VIPER (Strategy)
│         │  Viper reviews A9's costed options and adds booking strategy — timing
│         │  recommendations, fare watch logic, risk assessment, next-voyage planning.
│         │  Engaged for: TP 1.2, 5.4
│         │
│         └──► (feeds into Hale review)
│
▼
HALE (COS — Orchestration & Quality Control)
│
│  Hale reviews all inputs from A2/A6/A9/A5. She is the integration point.
│  She runs the WF-17 quality gate before any product surfaces to Commander or Dani.
│  She writes the weekly reports (full send to Commander). She owns all COS-led TPs.
│  File: thunderbird_presend_evaluator.py
│
├──► NAIA (EXEC — Voice Review) [High-Touch TPs only: 3.1, 3.2, 3.3, 5.1, 5.3]
│    │  Naia reviews the final copy for voice consistency, brand tone, and emotional
│    │  landing. She is the last creative check before client delivery.
│    │
│    └──► (feeds into Dani)
│
▼
DANI (A3 — Concierge, Client-Facing Voice)
│
│  Dani is the ONLY client-facing persona. She aggregates all research products
│  (from A2/A6/A9 and Hale's synthesis), crafts the final email in the D2M voice,
│  and presents as the client's dedicated concierge.
│
│  Dani DOES NOT:
│  - Research (that's A2)
│  - Set strategy (that's A5)
│  - Reply to Commander (that's Hale)
│  - Contact suppliers (that's Hale/A2)
│
│  Dani's 3-phase workflow (from thunderbird_dani_engine.py):
│    (1) Aggregate — gather all staff products into a single brief
│    (2) Artist — compose the email in D2M concierge voice
│    (3) Advocate — present as the client's champion/concierge
│
│  File: thunderbird_dani_engine.py / thunderbird_dani_email.py
│
▼
WF-17 QUALITY GATE (Mandatory for all client-facing emails)
│
│  Hale runs the pre-send evaluation checklist via thunderbird_presend_evaluator.py.
│  See Section 7 for full gate criteria.
│
▼
COMMANDER (Send Approval)
│
│  Commander reviews the draft in d2mconcierge Gmail.
│  He approves, edits, or rejects.
│  No client email sends without explicit Commander "yes."
│
▼
CLIENT (Recipient)
   Email from: concierge@d2mluxury.quest (send-as alias on d2mconcierge@gmail.com)
   Stationery: cream #f7f3ea, blue #0000ff, Georgia serif, D2M navy banner logo
```

### Special Routing: Commander-as-Client

When the Commander is also the client (e.g., Loucks personal voyages), the flow simplifies:
- No WF-17 gate required for Commander-directed communications
- Hale sends reports directly to johnloucks3@gmail.com as full sends
- Any co-traveler communications (e.g., Lyons) still require full WF-17 + Commander approval

---

## 6. WEEKLY REPORT CADENCE

All weekly reports are **FULL SENDS to johnloucks3@gmail.com** per Standing Order 27 MAR 2026. Not drafts — these fire without Commander approval gate.

### Report Streams by Phase

| Report Stream | Active Period | Frequency | Send Day | Owner | Content |
|--------------|---------------|-----------|----------|-------|---------|
| **Discovery Combined** | Phase 1 search window | Weekly | Monday AM | A2 Dembe | Fare trends (all routing pairs), hotel options progress, booking timing recs |
| **Excursion Research** | Phase 2 early window | Weekly | Monday AM | A2 Dembe | Port-by-port excursion options, Viking/Regent/independent comparison, booking urgency |
| **Dining Intel** | Phase 2 mid window | Weekly | Monday AM | A2 Dembe | Onboard specialty dining, port restaurant recs, reservation timing |
| **Monthly Validation** | Phase 1 through Phase 3 | Monthly | 1st or 15th | Hale | Booking status, payment status, upcoming milestones, guest form gaps, flagged risks |
| **Pre-Voyage Brief Assembly** | Phase 3 early | Weekly | Monday AM | A2 + Luna | Destination guides, packing lists, weather, logistics, confirmed reservations |
| **Payment Tracking** | Phase 4 (if active) | Weekly | Monday AM | A9 | Balance status, payment method confirmed, deadline countdown |
| **Post-Voyage Close** | Phase 5 | Per-send | Per TP | Hale | Welcome home, survey results, thank-you confirmation, next-voyage seed |

### Overlap Calendar (Relative to Embarkation)

| T-Minus Range | Active Report Streams |
|---------------|----------------------|
| E-180 to E-150 | Discovery Combined |
| E-150 to E-120 | Discovery Combined, Excursion Research |
| E-120 to E-90 | Discovery Combined, Excursion Research, Payment (if FPD in range) |
| E-90 to E-60 | Excursion Research, Dining Intel |
| E-60 to E-30 | Dining Intel, Pre-Voyage Brief Assembly |
| E-30 to E-3 | Pre-Voyage Brief Assembly (closes at E-21 send) |
| FPD-21 to FPD+7 | Payment Tracking (parallel, whenever active) |
| E+7 to E+30 | Post-Voyage Close |

### Formatting Standards for All Reports

- **Destination:** johnloucks3@gmail.com (full send — no draft step)
- **Sent from:** d2mconcierge@gmail.com
- **Format:** Scannable headers, tables for data, clickable hyperlinks on every source
- **Tone:** Intel report style — structured, direct, actionable
- **Length:** As long as needed to cover content; sub-sections for each active topic

---

## 7. WF-17 QUALITY GATE

**Applies to:** All client-facing emails (any send to any address outside the wing, except johnloucks3@gmail.com).

**Owner:** Hale (COS), supported by `core/email/thunderbird_presend_evaluator.py`.

**Gate is mandatory. No bypasses. Bypass attempt = 24-hour hold.**

### Checklist (All 8 Must Pass)

| # | Check | Standard |
|---|-------|----------|
| 1 | **Logo renders** | D2M navy banner renders in email preview — not broken image |
| 2 | **From address** | concierge@d2mluxury.quest (send-as alias on d2mconcierge@gmail.com) |
| 3 | **Sig block correct** | Name: Dani Moreau, D2M Luxury Travel Concierge. Phone: 719-291-0742. |
| 4 | **Paper color** | Cream background #f7f3ea — not white |
| 5 | **Ink color** | Bright blue #0000ff — not default black |
| 6 | **Font** | Georgia, serif — not Arial or system default |
| 7 | **Sign-off** | "Thanks" or "Thank you" — NEVER "Best," never "Warm regards," never "Sincerely" |
| 8 | **Content clean** | No AI disclaimers. No "happy to help." No "I'd be happy to assist." No concierge announcement ("As your concierge..."). No ⚠ unpaid markers visible to client. |

### WF-17 Pass Criteria

All 8 checks must pass. If any check fails:
1. Product is returned to Dani for correction.
2. Hale logs the gate failure.
3. Product is re-submitted after correction.
4. Gate runs again from scratch on the corrected version.

### WF-17 Exempt Sends

The following do not require WF-17 gate:
- Weekly intel reports → johnloucks3@gmail.com (within-wing, full send)
- Monthly validation reports → johnloucks3@gmail.com (within-wing, full send)
- Payment tracking reports → johnloucks3@gmail.com (within-wing, full send)
- Any report classified as "wing-to-Commander intel" under SO 27 MAR 2026

---

## 8. KEY EXTERNAL DEADLINES

These deadlines are determined by cruise lines and cannot be moved. All lifecycle planning anchors to these immovable dates.

### Cruise Line Portal Windows (Hard Anchors)

| Line | Window Type | Typical Open Date | Notes |
|------|-------------|------------------|-------|
| **Regent Seven Seas** | Shore excursion portal | ~E-210 (7 months out) | Popular excursions sell out within days. Pre-research mandatory. |
| **Regent Seven Seas** | Culinary Arts Kitchen Classes | ~E-120 (4 months out) | Book opening night — limited seats |
| **Regent Seven Seas** | Dining reservations | ~E-90 (3 months out) | Book opening night for specialty venues |
| **Regent Seven Seas** | Online check-in | E-21 | Guest registration MUST be complete before this date |
| **Viking** | Shore excursion portal | ~E-120 (4 months out) | Viking excursions sell out fast. Pre-research mandatory. |
| **Silversea** | Shore excursion portal | ~E-90 (3 months out) | Varies by voyage — verify per booking |
| **Oceania** | Shore excursion portal | ~E-90 | OLife included excursions require selection before sail date |
| **Seabourn** | Dining / Spa reservations | ~E-60 | Pre-booking recommended for popular venues |

### Standard Booking Windows (D2M Planning Norms)

| Item | Search Window Opens | Optimal Send To Client | Rationale |
|------|--------------------|-----------------------|-----------|
| International airfare | E-180 | E-120 to E-90 | Sweet spot: 4-6 months out for transatlantic/transpacific routes |
| Domestic airfare | E-120 | E-90 | 3-4 months adequate for domestic routes |
| Pre/post-cruise hotels | E-150 | E-90 | 3-5 months for hotel availability and rate stability |
| Ground transfers | E-60 | E-45 | 45-60 days adequate; book after flights confirmed |
| Travel insurance | Booking day | Within 14 days of deposit | Pre-existing condition waiver window typically 14-21 days from deposit |
| Passport verification | Phase 0 + Phase 2 audit | Audit at E-90, escalate if issue | Must be valid 6+ months post-disembarkation |

### Guest Registration Deadlines

| Line | Registration Deadline | Consequence of Miss |
|------|-----------------------|--------------------|
| Regent Seven Seas | Before online check-in opens (E-21) | Cannot complete online check-in; delays boarding |
| Viking | Before embarkation day | May require manual processing at port |
| Silversea | Before embarkation day | Boarding delay risk |

**D2M Standard:** Guest registration flagged in TP 0.5. Audited in TP 2.4/2.5. If incomplete at E-90, escalate to P0.

### Final Payment Dates (FPD Rules)

| Line | Typical FPD | Cancellation Risk Window |
|------|------------|--------------------------|
| Regent Seven Seas | ~E-150 (5 months out) | 100% penalty 0-14 days before sail |
| Viking | ~E-120 (4 months out) | 100% penalty within 120 days |
| Silversea | ~E-120 (4 months out) | Varies by fare class |
| Oceania | ~E-90 (3 months out) | 100% penalty within 90 days |

**D2M Standard:** Payment sequence activates at FPD-21. Three reminders. Verify payment posted within FPD+7.

---

## 9. MACHINE-READABLE SUMMARY

```json
{
  "system": "Thunderbird OS — Dreams2Memories Travel, LLC",
  "document": "LIFECYCLE_GRAND_SUMMARY",
  "version": "1.0",
  "created": "2026-04-19",
  "owner": "Col Victoria Hale, COS",
  "description": "Canonical lifecycle framework for all D2M client bookings. All t_minus values are relative to embarkation date (E). Negative = before embarkation. Positive = after disembarkation.",

  "phases": [
    {
      "id": 0,
      "name": "Onboarding",
      "color": "#22c55e",
      "timing": "Within 14 days of booking confirmation",
      "staff_lead": "Hale",
      "touchpoints": ["0.5", "0.6"]
    },
    {
      "id": 1,
      "name": "Discovery",
      "color": "#3b82f6",
      "timing": "E-180 to E-90",
      "staff_lead": "A2 Dembe",
      "touchpoints": ["1.1", "1.2", "1.3"]
    },
    {
      "id": 2,
      "name": "Momentum",
      "color": "#f59e0b",
      "timing": "E-120 to E-45",
      "staff_lead": "A2 Dembe / Hale",
      "touchpoints": ["2.1", "2.2", "2.3", "2.4"]
    },
    {
      "id": 3,
      "name": "Pre-Departure",
      "color": "#1e3a5f",
      "timing": "E-30 to E-3",
      "staff_lead": "Hale + EXEC Naia",
      "touchpoints": ["3.1", "3.2", "3.3"]
    },
    {
      "id": 4,
      "name": "Payment",
      "color": "#ef4444",
      "timing": "FPD-21 to FPD+7 (conditional — skip if paid in full at booking)",
      "staff_lead": "A9 Harlan",
      "touchpoints": ["4.1", "4.2", "4.3", "4.4", "4.5"],
      "conditional": true,
      "condition": "booking.balance_due > 0"
    },
    {
      "id": 5,
      "name": "Post-Voyage",
      "color": "#8b5cf6",
      "timing": "E+7 to E+30",
      "staff_lead": "Dani + Hale",
      "touchpoints": ["5.1", "5.2", "5.3", "5.4"]
    }
  ],

  "touchpoints": {
    "0.5": {
      "name": "Welcome / Validation",
      "phase": 0,
      "t_minus_window": "Book+0 to Book+7",
      "send_t_minus": "Book+7",
      "staff_pipeline": ["Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/booking/thunderbird_dossier.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 7,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Confirm all booking details. Flag guest registration gaps. List all key portal dates."
    },
    "0.6": {
      "name": "Insurance Discussion",
      "phase": 0,
      "t_minus_window": "Book+0 to Book+14",
      "send_t_minus": "Book+14",
      "staff_pipeline": ["A9", "Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/client/thunderbird_quote_render.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 14,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Pre-existing condition waiver window is typically 14-21 days from deposit. Quote Allianz, Travel Guard, IMG Global. CFAR add-on worth pricing for bookings over $10K."
    },
    "1.1": {
      "name": "Voyage Preview",
      "phase": 1,
      "t_minus_window": "E-180 to E-93",
      "send_t_minus": "E-90",
      "staff_pipeline": ["A2", "A6", "Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/intel/thunderbird_ship_intel.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 90,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Port-by-port destination guide. A2 researches; A6 writes narrative. Cover every port of call."
    },
    "1.2": {
      "name": "Airfare Watch",
      "phase": 1,
      "t_minus_window": "E-180 to E-123",
      "send_t_minus": "E-120",
      "staff_pipeline": ["A2", "A5", "Hale (report to Commander)"],
      "py_entry": "core/intel/thunderbird_price_monitor.py",
      "mcp_tool": "flight_price_tool",
      "search_window_days": 60,
      "output_type": "intel_report (full send) + client_email (if presenting options)",
      "wf17_required": false,
      "notes": "Weekly fare tracking. All origin/destination city pairs. Sweet spot: book 4-6 months before embarkation for international routes. A5 adds booking strategy."
    },
    "1.3": {
      "name": "Hotel Options",
      "phase": 1,
      "t_minus_window": "E-150 to E-93",
      "send_t_minus": "E-90",
      "staff_pipeline": ["A2", "A6", "A9", "Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/intel/thunderbird_ship_intel.py",
      "mcp_tool": "hotel_price_tool",
      "search_window_days": 60,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Pre-cruise and post-cruise hotels near embarkation/disembarkation ports. Include: name, link, images, customer comments, price (Queen/Double + King/Grand)."
    },
    "2.1": {
      "name": "Excursion Recommendations",
      "phase": 2,
      "t_minus_window": "E-120 to E-[portal_open+1]",
      "send_t_minus": "E-[portal_open] (day of portal opening or day before)",
      "staff_pipeline": ["A2", "A6", "Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/intel/thunderbird_ship_intel.py",
      "mcp_tool": "tour_price_tool",
      "search_window_days": 60,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "HARD CONSTRAINT: Must be delivered BEFORE cruise line excursion portal opens. Research: cruise-line options vs. independent, pricing, capacity urgency. A6 writes curated descriptions."
    },
    "2.2": {
      "name": "Monthly Validation",
      "phase": 2,
      "t_minus_window": "Rolling E-150 to E-30",
      "send_t_minus": "1st or 15th of each month",
      "staff_pipeline": ["Hale", "Commander (full send)"],
      "py_entry": "core/client/thunderbird_validation.py",
      "mcp_tool": "gmail_send_email",
      "search_window_days": 0,
      "output_type": "intel_report (full send to Commander)",
      "wf17_required": false,
      "notes": "Rolling monthly check-in. Content: booking status, payment status, upcoming milestones, guest form gaps, flagged risks. Full send to johnloucks3 — no draft step."
    },
    "2.3": {
      "name": "Dining Research",
      "phase": 2,
      "t_minus_window": "E-90 to E-[dining_portal+1]",
      "send_t_minus": "E-[dining_portal] (day of dining portal opening or day before)",
      "staff_pipeline": ["A2", "A6", "Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/intel/thunderbird_ship_intel.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 30,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Onboard specialty dining + port restaurant recommendations. Timed to arrive before the cruise line's dining reservation window opens."
    },
    "2.4": {
      "name": "Document Audit",
      "phase": 2,
      "t_minus_window": "E-90 to E-76",
      "send_t_minus": "E-75",
      "staff_pipeline": ["Hale", "Commander (full send)"],
      "py_entry": "core/client/thunderbird_validation.py",
      "mcp_tool": "gmail_send_email",
      "search_window_days": 15,
      "output_type": "client_email (if action required) + intel_report",
      "wf17_required": true,
      "notes": "Check: passports (valid 6+ months post-disembark), visas, guest registration, ticket contract, emergency contacts, dietary/medical in cruise line system. Escalate to P0 if guest registration incomplete within 90 days of embarkation."
    },
    "3.1": {
      "name": "Pre-Voyage Brief",
      "phase": 3,
      "t_minus_window": "E-30 to E-22",
      "send_t_minus": "E-21",
      "staff_pipeline": ["A2", "A6", "Hale", "Naia", "Dani", "WF-17", "Commander"],
      "py_entry": "core/email/thunderbird_dani_engine.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 9,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Comprehensive trip packet: all confirmed bookings, weather forecasts, packing guide, app reminders, emergency contacts, shipboard credit balance. Naia runs voice review. This is the highest-complexity client email in the lifecycle."
    },
    "3.2": {
      "name": "Final Confirmation",
      "phase": 3,
      "t_minus_window": "E-14 to E-8",
      "send_t_minus": "E-7",
      "staff_pipeline": ["Hale", "Naia", "Dani", "WF-17", "Commander"],
      "py_entry": "core/email/thunderbird_dani_engine.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 7,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Every booking, reservation, and transfer confirmed. Scannable format. Nothing left open."
    },
    "3.3": {
      "name": "Send-Off",
      "phase": 3,
      "t_minus_window": "E-5 to E-4",
      "send_t_minus": "E-3",
      "staff_pipeline": ["A6", "Hale", "Naia", "Dani", "WF-17", "Commander"],
      "py_entry": "core/email/thunderbird_dani_engine.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 2,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Bon voyage. Final weather. Embarkation logistics (port address, timing, parking/drop-off). Warm close. A6 leads copy."
    },
    "4.1": {
      "name": "Payment Reminder #1 (FPD-21)",
      "phase": 4,
      "t_minus_window": "FPD-22 to FPD-22",
      "send_t_minus": "FPD-21",
      "staff_pipeline": ["A9", "Hale", "Commander (full send)"],
      "py_entry": "core/booking/thunderbird_commission_recon.py",
      "mcp_tool": "gmail_send_email",
      "search_window_days": 1,
      "output_type": "intel_report (to Commander) + optional client_email",
      "wf17_required": false,
      "conditional": true,
      "notes": "First payment reminder. Balance amount, payment options, deadline date. 21 days to act."
    },
    "4.2": {
      "name": "Payment Reminder #2 (FPD-14)",
      "phase": 4,
      "t_minus_window": "FPD-15 to FPD-15",
      "send_t_minus": "FPD-14",
      "staff_pipeline": ["A9", "Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/booking/thunderbird_commission_recon.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 1,
      "output_type": "client_email",
      "wf17_required": true,
      "conditional": true,
      "notes": "Second reminder. Escalated tone. Confirm payment method. Check card expiration dates."
    },
    "4.3": {
      "name": "Payment Goal (FPD-7)",
      "phase": 4,
      "t_minus_window": "FPD-8 to FPD-8",
      "send_t_minus": "FPD-7",
      "staff_pipeline": ["A9", "Hale", "Dani", "WF-17", "Commander"],
      "py_entry": "core/booking/thunderbird_commission_recon.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 1,
      "output_type": "client_email",
      "wf17_required": true,
      "conditional": true,
      "notes": "Urgency: pay this week, not on deadline day. Avoid last-day risk."
    },
    "4.4": {
      "name": "Final Payment Due",
      "phase": 4,
      "t_minus_window": "FPD (day of)",
      "send_t_minus": "FPD",
      "staff_pipeline": ["A9 (monitor)", "Hale (oversight + escalate if missed)"],
      "py_entry": "core/booking/thunderbird_commission_recon.py",
      "mcp_tool": "gmail_send_email",
      "search_window_days": 0,
      "output_type": "within-wing alert if missed",
      "wf17_required": false,
      "conditional": true,
      "notes": "NON-NEGOTIABLE deadline. If payment not confirmed by end of business: escalate to Commander immediately. Booking cancellation risk."
    },
    "4.5": {
      "name": "Payment Confirmation",
      "phase": 4,
      "t_minus_window": "FPD+6 to FPD+7",
      "send_t_minus": "FPD+7",
      "staff_pipeline": ["A9", "Hale", "Commander (full send)"],
      "py_entry": "core/booking/thunderbird_reconciliation.py",
      "mcp_tool": "gmail_send_email",
      "search_window_days": 1,
      "output_type": "intel_report",
      "wf17_required": false,
      "conditional": true,
      "notes": "Verify balance cleared. New balance $0.00. Verify shipboard credits intact. Update dossier and THUNDERBIRD_MASTER_PLAN.md."
    },
    "5.1": {
      "name": "Welcome Home",
      "phase": 5,
      "t_minus_window": "E+6 to E+7",
      "send_t_minus": "E+7",
      "staff_pipeline": ["A6", "Dani", "Naia (high-value)", "WF-17", "Commander"],
      "py_entry": "core/email/thunderbird_dani_email.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 1,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Warm welcome home. Initial experience capture. 'How was the canal transit?' A6 provides a highlight phrase."
    },
    "5.2": {
      "name": "Post-Voyage Survey",
      "phase": 5,
      "t_minus_window": "E+13 to E+14",
      "send_t_minus": "E+14",
      "staff_pipeline": ["A7 Gauge", "Hale", "deploy"],
      "py_entry": "core/client/thunderbird_survey.py",
      "mcp_tool": "gmail_send_email",
      "search_window_days": 2,
      "output_type": "client_email (survey link)",
      "wf17_required": false,
      "notes": "A7 Gauge designs survey. Capture: what worked, what didn't, supplier performance, ship service quality, excursion hits/misses, suite satisfaction. Results fed back to Commander."
    },
    "5.3": {
      "name": "Thank You + Referral",
      "phase": 5,
      "t_minus_window": "E+20 to E+21",
      "send_t_minus": "E+21",
      "staff_pipeline": ["A6", "Dani", "Naia", "WF-17", "Commander"],
      "py_entry": "core/email/thunderbird_dani_email.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 2,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "Personalized, handwritten tone. Referral ask embedded naturally — not transactional. A6 leads copy. Naia voice review required."
    },
    "5.4": {
      "name": "Next Voyage Plant",
      "phase": 5,
      "t_minus_window": "E+29 to E+30",
      "send_t_minus": "E+30",
      "staff_pipeline": ["A5 Viper", "A2", "Dani", "WF-17", "Commander"],
      "py_entry": "core/email/thunderbird_dani_engine.py",
      "mcp_tool": "gmail_create_draft",
      "search_window_days": 2,
      "output_type": "client_email",
      "wf17_required": true,
      "notes": "A5 develops next-voyage strategy based on stated interests and preferences learned throughout this lifecycle. A2 runs preliminary destination research. Lifecycle formally closes after this send."
    }
  },

  "staff_pipeline_canonical": {
    "description": "Standard D2M production pipeline. Each staff member adds one function. Pipeline runs sequentially per TP.",
    "stages": [
      {
        "order": 1,
        "actor": "A2 Dembe",
        "role": "Research & Market Intelligence",
        "output": "Raw research findings: fares, destinations, hotels, excursions, dining",
        "py_files": ["core/intel/thunderbird_ship_intel.py", "core/intel/thunderbird_price_monitor.py", "core/mcp/travel_mcp_server.py"]
      },
      {
        "order": 2,
        "actor": "A6 Luna",
        "role": "Creative Director",
        "output": "Narrative copy, imagery selection, emotional travel writing",
        "py_files": [],
        "note": "Parallel with A9 — both receive A2 research independently"
      },
      {
        "order": 2,
        "actor": "A9 Harlan",
        "role": "Finance & Process Improvement",
        "output": "Cost analysis, commission calculations, payment tracking",
        "py_files": ["core/booking/thunderbird_commission_recon.py", "core/booking/thunderbird_reconciliation.py"],
        "note": "Parallel with A6"
      },
      {
        "order": 3,
        "actor": "A5 Viper",
        "role": "Strategy & Business Growth",
        "output": "Booking strategy, fare timing recommendation, next-voyage planning",
        "py_files": [],
        "note": "Receives A9 output. Engaged on TP 1.2 and TP 5.4 primarily."
      },
      {
        "order": 4,
        "actor": "Hale",
        "role": "COS — Orchestration & QC",
        "output": "Integrated product ready for Dani. Weekly reports. WF-17 gate pass/fail.",
        "py_files": ["core/email/thunderbird_presend_evaluator.py", "core/client/thunderbird_validation.py"]
      },
      {
        "order": 5,
        "actor": "Naia (EXEC)",
        "role": "Voice & Visual Review (high-touch TPs only)",
        "output": "Voice-approved copy for high-touch touchpoints",
        "py_files": [],
        "note": "Engages on TPs 3.1, 3.2, 3.3, 5.1, 5.3"
      },
      {
        "order": 6,
        "actor": "Dani (A3)",
        "role": "Concierge — Aggregate / Artist / Advocate",
        "output": "Final client email in D2M voice",
        "py_files": ["core/email/thunderbird_dani_engine.py", "core/email/thunderbird_dani_email.py"]
      },
      {
        "order": 7,
        "actor": "WF-17 Gate",
        "role": "Quality Gate — 8 mandatory checks",
        "output": "Pass or fail",
        "py_files": ["core/email/thunderbird_presend_evaluator.py"]
      },
      {
        "order": 8,
        "actor": "Commander",
        "role": "Send Approval",
        "output": "Approved send or edit/reject",
        "py_files": []
      }
    ]
  },

  "wf17_gate": {
    "description": "Mandatory pre-send quality gate for all client-facing emails.",
    "owner": "Hale",
    "py_entry": "core/email/thunderbird_presend_evaluator.py",
    "bypass": "NEVER — bypass attempt triggers 24-hour hold",
    "checks": [
      "logo_renders",
      "from_address_correct",
      "sig_block_correct",
      "paper_color_f7f3ea",
      "ink_color_0000ff",
      "font_georgia_serif",
      "signoff_thanks_or_thank_you",
      "content_clean_no_ai_disclaimer_no_happy_to_help"
    ],
    "exempt": [
      "weekly_intel_reports_to_johnloucks3",
      "monthly_validation_reports_to_johnloucks3",
      "payment_tracking_reports_to_johnloucks3"
    ]
  },

  "email_routing": {
    "client_facing": {
      "from": "concierge@d2mluxury.quest",
      "send_account": "d2mconcierge@gmail.com",
      "requires_wf17": true,
      "requires_commander_approval": true,
      "draft_location": "d2mconcierge Gmail drafts"
    },
    "within_wing_reports": {
      "from": "d2mconcierge@gmail.com",
      "to": "johnloucks3@gmail.com",
      "requires_wf17": false,
      "requires_commander_approval": false,
      "delivery": "full_send_no_draft_step"
    }
  },

  "key_external_anchors": {
    "regent_excursion_portal": "E-210 (approximately 7 months out)",
    "regent_culinary_classes": "E-120 (approximately 4 months out)",
    "regent_dining_portal": "E-90 (approximately 3 months out)",
    "regent_online_checkin": "E-21",
    "viking_excursion_portal": "E-120 (approximately 4 months out)",
    "insurance_preexisting_window": "14-21 days from deposit date",
    "airfare_sweet_spot": "E-180 to E-120",
    "hotel_booking_window": "E-150 to E-90",
    "passport_validity_minimum": "6 months post-disembarkation"
  },

  "core_module_registry_relevant": {
    "dossier_crud": "core/booking/thunderbird_dossier.py",
    "guest_forms": "core/booking/thunderbird_guest_forms.py",
    "commission_recon": "core/booking/thunderbird_commission_recon.py",
    "reconciliation": "core/booking/thunderbird_reconciliation.py",
    "validation": "core/client/thunderbird_validation.py",
    "quote_render": "core/client/thunderbird_quote_render.py",
    "survey": "core/client/thunderbird_survey.py",
    "followup_reminders": "core/client/thunderbird_followup_reminders.py",
    "dani_engine": "core/email/thunderbird_dani_engine.py",
    "dani_email": "core/email/thunderbird_dani_email.py",
    "presend_evaluator": "core/email/thunderbird_presend_evaluator.py",
    "gmail": "core/email/thunderbird_gmail.py",
    "ship_intel": "core/intel/thunderbird_ship_intel.py",
    "price_monitor": "core/intel/thunderbird_price_monitor.py",
    "mcp_server": "core/mcp/travel_mcp_server.py"
  },

  "booking_specific_lifecycle_docs": {
    "kuklinski_viking_panama": "D2M/lifecycle/Kuklinski_Viking_Panama_Lifecycle.md",
    "loucks_grandeur_panama_pacific": "D2M/lifecycle/Loucks_Grandeur_PanamaPacific_Lifecycle.md",
    "mcleod_grandeur_lesser_antilles": "D2M/lifecycle/McLeod_Grandeur_LesserAntilles_Lifecycle.md"
  },

  "standing_orders": {
    "send_gate": "SO 21 MAR 2026 — No send outside wing without Commander approval. Exception: johnloucks3@gmail.com",
    "account_separation": "SO 24 MAR 2026 — d2mconcierge = sole ops Gmail. ZERO drafts in johnloucks3.",
    "intel_full_send": "SO 27 MAR 2026 — All intel/briefs to johnloucks3 as full sends (no draft step).",
    "dani_scope": "SO 25 MAR 2026 — Dani is client-facing ONLY. No supplier contact, no briefings, no Commander replies."
  }
}
```

---

*THUNDERBIRD LIFECYCLE — GRAND SUMMARY | Dreams2Memories Travel, LLC*
*Owner: Col Victoria Hale, COS | Thunderbird Wing | v1.0 | 2026-04-19*
*This is a living document. Update when lifecycle framework changes. Booking-specific docs live in `D2M/lifecycle/`.*
