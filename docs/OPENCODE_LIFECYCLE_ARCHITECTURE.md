# OPENCODE LIFECYCLE ARCHITECTURE — THUNDERBIRD OS
## Event-Driven Client Lifecycle System Integration
### Dreams2Memories Travel, LLC | OpenCode Perspective | 2026-04-07

---

## CORE ARCHITECTURAL PERSPECTIVE

### Phase Determination Engine vs. 35-Touchpoint Model

The Thunderbird Lifecycle System has two complementary perspectives:

1. **Phase Determination Engine** (`client_ingester.py`) — **Algorithmic**
   - 6 distinct phases (PHASE_0 to PHASE_5) based on anchor dates
   - Algorithmic assignment using booking, FPD, embark, disembark dates
   - Validates anchor date logic and payment status transitions
   - **Current Phase for Kuklinski: PHASE_2 (Execute)**

2. **35-Touchpoint Production Model** (`CLIENT_LIFECYCLE_ARCHITECTURE.md`) — **Operational**
   - 35 specific client deliverables across 18-month span
   - Staff workflow (A2 → A6 → A9 → A3 → COS → Commander)
   - 2-week draft rule for all client communications
   - 3-zone model (Commitment, Preparation, Execution)

### Key Integration Points

| Lifecycle Engine Output | Production Model Integration |
|-------------------------|------------------------------|
| **Phase Assignment** | Determines which production tasks are active |
| **Anchor Validation** | Ensures all critical dates are logically consistent |
| **Payment Status** | Drives financial workflow (insurance, FPD reminders) |
| **Days to Embark** | Maps to appropriate production phase |

### Staff Workflow — Cross-Validated View

```
[A2 Research] → [A6 Narrative] → [A9 Financial] → [A3 Voice] → [COS Gate] → [Commander Send]
    ↓              ↓               ↓               ↓             ↓              ↓
Data Input  →   Story Craft →   $$ Validation →   Brand Polish → WF-17 Compliance → Final Approval
```

**2-Week Draft Rule:** Every client deliverable requires complete A3 draft 14 days before send date.
**Insurance Exception:** 7-day rule for pre-existing condition waiver windows.

### Anchor Date Validation (Engine Output)

The Lifecycle Engine validates four critical anchors:
- `booking_date` — Clock starts here
- `fpd` — Final Payment Due (standard T-120)
- `embark_date` — T-0, immovable
- `disembark_date` — Voyage end

**Validation Status for Active Clients (7 total):**
- Furlow: ✅ VALID (PHASE_3)
- Nichols: ✅ VALID (PHASE_3)
- Ely: ✅ VALID (PHASE_3)
- Lyons: ✅ VALID (PHASE_2)
- McLeod: ✅ VALID (PHASE_3)
- Westbrook: ✅ VALID (PHASE_4)
- **Kuklinski: ✅ VALID (PHASE_2)**

### Production Counts from 35-Touchpoint Model

| Category | Count | Notes |
|----------|-------|-------|
| **Client Emails** | 24 | All staff-drafted, WF-17 gated |
| **Internal Actions** | 13 | Validation, checks, logs |
| **Staff Drafts Total** | 23 | Excluding internal-only actions |
| **Critical Path Items** | 6 | Dates that cannot slip |

### Fare Watch Specifications — Algorithmic Implementation

**Air Fare Watch:**
- Opens: D+0 (at booking)
- Frequency: Weekly monitoring
- Alert: −10% from baseline OR business class availability
- Delivery: Month 6 (T-12mo) → "first client delivery"
- Close: Air booked & confirmed

**Hotel Fare Watch:**
- Opens: D+0
- Frequency: Weekly first 3mo, bi-weekly thereafter
- Alert: Rate drop >15% on cancelable hold OR category upgrade
- Delivery: Month 6 (T-12mo) → "first client delivery"
 - Close: Hotels booked & confirmed

**Algorithmic Implementation in `client_ingester.py`:**
- Validates fare watch activation based on current phase
- Calculates optimal monitoring window
- Integrates with automated task spawning

### Industry Windows — Line-Specific Overrides

| Activity | Standard Window | Viking Exception |
|----------|----------------|------------------|
| Excursion Booking | T-180 | **OPEN FROM BOOKING ⚠️** |
| Dining Reservations | T-90 | T-90 (standard) |
| Online Check-in | T-120 to T-90 | T-90 (standard) |

**Viking Exception Handling:** Kuklinski Group is 4+ weeks late on excursion research (open since booking on Mar 10). This is flagged as URGENT in phase validation.

