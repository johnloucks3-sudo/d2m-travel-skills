**Proposal written to:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260710-thunderbird-generic-remediate@nexus.md`

**Summary:**

**Root cause:** Regent cookies expire every 365 days with zero auto-refresh (Akamai wall blocks API re-auth — requires manual browser). When nexus starts and detects expired creds, it crashes. Systemd restarts it in a loop because the underlying issue (manual re-auth needed) can't be auto-fixed. Current: 3 restarts in 7 days, noise in logs, no recovery path without Commander.

**Fix (dual approach):**
1. **Config change** — Add exponential backoff + max 3 restarts/hour to the remediate service. Stops the churn; service fails clean instead of looping forever.
2. **Standing order** — Monthly heartbeat check (1st of month). If Regent creds >90d old or expired, alert Commander to re-auth via Firefox. 5-minute manual touch every 365 days.
3. **Long-term (QUEUE_FOR_COMMANDER)** — Propose Playwright-based credential keepalive daemon to eliminate manual touch entirely. ~16h effort, full payoff.

**Hale can execute Parts 1+2 autonomously** (low-risk, reversible, no gates crossed). Part 3 is a future mission pending Commander prioritization.

The recommendation aligns with the current credential issue blocking MISSION-820 (McLeod FPD prep waiting on Regent portal refresh). Once this config is in place, the next restart loop is much quieter, and the monthly audit ensures Regent creds stay fresh.

Thanks
