# CLIENT LIFECYCLE REVISION - SESSION INIT

## 🚨 IMMEDIATE ACTION REQUIRED

You are resuming the client lifecycle chart revision work. Commander has rejected the current lifecycle HTMLs as insufficient. Read this first, then proceed.

## 1. READ THESE CRITICAL FILES (in order):

**A. Commander's Feedback (MUST READ FIRST):**
- `OpsCenter/priority3_lifecycle_v3_flash.py` - Lines 14-21 contain Commander's breakthrough feedback rejecting rigid timelines

**B. Current Lifecycle State:**
- `business/client_lifecycle/Phase_Standardization.md` - Current 6-phase model
- `business/client_lifecycle/Kuklinski_Morton_Lifecycle.html` - Example HTML needing revision
- `trip_lifecycle.html` - Main visualization needing update

**C. Anchor Date Engine:**
- `core/scheduling/thunderbird_anchor_dates.py` - Lines 42-69 show anchor date template

**D. Mission Status:**
- `OpsCenter/mission_board.json` - MISSION-002 and MISSION-003 show "incomplete deliverables" per Commander

## 2. COMMANDER'S CORE REQUIREMENTS:

```
"ALWAYS get staff input first.
The schedule needs to be extremely flexible but also firm.
1) It has several unpredictable but once committed factually known dates: initial contact, deposit date.
2) Then once booked: embarkation date, disembarkation date, final payment, excursions, dining.
3) From that point on, they are at client's discretion: Flights, hotels, transfers, independent bookings.
```

## 3. REVISION ARCHITECTURE:

**Anchor Node Model (NOT rigid timeline):**
- **Node 1:** Unpredictable Triggers (Initial Contact, Deposit Date)
- **Node 2:** Hard Anchors (Embarkation, Disembarkation, Final Payment Date, Excursion/Dining Windows)
- **Node 3:** Fluid Variables (Flights, pre/post hotels, transfers - at client discretion)

**Staff Input Workflow (CRITICAL):**
- A2 (Dembe) → Research & Market Intelligence
- A6 (Luna) → Creative Director & Brand Dreamer  
- A9 (Vic) → Finance & Process Improvement
- **ALL feed intelligence to A3 (Dani)** BEFORE she acts

## 4. IMMEDIATE DELIVERABLES:

1. **Revise Phase_Standardization.md** with event-driven architecture
2. **Update Kuklinski_Morton_Lifecycle.html** with anchor date visualization
3. **Update Furlow_Nichols_Ely_Lifecycle.html** with anchor date visualization  
4. **Create staff input diagram** showing A2/A6/A9 → A3 workflow
5. **Update mission_board.json** to reflect accurate MISSION-002/003 status

## 5. VERIFICATION CHECKLIST:

✓ Does it show Anchor Nodes instead of rigid months?  
✓ Does it demonstrate "ALWAYS get staff input first"?
✓ Are client-discretion items clearly marked as flexible?
✓ Are hard anchors (FPD, embark, dining windows) clearly firm?
✓ Does it integrate with anchor date engine T-minus calculations?

## 6. STARTING POINT EXAMPLES:

From `furlow_context.json` (cache/client_context/):
- Booking: 3071222, Embark: 2026-08-29, FPD: 2026-04-01, Disembark: 2026-09-08
- Dining opens: May 31, 2026, Excursions booked: Jan 31, 2026
- Payment: $15,486 COMPLETE (Apr 1, 2026)

Use these actual client anchors for the revised visualization.

---

**MEMORY CONTEXT:** This is Thunderbird OS - Python AI travel ops for Dreams2Memories Travel, LLC. Dani (A3) is ONLY client-facing voice. Email gate LOCKED - no sends without Commander approval. Goose decommissioned - use OpenCode.

**MODEL:** You are OpenCode via OpenRouter (DeepSeek V3.1). Act as ops engine.

**KEY RULE:** ALWAYS get staff input first. This is the Commander's central critique of current lifecycle charts.

*Init created: 2026-04-07 | For next OpenCode session*