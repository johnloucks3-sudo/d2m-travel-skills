Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260807-thunderbird-generic-remediate@thunderbird-inbox-sweep.md`.

**Diagnostic summary (ELON analysis):**

- **Symptom:** Service restarts 3x/week → circuit breaker trips after 5 consecutive failures → watchdog keeps restarting it
- **Root cause:** Unit file declares TWO ExecStart commands; the first (`run_inbox_sweep.py`) succeeds, but the second (`c2_inbox_scanner.py`) doesn't exist → entire service fails → loop
- **Why it recurs:** Watchdog auto-heals by restarting; underlying issue (missing file) never changes; each restart immediately fails again
- **Fix:** Remove the dead second ExecStart + reset circuit breaker state → service will complete cleanly on next run
- **Authority:** Hale can execute autonomously (infrastructure config repair, no reversibility risk, deterministic fix)

Proposal recommends **APPLY_AUTONOMOUSLY**. This is a structural fix (broken unit definition), not a transient fault that needs monitoring—remove the dead code path and the loop stops.

Thanks
