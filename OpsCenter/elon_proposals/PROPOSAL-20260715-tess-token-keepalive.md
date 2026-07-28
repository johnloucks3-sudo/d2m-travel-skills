Proposal complete. Structured analysis:

**ROOT CAUSE:** Playwright credential login has zero exception handling. When Akamai/network causes `page.goto()` timeout, unhandled exception crashes the service → systemd OnFailure restarts it. Transient errors trigger full restart cycle (MTBF ~1.7 days).

**FIX:** Add exponential backoff retry wrapper (max 3 attempts, 1s/2s/4s delays) around page navigation/fill/click operations. Converts crash-on-timeout to "retry gracefully, exit 1 if all fail."

**DECISION:** Apply autonomously — infrastructure fix, zero client impact, zero financial gate. Deploy immediately; monitor 7 days for MTBF improvement (target: zero OnFailure events).

Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260715-tess-token-keepalive.md` — ready for Hale execution.

Thanks 🎯

2026-07-15T18:14:00Z MT
