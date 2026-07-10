# FARE WATCH ALERT — Execution Report (Amadeus API Monitoring)
*2026-07-06 · Task: Deploy d2m-fare-watch-alert service (Amadeus API monitoring)*

## Finding: Already deployed. No new build required — duplicate avoided.

### 1. API key status
**Present.** `/home/john/Thunderbird/amadeus_credentials.json` has `client_id` + `client_secret`.
Also loaded via `.env` (`AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET`), consumed by `scripts/fare_watch_amadeus.py`.
No Infisical secrets file exists at the path given in the task (`config/infisical_secrets.json` — not present on this system); credentials are stored directly in `amadeus_credentials.json` + `.env` instead. Not a blocker — key is live and working.

### 2. Existing service (pre-dates this task)
| Component | Detail |
|---|---|
| Script | `scripts/fare_watch_amadeus.py` — Amadeus Flight Offers Search integration, replaces Centrav for trendline/alert monitoring |
| Route source | `core/travel/data/fare_watches.json` (27 active watches) |
| Results | `OpsCenter/fare_watches/last_check_amadeus.json` (latest snapshot) + `amadeus_history.json` (trendline) |
| Alerting | Telegram → D2MC2C_bot → Commander (7554895206), threshold-based, dedup'd |
| Systemd unit | `thunderbird-fare-watch.service` → `thunderbird-fare-watch.timer` (`OnCalendar=*-*-* 02:30:00`, daily before AM brief) |
| Status | `enabled` / `active`. Last run 2026-07-06 08:33 UTC: **27/27 watches OK, 0 errors, 8 alerts fired.** |

A second, generic Telegram alert hook also exists and runs 3x/day: `d2m-fare-watch-alert.service`/`.timer` (MISSION-145, `scripts/fare_watch_alert.py`) — reads the same `fare_watches.json` store (any provider, not just Amadeus) and fires dedup'd Telegram alerts independently.

### 3. Test result
Not re-run manually — the live systemd run from earlier today (2026-07-06 08:33 UTC) already exercised the full path end-to-end and fired 8 real alerts, confirmed in `OpsCenter/fare_watches/fare_watch.log`.

### 4. Cadence note (only real gap vs. the task spec)
Task asked for a 2-hour interval (`OnUnitActiveSec=2h`). The existing `thunderbird-fare-watch.timer` runs **once daily** (02:30 MDT), by design — "before AM brief." Flagging this discrepancy rather than unilaterally changing a live production timer's cadence: if 2-hourly Amadeus polling is actually wanted (vs. the current daily-batch design), that's a cadence change to existing infra, not a new deployment, and should go through Hale/Sterling review rather than a silent edit.

## Conclusion
No escalation needed (key present), no new service built (duplicate of `thunderbird-fare-watch.timer` + `fare_watch_amadeus.py`, which is already live, enabled, and firing real alerts). Recommend closing this task as **already satisfied** unless the 2-hour cadence is a hard requirement — in which case that's a one-line `OnUnitActiveSec=2h` timer edit, held for confirmation before touching a live unit.
