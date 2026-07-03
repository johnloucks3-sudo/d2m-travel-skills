**Proposal complete.** Written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260628-tess-token-keepalive.md`

**Summary:**

The prior proposal (09:02 MT) called the Playwright fallback "working perfectly," but the current logs reveal it's now broken: Chromium isn't installed. This shows the architecture is fragile by design — proactive timer-based keepalives fail in cascading ways.

ELON's recommendation: **Replace the entire timer + Playwright layer with reactive call-time validation** (industry standard pattern in AWS SDK, Google clients, etc.). No more background daemon. Token validation happens inline when TESS is actually needed. Simpler, more robust, standard.

**Decision:** `APPLY_AUTONOMOUSLY` — this is a code refactor in the TESS wrapper, not a gate decision. Hale can execute over 2–3 work days by 2026-07-01. Parallel: Commander should rotate TESS credentials (separate action, not blocking).

The proposal is ready for Hale to route and execute.
