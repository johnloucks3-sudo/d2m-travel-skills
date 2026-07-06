# EXECUTION RECORD — PROPOSAL-20260528-thunderbird-fare-watch.md
**Date:** 2026-07-06 · **Executor:** Hale (Claude Code)

## DISPOSITION: PROPOSAL STALE / NOT APPLIED — SERVICE VERIFIED HEALTHY, ALREADY LIVE

The `APPLY_AUTONOMOUSLY` code diff and standing order in this proposal were **not applied**. Investigation found the proposal's technical premise no longer matches the deployed system. Applying it as written would have edited the wrong file and referenced a watchdog structure that no longer exists.

## FINDINGS

**1. Service already deployed and active.**
`thunderbird-fare-watch.service` + `.timer` are loaded, enabled, running daily at 02:30 MDT. No deployment action was needed.

**2. Proposal targets the wrong file.**
The proposal's code diff targets `core/travel/thunderbird_fare_watch.py`. The actual `ExecStart` for `thunderbird-fare-watch.service` is `scripts/fare_watch_amadeus.py` — a different file entirely. `core/travel/thunderbird_fare_watch.py` is a shared data-access module imported by ~14 unrelated scripts (MCP servers, scheduler, `list_watches.py`, `flight_scan_trigger.py`, etc.), not the daemon that was restarting. Patching it per the proposal would not have touched the actual service and would have risked those 14 importers.

**3. Proposal's watchdog patch site doesn't exist.**
The proposal calls for changing `auto_heal=["fare-watch"]` to `manual_restart_only=["fare-watch"]` at "line 187" of `thunderbird_coo_watchdog.py`. The current watchdog uses a `TIER1_SERVICES` / `TIER2_SERVICES` dict classification (not an `auto_heal=[...]` list). `thunderbird-fare-watch` is already classified Tier 2 (self-heal, log only, no Commander page) — the pattern the proposal describes was superseded by later watchdog architecture.

**4. Root cause was misdiagnosed.**
The proposal hypothesizes deadlock/resource-starvation from unbounded Bedsonline/CruCom/GYG connections. The service doesn't call those suppliers — it calls the Amadeus API. The actual Jul 4 and Jul 5 exit-code-1 failures (confirmed via `fare_watch.log` traceback) were transient DNS/connection failures reaching the Amadeus token endpoint (`urllib3.connection` → `create_connection` failure), which self-recovered on the next scheduled run. Not a deadlock; not the supplier set named in the proposal.

## VERIFICATION (independent, this session)

- Manually triggered `systemctl --user start thunderbird-fare-watch.service` — exit code 0/SUCCESS, ~2m runtime.
- Fresh log output: 26/27 watches checked, 8 alerts fired correctly, 0 errors.
- Scheduled Jul 6 02:30 run also completed clean (exit 0).
- `fare_watch_deadman_alert.json` shows `dark_hours: 999.0` — confirmed this is the dead-man switch's reset/sentinel value (fare-watch ran at 15:30 same day), not an active alarm.
- Only 2 failures in the last 30 days (Jul 4, Jul 5), both transient network errors, both self-recovered on next scheduled run — well under any restart-storm threshold.

## RECOMMENDATION (not executed — flagging only)

If the occasional Amadeus DNS/connection failure is worth hardening against, add a simple retry-with-backoff around `_get_amadeus_token()` in `scripts/fare_watch_amadeus.py` specifically (2-3 attempts, short backoff). This is a narrow, correctly-targeted version of the proposal's intent — scoped to the real failure point, not the unrelated module. Not built here; this is outside "verify/deploy," and the failure rate (2 transient errors/30 days, both self-healed) doesn't currently justify it.

## STATUS: CLOSE PROPOSAL AS SUPERSEDED

Recommend marking `PROPOSAL-20260528-thunderbird-fare-watch.md` as superseded-by-architecture-drift rather than accepted — the watchdog and service topology it describes moved on since May 28, and the service it worried about is healthy under current operation.
