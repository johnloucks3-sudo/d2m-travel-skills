**Proposal complete.** ELON's analysis of the Telegram gateway auto-heal pattern (11x/week):

**Root cause:** Unbounded daemon threads spawned per message without timeouts or resource limits. Handlers can hang (Claude calls up to 180s), accumulate memory/file descriptors, and eventually exhaust system limits. systemd's `Restart=always` masks the leak rather than fixing it.

**Fix:** Thread pool (max 10 workers) + per-handler timeout (300s) + exception wrapper around the entire polling loop + resource monitoring logs. Eliminates the crash-recovery cycle by making the service resilient.

**Decision:** `APPLY_AUTONOMOUSLY` — infrastructure reliability, P0, no gates needed. Hale can execute immediately.

Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260605-thunderbird-telegram-gw.md`.
