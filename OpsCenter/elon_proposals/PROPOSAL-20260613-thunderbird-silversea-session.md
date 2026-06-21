**Proposal written.** ELON's analysis: the Silversea session service is dying on transient API failures (timeouts, rate limits) because it lacks retry logic — not a resource issue or watchdog problem. The watchdog is working correctly by restarting it; the fix is to eliminate the fragile persistent service and replace it with a resilient polling daemon (5-min interval) that handles errors gracefully instead of crashing.

**Hale should:**
1. Review the service logs (`journalctl` command in the proposal) to confirm transient API failures are the trigger
2. If confirmed, build the polling daemon autonomously (Path A) — it's within her execution band
3. If logs show something else, escalate to Commander with findings

The proposal is ready for Hale's review. Current auto-heal rate is ~3/week; polling daemon should drop that to near-zero.
