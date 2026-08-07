# RT-TELEGRAM — 4-Day Telegram Error Triage (brief)
**Session:** RT-TELEGRAM · **Date:** 2026-08-07 ~06:45 MT · **Seats:** CC ✅ AG ✅ ~~Grok~~ (omit — login)
**Method:** War Room — each seat reads evidence, files analysis + fix, then we consolidate + execute.
**Status:** DATA GATHERED — SEAT INPUT NEEDED

## Objective
Diagnose + fix ALL Telegram gateway errors observed over the past 4 days (2026-08-03 → 08-07). Determine if they share one root cause. Deliver: root-cause + concrete, low-risk fixes (prefer reuse of existing infra; no new stack).

## Evidence (ground truth, from journalctl + ps)
**A. Service externally terminated (SIGTERM 143), marked 'exit-code':**
- `2026-08-06 17:37:57` → `Main process exited, code=exited, status=143/n/a` → `Failed with result 'exit-code'`
- `2026-08-06 17:50:01` → same (143 / exit-code)
- 143 = SIGTERM. So external kill (systemd reset/what?/watchdog/manual), flagged as FAILED. Kills the bot → drops the poll → after restart re-polls.

**B. Duplicate getUpdates CONFLICT (confirmed thrash):**
- `2026-08-07 01:00:03 → 01:00:29` (×8): `Conflict: terminated by other getUpdates request; make sure that only one bot instance is running`
- Two processes polling SAME bot simultaneously → each terminates the other's getUpdates → loop. Only 1 process now (pid 2137 started 06:04), but conflict occurred at 01:00 → something spawns a 2nd instance intermittently (cron? stray background wrapper? watchdog overlapping restart?).

**C. Network / SSL flakiness to api.telegram.org (WARNING flood):**
- `Connection reset by peer (104)` — 17:19 ×3
- `SSLEOFError: UNEXPECTED_EOF_WHILE_READING ... api.telegram.org:443 getUpdates` — 19:52→20:06 ×5
- `Read timed out (read timeout=35)` — 01:47
- Long-poll `getUpdates` (timeout 35s) intermittently dies. MTU/keepalive/firewall/captive suspicion. Recovers on retry.

**D. 429 rate-limit:** 3 total (no retry-after captured). Probably burst from rapid restart re-poll. Low.

**E. NOT present (good):** no 403, no "chat not found", no blocked, no auth/credential errors.

## Your brief/responses (each fix-analysis)
1. SINGLE root cause or multiple independent?
2. FIX A (termination): what is sending SIGTERM to the gateway and how do we stop it? Check restart/OnFailure/WatchdogSec/start-limit and any cron/watchdog that restarts it.
3. FIX B (conflict): how to guarantee a single getUpdates poller per bot (lockfile? exclusive long-poll? suppress auto-restart on same token)? Prefer the gateway's own guard if present (gate v2.0).
4. FIX C (network/SSL): mitigation for the 35s long-poll drops — keepalive/backoff/enqueue-on-disconnect; are errors harmless churn or data loss? (getUpdates DROP vs send fail).
5. Any 429 mitigations (retry-after backoff / flood-control pacing).
6. Give me exact file+line targets and the min change (stdlib, no new deps).

Deliver to seat input file in OpsCenter/meetroom/RT-TELEGRAM/. Keep tight — this is a fix sheet, not an essay.