### Three-Zone Temporal Model

```
ZONE 1 — COMMITMENT (D+0 → T-6mo)
  • "Everything is ahead"
  • Kuklinski currently here (T-254)
  • Focus: Research, planning, insurance, guest forms

ZONE 2 — PREPARATION (T-6mo → T-30)
  • "Details are hardening"
  • Air/hotel booking decisions
  • Excursion & dining preparations

ZONE 3 — EXECUTION (T-30 → T+30)
  • "We are live"
  • Final logistics, embarkation
  • Voyage support, post-trip follow-up
```

### Critical Path Validation

The Lifecycle Engine validates these critical deadlines:

1. **Insurance Email (D+7)** — Pre-existing waiver expires D+14–21
2. **Air Fare Delivery (T-12mo)** — Business class inventory vanishes
3. **Hotel Booking (T-10mo)** — Luxury pre/post properties fill in peak ports
4. **Excursion Research (Viking: AT BOOKING)** — Book ASAP or miss slots
5. **Dining Reservations (T-104)** — Specialty restaurants fill quickly
6. **Final Payment (FPD)** — Contractual deadline

### Kuklinski-Specific Architecture Analysis

**Current Status (T-254 days):**
- **Phase:** PHASE_2 (Execute) per Lifecycle Engine
- **Payment:** ✅ PAID IN FULL ($21,244 Mar 27)
- **Insurance:** 🔴 CRITICAL — pre-existing waiver window expired
- **Guest Forms:** 🟡 PARTIAL (5/6 complete — Josh Morton missing)
- **Excursions:** 🔴 URGENT — window open since booking (4+ weeks overdue)

**Architecture Integration Gaps Identified:**
1. **Viking Exception Handling** — System didn't auto-flag excursion urgency at booking
2. **Insurance Waiver Tracking** — Missed D+7 window not auto-detected
3. **Partial Completion Tracking** — Guest form completion status not auto-validated

### Recommendations for Architecture Enhancement

1. **Automated Exception Detection**
   - Viking "open from booking" should trigger P0 urgency
   - Insurance window passes → auto-alert
   - Partial form completion → auto-reminder

2. **Phase-Triggered Task Generation**
   - PHASE_2 → auto-schedule excursion research
   - PHASE_3 → auto-initiate validation audits
   - PHASE_4 → auto-activate emergency contact protocol

3. **Cross-System Validation**
   - Lifecycle Engine phase assignments should sync with mission board
   - Anchor dates should populate production schedule templates
   - Payment status should auto-update dossier validation matrix

### Technical Debt Observations

1. **Inconsistency in Phase Definitions**
   - `client_ingester.py`: PHASE_2 for Kuklinski (Execute)
   - Production schedule: Shows Kuklinski in Zone 1 (Commitment)
   - Need alignment on temporal boundaries

2. **Lack of Automated Handoff**
   - Lifecycle Engine outputs not directly feeding production templates
   - Manual synchronization required between systems

3. **Missing Validation Hooks**
   - No automated check for "Viking exception" at booking
   - No auto-spawn of mission tasks based on phase transitions

---

## APPENDIX: PHASE DEFINITIONS CROSS-REFERENCE

| Phase Code | Phase Name | Anchor | Payment Status | Condition | Equivalent Zone |
|------------|------------|--------|----------------|-----------|----------------|
| PHASE_0 | Dream | booking_date | None | today < booking_date | Pre-Booking |
| PHASE_1 | Craft | booking_date | None | booking_date ≤ today < (booking_date + 60d) | ZONE 1 |
| PHASE_2 | Execute | fpd | pending/partial | (booking_date + 60d) ≤ today < fpd | ZONE 1/ZONE 2 |
| PHASE_3 | Polish | embark_date | paid | fpd ≤ today < (embark_date - 7d) | ZONE 2 |
| PHASE_4 | Voyage | embark_date | paid | (embark_date - 7d) ≤ today ≤ disembark_date | ZONE 3 |
| PHASE_5 | Return | disembark_date | paid | today > disembark_date | Post-Zone 3 |

**Note:** Kuklinski shows as PHASE_2 (Execute) despite being paid in full — indicates FPD hasn't technically passed calendar-wise but payment received early. This highlights edge case in algorithm where early payment doesn't transition phase until actual FPD date.

---

Generated by OpenCode Agent | Thunderbird OS Lifecycle Integration Perspective | 2026-04-07
