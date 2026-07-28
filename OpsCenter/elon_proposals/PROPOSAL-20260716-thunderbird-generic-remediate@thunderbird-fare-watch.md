Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260716-thunderbird-generic-remediate@thunderbird-fare-watch.md`.

**Summary:**

I've diagnosed the recurring restart pattern (7x in 7d) as a root-cause fault in the fare-watch service—likely credential expiration, rate limiting, or resource leaks—rather than a transient issue. The proposal recommends:

- **Root cause:** Service lacks defensive credential refresh and API backoff logic, causing daily failures that Hale's watchdog keeps restarting
- **Fix:** Add just-in-time credential refresh, exponential backoff for rate limits, and structured logging to surface actual errors
- **Decision:** `APPLY_AUTONOMOUSLY` — Hale runs diagnostics (15 min), applies code fix if clear, verifies clean 24h+ run. Escalates to Commander only if diagnosis is ambiguous (within 30 min)

This stops the symptom-relief cycle and makes the service resilient. No more wasting compute cycles on daily restarts.
