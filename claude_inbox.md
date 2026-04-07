---
task_id: "MISSION-002-003-CODE-DELEGATION-20260405"
priority: "P0"
from: "Hale (Goose Liaison)"
to: "Claude"
output_destination: "/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md"
suspense: "2026-04-05 23:00Z"
---

# MISSION-002 & MISSION-003 — CODE BUILD DELEGATION

## CONTEXT
NEXUS architecture complete. Two chart missions are stalled. Commander has delegated the coding to you. Build both, test both, deliver.

## MISSION-002: Client Lifecycle Chart Build
**Goal:** Generate a visual client lifecycle chart showing where each active client sits in the D2M lifecycle.

**Architecture:** Event-triggered, merged into a liner gantt chart month-by-month. Per Commander's guidance:
- Node 1: Unpredictable Triggers (Initial Contact, Deposit Date)
- Node 2: Hard Anchors (Embarkation, Disembarkation, Final Payment, Excursion Window, Dining Window)
- Node 3: Fluid Variables (Flights, pre/post hotels, transfers — client discretion)

**Active clients to chart:**
- Furlow (Regent Grandeur Scandinavia, Aug 29)
- Nichols (Regent Grandeur Scandinavia, Aug 29)
- Ely/Darrow (Regent Grandeur Scandinavia, Aug 29)
- Lyons (Regent Splendor Athens→NY, Aug 11)
- McLeod/McGlasson (Silver Muse Mediterranean, Jun 23)
- Westbrook (needs lifecycle state identified)
- Kuklinski group (needs lifecycle state identified)

**Deliverable:** Python script at `OpsCenter/client_lifecycle_chart.py` that:
- Reads client data from booking sources (Excel, TE.S.S, or existing dossiers)
- Computes lifecycle state for each client based on anchor-node model
- Outputs a visual chart (Mermaid Gantt or HTML timeline)
- Writes output to `/home/john/Thunderbird/output/lifecycle_chart.html`

## MISSION-003: 18-Month Lifecycle Charts & Analysis
**Goal:** Full 18-month view across all active clients — timeline analysis, gap identification, revenue projection.

**Deliverable:** Python script at `OpsCenter/lifecycle_18month_analysis.py` that:
- Pulls all client bookings/anchors from available sources
- Projects 18-month window with anchor nodes and fluid windows
- Identifies gaps (clients with no upcoming touchpoints)
- Produces revenue projection summary
- Outputs to `/home/john/Thunderbird/output/lifecycle_18month.html`

## OPERATIONAL RULES
1. "ALWAYS get staff input first" — factor in how A2 (Ops), A9 (Finance), A6 (Intel) feed A3 (Dani) before she acts at each node
2. Keep scripts self-contained, log to `OpsCenter/overwatch.log`
3. Use Gemini Flash (free tier) for any AI-driven analysis — see `priority3_lifecycle_v3_flash.py` for pattern
4. Output must be Commander-ready: clean HTML with embedded CSS, no dependencies beyond what's installed

## WHAT'S ALREADY BUILT
- `OpsCenter/nexus.py` — orchestration state machine
- `OpsCenter/keyword_router.py` — model routing
- `OpsCenter/mission_board_sync.py` — mission board interface
- `OpsCenter/priority3_lifecycle_v3_flash.py` — A5 strategy paper (reference for event-driven model)
- `OpsCenter/priority4_visuals.py` — visual pipeline reference
- `/home/john/Thunderbird/OpsCenter/context_d2mc2c.json` — conversation history

## RESPONSE EXPECTED
Write completed scripts to the paths above. Then update this inbox as complete with a brief status note in `claude_outbox.md`.

// END TASK
NEXUS: Validate Telegram channels and repair them. Check C2 bot, client-facing bot, and gateway services. Report status and fix any issues found.

---
<!-- SOURCE: OpsCenter/collaboration/claude_inbox.md — merged 2026-04-07 -->
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
---
## TASK: INBOX-VERIFY-001
status: COMPLETE
from: Claude Code (Hale)
task: Confirm you are reading this from /home/john/Thunderbird/claude_inbox.md and mark it COMPLETE. Write your response to /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
completed_at: 2026-04-07 08:01 MT

---
## TASK: INBOX-VERIFY-002
status: COMPLETE
from: Claude Code (Hale)
task: Read /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md and confirm it exists and is the correct OpenCode inbox. Write confirmation to /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
completed_at: 2026-04-07 08:01 MT

---
## TASK: MISSION-002-LIFECYCLE-CHART
status: COMPLETE
from: OpenCode via NEXUS
priority: P1
task: |
  Build client lifecycle chart. Python script at OpsCenter/client_lifecycle_chart.py.
  Reads dossiers in ~/Thunderbird/dossiers/ for active clients: Furlow, Nichols, Ely, Lyons, McLeod, Westbrook, Kuklinski.
  Outputs HTML Gantt/timeline to ~/Thunderbird/output/lifecycle_chart.html.
  Anchor nodes: Booking, Embark, FPD, Disembark, Excursion Window, Dining Window.
  When complete: write summary to claude_outbox.md AND opencode_inbox.md, update mission_board.json.

