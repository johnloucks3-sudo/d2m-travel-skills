Proposal written. **ELON's diagnosis:**

The service crashes intermittently on transient network errors (DNS timeouts, network state changes) instead of retrying. The watchdog masks the issue by restarting it. The fix is straightforward:

1. **Add retry logic to the refresh script** (3 attempts, exponential backoff)
2. **Run the timer twice daily** instead of once (05:00 + 17:00 MT)

This is an **APPLY_AUTONOMOUSLY** fix — operational, low-risk, no secrets required. Hale can execute it and monitor for 7 days to verify zero unwanted restarts.

Proposal saved to: `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260614-thunderbird-silversea-session-ROOT-CAUSE.md`
