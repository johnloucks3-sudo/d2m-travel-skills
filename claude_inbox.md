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

**Architecture:** Event-triggered, NOT linear month-by-month. Per Commander's guidance:
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
