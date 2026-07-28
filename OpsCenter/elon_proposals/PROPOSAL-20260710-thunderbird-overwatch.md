Done. I've diagnosed a **watchdog timeout pattern** in the `thunderbird-overwatch` service and produced a structured ELON proposal.

## Summary

**Root Cause:** The daemon's watchdog ping happens only once per loop iteration, but the `process_one()` call inside can block indefinitely. When it hangs for > 10 minutes (the watchdog limit), systemd kills it. Auto-heal restarts it, but the same blocking operation recurs—causing a 3-in-7-days crash loop.

**Proposed Fix:** Add watchdog-aware sleep (pings every 30 seconds during sleeps) and wrap `process_one()` with a 5-minute timeout. This keeps the watchdog alive during long operations and gracefully skips tasks that take too long.

**Decision:** `APPLY_AUTONOMOUSLY` — this is infrastructure self-healing, not a feature or policy change. Hale can patch `task_processor.py` directly (30 lines of defensive code).

Proposal written to: `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260710-thunderbird-overwatch.md`

Thanks
