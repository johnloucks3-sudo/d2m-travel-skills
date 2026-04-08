# ⛔ TOMBSTONE — 2026-04-07
# This file is DEPRECATED. Do not write here.
# See AGENTS.md for canonical paths:
#   claude_inbox  → /home/john/Thunderbird/claude_inbox.md
#   claude_outbox → /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
#   opencode_inbox→ /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md
# ─────────────────────────────────────────────
# ARCHIVED CONTENT BELOW (read-only)
---
task_id: "LIFECYCLE-RESEARCH-COMPREHENSIVE-20260407"
priority: "P0"
from: "Hale"
to: "Claude MAX $0"
assigned: "Claude"
---

# COMPREHENSIVE LIFECYCLE & RESEARCH FRAMEWORK DEPLOYMENT

**Commander directive:** "We also need: fare and flight research (there is a Kuklinski example in the files), destination, port, tour location weather forecast, port, city guide development process, Trip Validation Monthly, Dining recommendations process, lodging recommendations process ask me questions if needed. also the 4 or 5 forms in google drive need to be added, and the logic for them established--WHEN do we send forms"

## MISSION STATUS
MISSION-002/003 already in progress (lifecycle revision). Added 5 new missions (MISSION-010 to MISSION-014) for comprehensive research framework.

## DELIVERABLES REQUIRED

### 1. LIFECYCLE ARCHITECTURE REVISION (MISSION-002)
- **Event-driven node model** (NOT rigid timeline)
- **Staff input workflow:** A2 → A6 → A9 → A3 visualization
- **Anchor date integration:** Booking, Embark, FPD, Disembark triggers
- **Files:** Phase_Standardization.md, 3 HTML lifecycle charts

### 2. GOOGLE FORMS LOGIC (MISSION-010)
- **Forms inventory:** Guest Profile, Dining, Excursion, Travel Style, Special Requests
- **Send timing protocol:** Based on anchor dates
  - Booking +24h: Guest Profile Form
  - T-90 days: Dining Preferences + Travel Style  
  - T-60 days: Excursion Interest
  - T-30 days: Special Requests
- **Integration:** Google Sheets (EARA_D2M_Command_Center), dossier auto-updates

### 3. FARE & FLIGHT RESEARCH (MISSION-011)
- **Kuklinski case study:** Panama Canal example (Viking Mars, Dec 17-27, 2026)
- **Fare watch automation:** Price tracking, best deal alerts
- **Flight comparison:** Option matrix, routing optimization

### 4. DESTINATION INTELLIGENCE (MISSION-012)
- **Port guides:** Logistics, facilities, local services
- **City profiles:** Attractions, culture, safety
- **Weather forecasting:** Seasonal patterns, climate data
- **Tour location intelligence:** Activity research

### 5. DINING & LODGING (MISSION-013)
- **Restaurant research:** Cuisine profiling, reviews, reservations
- **Hotel evaluation:** Property comparison, amenity analysis  
- **Client matching:** Preference system integration
- **Quality assurance:** Checklist development

### 6. MONTHLY VALIDATION (MISSION-014)
- **Trip audit system:** Booking verification, payment status
- **Document completeness:** Checklist automation
- **Issue flagging:** Protocol for problems
- **Reporting:** Validation template creation

## ARTIFACTS & INTEGRATION

**Key Files:**
- `comms/create_guest_profile_form.py` - Existing forms infrastructure
- `storage/cache/client_context/kuklinski_context.json` - Research example
- `OpsCenter/client_lifecycle_revision_init.md` - Commander's requirements
- `business/client_lifecycle/Revised_Lifecycle_Architecture.md` - New design
- `comms/Google_Forms_Logic_Protocol.md` - Forms timing established

**Integration Points:**
- Anchor date engine (`thunderbird_anchor_dates.py`)
- Google Sheets response tracking
- Dossier auto-update system
- Staff workflow coordination

## CONSTRAINTS
- $0 cost - use Claude MAX $0
- Maintain existing form infrastructure
- Integrate with current lifecycle revision
- Follow Commander's specific timing requirements

## REPORTING
When complete: write summary to `claude_outbox.md` and update all mission statuses in `mission_board.json`.

// End of comprehensive brief
