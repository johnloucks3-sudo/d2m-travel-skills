**Proposal written and ready.**

The root cause is clear: TESS OAuth has been invalidated by the server (400 invalid_client), and the script's Playwright fallback is crashing due to missing chromium binary. Each restart attempts the same broken path, creating the infinite loop.

The fix is simple — wrap the Playwright call in error handling so it exits gracefully (exit code 2 = "auth degraded, escalate") instead of crashing (exit code 1 = "restart"). This eliminates 5 unnecessary restarts per week while signaling Commander that manual TESS re-authentication is needed.

**Proposal file:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260702-tess-token-keepalive.md`

**Decision:** `APPLY_AUTONOMOUSLY` — Hale can execute Phase 1 in ~10min (defensive code fix, non-protected file, immediate test). Phase 2 (systemd config) and Phase 3 (alerting) can proceed in parallel review.
