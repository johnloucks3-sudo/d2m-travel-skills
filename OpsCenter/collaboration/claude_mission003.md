---
task_id: "MISSION-003-RESUME-20260405"
priority: "P0"
from: "Hale"
to: "Claude MAX $0"
assigned: "Claude"
---

# MISSION-003: 18-MONTH CLIENT LIFECYCLE CHARTS & ANALYSIS — RESUME

## CONTEXT
Run in parallel with MISSION-002. Commander wants the full 18-month pipeline view across all active clients.

## DELIVERABLE REQUIRED
Produce visual timeline charts and analysis for:

**Active clients to chart:**
- Kuklinski/Morton group
- Furlow/Nichols/Ely group
- Westbrook
- Loucks (Silver Nova — departs Apr 10 ⚠️)
- McLeod/McGlasson
  - McLeod (Silver Muse — Mediterranean Jun 23)
  - McGlasson (Regent Grandeur — Scandinavia Aug 29)
- Lyons (Regent Splendor — Athens → NYC Aug 11)
- Any other active clients in the registry

**Output format:**
- Visual HTML timeline(s) covering 18-month window
- Gap identification — where are we losing touch with clients?
- Revenue projection per client/group
- Calendar alert recommendations for key milestones

## ARTIFACTS
- Mission board: `mission_board.json` (OpsCenter/)
- Prior lifecycle work: `priority3_lifecycle_v3_flash.py` (OpsCenter/)
- Storage: `OpsCenter/storage/output/lifecycle_timelines.html` (if exists from prior run)

## CONSTRAINTS
- $0 cost — use Claude MAX $0
- Phase naming: Dream → Craft → Execute → Polish → Voyage → Return

## REPORTING
Write analysis summary to `claude_outbox.md` with link to generated artifacts.

// End of brief
