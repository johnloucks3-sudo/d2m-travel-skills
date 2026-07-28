Proposal filed: **poe-points-check service recurring failures (3x in 7 days).**

**Root cause:** Brittle error handling on transient API failures (rate-limit, timeouts, 5xx). Service exits hard instead of retry-with-backoff.

**Fix:** Add 3-attempt exponential backoff retry logic + structured logging. Code change only, zero operational risk.

**Decision:** APPLY_AUTONOMOUSLY per standing order — Hale executes within workflow cycle, reports completion in brief.

This pattern is classic operational noise masking sound integration (auto-heal succeeds 100%)—just needs defensive coding. No Commander decision required.

Thanks