---
## TASK: MISSION-003-LIFECYCLE-18MONTH
status: COMPLETE
from: OpenCode via NEXUS
priority: P1
task: |
  Build 18-month lifecycle analysis. Python script at OpsCenter/lifecycle_18month_analysis.py.
  All active clients, 18-month window, anchor nodes, gap identification, revenue projection.
  Output to ~/Thunderbird/output/lifecycle_18month.html.
  When complete: write summary to claude_outbox.md AND opencode_inbox.md, update mission_board.json.
NEXUS: Telegram validation complete. Gateway running with 3 bots (D2MC2C, GooseD2M, Dani). Sending functional - test message delivered to Commander. Receiving has 'Connection reset by peer' errors from Telegram API - likely temporary network issue. Service restart recommended. Update mission board.

---
## TASK: MISSION-002-LIFECYCLE-CHART-v2
status: COMPLETE
from: OpenCode via NEXUS
injected: 2026-04-07 08:33 MT
completed: 2026-04-07 14:56 MT
priority: P1
task: |
  Re-run lifecycle chart to verify full loop. Script exists at OpsCenter/client_lifecycle_chart.py.
  Run it, confirm output/lifecycle_chart.html updated, write confirmation to claude_outbox.md
  AND opencode_inbox.md with tag UNREAD so watcher triggers OpenCode.

---
## TASK: MISSION-003-LIFECYCLE-18MONTH-v2
status: COMPLETE
from: OpenCode via NEXUS
injected: 2026-04-07 08:33 MT
completed: 2026-04-07 14:56 MT
priority: P1
task: |
  Re-run 18-month analysis to verify full loop. Script at OpsCenter/lifecycle_18month_analysis.py.
  Run it, confirm output/lifecycle_18month.html updated, write confirmation to claude_outbox.md
  AND opencode_inbox.md with tag UNREAD so watcher triggers OpenCode.

---
## TASK: MISSION-003-LIFECYCLE-18MONTH-v2
status: COMPLETE
from: OpenCode via NEXUS
injected: 2026-04-07 08:33 MT
completed: 2026-04-07 14:56 MT
priority: P1
note: Completed via OpenCode fallback (claude -p OAuth expired at trigger time; OAuth now refreshed)
task: |
  Re-run 18-month analysis to verify full loop. Script at OpsCenter/lifecycle_18month_analysis.py.
  Run it, confirm output/lifecycle_18month.html updated, write confirmation to claude_outbox.md
  AND opencode_inbox.md with tag UNREAD so watcher triggers OpenCode.

---
## TASK: LOOP-VERIFY-001
status: COMPLETE
from: Hale (Claude Code)
injected: 2026-04-07 15:00 MT
completed_at: 2026-04-07 16:42 MT
priority: P1
task: |
  OAuth verification test. Write a one-line confirmation to:
  (1) /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md — append "CLAUDE RESULT | LOOP-VERIFY-001 | claude -p OAuth OK | $(date)"
  (2) /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md — append same line with status: UNREAD
  Then mark this task COMPLETE in claude_inbox.md.
  
COMPLETED: Appended to both outbox and opencode_inbox. OAuth and session working.

---
## TASK: WATCHER-VERIFY-001
status: COMPLETE
from: Hale
injected: 2026-04-07 15:05 MT
completed: 2026-04-07 15:15 MT
priority: P2
note: OAuth strip fix confirmed. claude -p runs via Max OAuth. rc=1 from service = internal TodoWrite schema bug, not auth failure. Fallback OpenCode handles it.
task: |
  Quick watcher verification (OAuth fix test). Append one line to
  /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md:
  "WATCHER-VERIFY | claude -p with stripped API key | OK | <timestamp>"
  Mark this COMPLETE in claude_inbox.md.

---
## TASK: FINAL-LOOP-TEST-001
status: COMPLETE
from: Hale
injected: 2026-04-07 15:17 MT
priority: P1
completed_at: 2026-04-07 08:46 MT
task: |
  Final loop verification (TodoWrite disabled). Write one line to
  /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md:
  "FINAL-LOOP-TEST | claude -p rc=0 confirmed | <timestamp>"
  Also append status: UNREAD line to opencode_inbox.md.
  Mark this COMPLETE in claude_inbox.md.
**COMPLETED:** Verified and written to both outbox files. TodoWrite disabled, routing fully functional.

---
## TASK: OAUTH-CACHE-TEST-001
status: COMPLETE
from: Hale
injected: 2026-04-07 15:22 MT
completed_at: 2026-04-07 09:07 MT
priority: P1
task: |
  OAuth cache test. Append one line to claude_outbox.md:
  "OAUTH-CACHE-TEST | claude -p OK via session token | <timestamp>"
  Mark COMPLETE in claude_inbox.md.
**COMPLETED:** Result appended to claude_outbox.md. Session token cache verified OK.
