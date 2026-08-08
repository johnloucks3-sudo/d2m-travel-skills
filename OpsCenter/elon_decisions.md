
## 2026-08-07 03:26 — MCP Service Recurrence (29x/7d)

**Status:** PROPOSAL_READY  
**Proposal:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260807-thunderbird-mcp.md`  
**Decision Inbox:** Awaiting Hale (autonomous authority on monitoring + cleanup; Commander gate on refactor)

**Summary:** Recurring MCP server restarts point to resource accumulation (FD exhaustion, connection leaks, or subprocess starvation). Proposed 3-step fix: (1) add resource monitoring daemon, (2) implement cleanup handlers, (3) refactor tool registration to lazy-load (Commander gate). Steps 1–2 autonomous; Step 3 escalates.

**Hale routing:** Execute Steps 1–2 autonomously. Escalate Step 3 + baseline metrics to Commander within 48h if restarts persist.

