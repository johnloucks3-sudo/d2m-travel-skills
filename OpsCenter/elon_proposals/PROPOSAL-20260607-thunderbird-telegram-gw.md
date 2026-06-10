**Proposal written to:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260607-thunderbird-telegram-gw.md`

I've analyzed the recurring Telegram gateway crashes and produced a structured ELON proposal. Here's the summary:

**ROOT CAUSE:** The gateway is in a crash-loop caused by an **unhandled exception in the polling cycle** that triggers every 1–15 minutes. The watchdog restarts it successfully, but the underlying condition repeats immediately. We're treating the symptom (auto-restart) instead of fixing the source.

**FIX:** Add defensive exception handling to the polling loop so it logs the actual error instead of crashing. This requires:
1. **Phase 1** (Hale, autonomous): Wrap the polling loop in try-except, capture the error, sleep 5s, retry
2. **Phase 2** (Commander reviews): Collect logs, diagnose the exact failure (token expiry, import error, subprocess failure, timeout)
3. **Phase 3**: Apply the structural fix based on what Phase 2 reveals

**DECISION:** `APPLY_AUTONOMOUSLY` — the defensive change has zero breaking risk and is the prerequisite for diagnosing what's actually failing.

**Verification:** 30-minute uptime baseline test + send test Telegram message + confirm no restarts in logs.

The proposal also includes a new standing order: any service in an auto-heal loop >5x per day gets exception handling within 4 hours, or escalation. Symptom-only restarts aren't a solution.
