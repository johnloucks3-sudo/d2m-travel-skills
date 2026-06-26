**ELON BRIEFING — Hale, 2026-06-25 21:35 MT**

⚡

Wilco — TESS token keepalive issue analyzed. Proposal filed: `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260625-tess-token-keepalive.md`

**The Pattern (3x restarts in 7d):** Not a service crash. The watchdog is catching an unresponsive service during credential fallback. Every 90 minutes, the TESS OAuth token becomes invalid (400 `invalid_client`), the service attempts a Playwright-based re-login, and that login hangs long enough for the watchdog to restart the process.

**The Fix:** Two autonomous changes.
- **Code:** Wrap Playwright login in a 30-second timeout so it doesn't hang the service
- **Config:** Reduce keepalive timer from 90 min to 60 min so we never let an invalid token poison the cache

Both deploy in under 2 hours. The service will survive OAuth failures instead of appearing dead to the watchdog. The underlying OAuth credential issue (likely revoked/expired) becomes a background investigation for the Commander, not a blocker.

**Recommendation:** Apply Phase 2 + Phase 4 autonomously. Monitor 7 days. If failures persist, escalate the credential verification to Commander.

Proposal ready for your approval.

— ELON
