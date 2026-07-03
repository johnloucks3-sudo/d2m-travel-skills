Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260701-ai-auth-probe.md`.

**The tell:** The probe is failing the same way every time because it's **not adapting to network reality**. Synchronous calls + zero backoff + aggressive timeout = a system that breaks predictably under transient latency. The fix isn't Telegram-side — it's probe architecture: connection reuse, exponential backoff, circuit breaker. This runs on 5-in-7d pattern because the network occasionally hiccups, the fixed timeout is exceeded, and the repair doesn't learn anything.

**For Hale:** This is autonomous. Code diff + test + deploy. No Commander gate. Infrastructure, not client-facing. Verification is deterministic — soak-test the probe for 1 hour and watch for the zero-failure signal you're not getting now.
