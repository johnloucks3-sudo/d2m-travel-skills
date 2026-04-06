---
task_id: "MISSION-002-RESUME-20260405"
priority: "P0"
from: "Hale"
to: "Claude MAX $0"
assigned: "Claude"
---

# MISSION-002: CLIENT LIFECYCLE CHART — RESUME

**Commander directive:** "You decide/hale" followed by "Keep me informed. Ask questions if needed."

## CONTEXT
MISSION-001 (NEXUS build) is complete. MISSION-002 stalled after 3 engine timeouts. Commander wants it done and to be kept informed.

## DELIVERABLE REQUIRED
Rebuild all lifecycle HTML charts with **TODAY** as the reference date. The audit on 20260405_4 found 8 issues:

### 4 HIGH
1. **Regenerate ALL lifecycle HTMLs** with current TODAY date
2. **Fix Group 2 Morton** — missing guest form
3. **Flag Loucks Silver Nova** — departs Apr 10 (urgent)
4. **Create Group 5 Lyon** companions

### 3 MEDIUM
5. Promote spec prompt to formal SOP
6. Standardize phase naming: Dream → Craft → Execute → Polish → Voyage → Return
7. Set up calendar alerts for key dates

### 2 LOW
8. Additional hygiene items from audit

## ARTIFACTS
- Source: `mission_board.json` (OpsCenter/)
- NEXUS: `nexus.py` (OpsCenter/) — state machine is ready
- Router: `keyword_router.py` (OpsCenter/) — Qwen/Claude routing
- Prior lifecycle templates: `priority3_lifecycle_v3_flash.py` (OpsCenter/)

## CONSTRAINTS
- $0 cost — use Claude MAX $0
- Phase naming convention is non-negotiable
- Loucks Silver Nova (Apr 10 departs soon — priority)

## REPORTING
When done: write summary to `claude_outbox.md` and update `mission_board.json` mission status.

// End of brief
