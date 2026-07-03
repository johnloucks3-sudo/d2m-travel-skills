Done. I've written a structured ELON proposal analyzing the recurring `tess-token-keepalive` failures (6x in 7 days).

**Key findings:**

- **Root Cause:** TESS token has been expired for ~8 hours; refresh attempts hit `400 — invalid_client`, meaning the OAuth credentials themselves are invalidated on TESS's side. The Playwright fallback is failing silently. The timer keeps restarting the service endlessly because the problem is unrecoverable by automation.

- **Immediate Fix (Phase 1):** Detect `invalid_client` as a specific auth failure, log it, escalate to Commander via Telegram, and **stop retrying**. Mark the token as broken so the timer skips future runs instead of hammering Playwright endlessly.

- **Architecture Hardening (Phase 2):** Implement the reactive validation pattern from the 2026-06-28 proposal — replace 90-minute timer keepalives with call-time token checks inside every TESS API call.

- **Decision:** `APPLY_AUTONOMOUSLY` — Hale can execute Phase 1 in ~20 minutes (non-protected file, defensive change). Dembe/Sterling review Phase 2 in parallel for 2026-07-02.

Proposal is staged at `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260629-tess-token-keepalive.md` — ready for Hale routing.
