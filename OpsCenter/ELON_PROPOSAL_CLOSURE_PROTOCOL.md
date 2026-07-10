# ELON Proposal Closure Protocol
**Effective 2026-07-06 22:22 MT**

## The Problem (Solved Today)
83 ELON proposals accumulated May–July 2026. Most marked APPLY_AUTONOMOUSLY, zero executed until 2026-07-06 parallel batch (20 agents, 90% completion rate in 2.5 hours). Root cause: write-only queue, no feedback loop, no closure tracking.

## The Solution: Three-Step Closure Loop

### STEP 1: PROPOSE (ELON)
- Write proposal to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-[DATE]-[SYSTEM].md`
- Mark decision: `APPLY_AUTONOMOUSLY`, `QUEUE_FOR_COMMANDER`, or `HOLD`
- **New requirement:** include `CLOSURE_TARGET_DATE: YYYY-MM-DD` (max 7 days out)

### STEP 2: EXECUTE (Parallel agents or manual)
- Agent spawned per proposal OR manual execution
- Write execution report to `/home/john/Thunderbird/OpsCenter/elon_proposals/[SYSTEM]_EXECUTION.md`
- Report must include: what was done, test results, commits, any blockers

### STEP 3: CLOSE (Hale, weekly review)
- Every Sunday 18:00 MT, Hale reviews open proposals vs closure targets
- For each completed proposal: write closure doc to same directory
- Closure doc format:
  ```
  # CLOSURE: [SYSTEM] (date)
  Status: COMPLETE / BLOCKED / PARKED
  Target date: [was] | Actual close: [is] | Delta: [days]
  Blockers (if any): [list]
  Next action: [none/follow-up proposal/escalation]
  ```
- Archive closed proposals to `/home/john/Thunderbird/OpsCenter/elon_proposals/CLOSED/`

## Metrics (Tracked in hale_state.json)

```json
{
  "elon_proposals": {
    "active": 0,
    "closed_this_week": 0,
    "overdue_targets": 0,
    "avg_closure_days": 0,
    "closure_rate_pct": 0
  }
}
```

**Target:** 80%+ proposals closed within target window.

## Weekly Review Cadence
- **Sunday 18:00 MT:** Hale reviews all open proposals
- **Output:** closure docs + archival + metrics update
- **Report:** one-line summary to hale_decisions.md + Telegram to Commander

---

*Implemented 2026-07-06 as root-cause fix for backlog languish. First review: 2026-07-14 18:00 MT.*
