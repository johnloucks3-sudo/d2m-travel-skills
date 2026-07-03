The file already exists with a complete, high-quality proposal from 04:53 MT. Content matches the current task exactly — same event ID, same recurrence pattern, same auto_healed signal. No rewrite needed; the deliverable is durable at the requested path.

**File:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260702-inbox-hygiene.md` — 161 lines, verdict **APPLY_AUTONOMOUSLY**.

**Root cause (summary):** Service always exits 0 despite 251 `ECONNRESET` errors in log — silent success masks Gmail-token expiry gap between 10-min hygiene runs and 90-min OAuth keepalive. Watchdog's "auto_heal" is theater.

**Fix:** exit 1 when both accounts fail + 1 retry with 2s backoff in `_find_messages()` + timer 10min→30min. Rollback = `git revert` + timer restart.

**Next:** Hale should execute — the June 13 proposal carried the same verdict and was never applied; today's log evidence confirms the same failure mode is still live.
