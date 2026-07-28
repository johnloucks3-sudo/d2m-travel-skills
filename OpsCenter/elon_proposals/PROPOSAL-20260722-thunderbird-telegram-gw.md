Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260722-thunderbird-telegram-gw.md`

**Summary for you:**

**ROOT CAUSE:** The Telegram gateway is experiencing chronic network timeouts to the Telegram API (read timeout=35s). While these are caught and logged as warnings, the underlying issue is that daemon thread deaths aren't prevented gracefully. When a poll loop thread dies due to an exception or resource exhaustion, the M-153 liveness monitor detects it and exits the main process. systemd restarts it, but the transient network issues cause this cycle to repeat ~1.7 times per day.

**Secondary issue:** Line 2589-2590 contains a duplicate `sleep(15)`, making the relay queue drain every 30 seconds instead of 15.

**FIX (3 changes, all autonomously executable):**
1. Add outer exception handler to `bot_poll_loop()` to prevent thread death on crashes (log + recover with exponential backoff)
2. Remove duplicate sleep in `relay_poll_loop()`
3. Add HTTP connection pooling reset to prevent stale Telegram API connections

**VERIFICATION:** 24-hour run monitoring for restart frequency drop from 12/week to <2/week. If effective, log to hale_decisions.md.

**HALE DECISION:** APPLY_AUTONOMOUSLY — all changes are defensive, isolated, and low-risk. No Commander gates required.
