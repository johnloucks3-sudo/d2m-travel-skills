# SO-TimerGovernance_v1 — Standing Order on Timer Lifecycle & Cost Envelopes

**Authority:** Victory Hale, COS/COO | **Effective Date:** 2026-07-26  
**Scope:** All Thunderbird Wing systemd timers, cron schedules, and subagent recurring loops.

## Core Rules

1. **Token Envelope Limit:**
   - Any recurring timer calling an LLM API must define a max token envelope ($\le 15,000$ tokens/run).
   - Frequency ceiling: Minimum interval between LLM-backed runs is 30 minutes, unless explicitly approved by Commander.

2. **Mandatory Execution Criteria:**
   - Every systemd `.service` unit backing a `.timer` MUST specify exact log destinations using `StandardOutput=append:/path/to/log` and `StandardError=append:/path/to/log`.
   - Silent/unlogged background timers are strictly forbidden.

3. **Orphan & Fail-Safe Cleanup:**
   - Timers with $\ge 3$ consecutive execution failures must auto-disable or trigger an alert to Hale.
   - Any script referenced in `ExecStart` that is deleted or renamed must immediately trigger unit removal during weekly audit.

---
*Approved by Hale-AG under Weapons Free Authority.*
