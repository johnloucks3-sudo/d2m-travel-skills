ISSUE: Supplier Lifecycle Management — validation and operational effectiveness framework for the new keepalive and sentinel systems.

DISCUSSION:

We have deployed four systemd-timed keepalive loops and a site structure sentinel. Sterling now needs a validation cadence to ensure these systems actually prevent the failures they were built to prevent.

Current deployment:
- d2m-rssc-session-keepalive.timer — every 4h (Regent cookies, was the #1 gap)
- d2m-centrav-session-keepalive.timer — every 90 min (existing centrav_reauth.py, now scheduled)
- d2m-perx-session-keepalive.timer — every 6h (new perx_session_keepalive.py)
- d2m-site-sentinel.timer — daily 08:00 (DOM hash change detection for 8 Tier 1/2 sites)
- sterling-lifecycle-validate.timer — every 6h (validates all of the above are running)

The Sterling validation script (scripts/sterling_validate_lifecycle.py) checks:
1. Each timer is active and firing within expected intervals
2. Cookie files are being refreshed (mtime within expected window)
3. Credentials health check has no unresolved client-affecting alerts
4. Site sentinel state file exists and has baselines recorded
5. Sends Telegram D2MC2C alert on any failure

Metrics to track going forward:
- Timer overdue rate: % of runs where a timer missed its window
- Cookie stall rate: how often a cookie file's mtime exceeds 2x the refresh interval
- Sentinel change detections: how many structural changes caught before scrapers broke
- Mean time to repair: from sentinel alert to updated scraper

ACTIONS I RECOMMEND TAKING:
1. Run `bash deploy/systemd/install_supplier_timers.sh` to install all timers
2. Run `python3 scripts/sterling_validate_lifecycle.py` to validate initial state
3. After first sentinel run (next 08:00), check `OpsCenter/state/site_sentinel_state.json` for baselines
4. Add a weekly validation review to morning brief: Sterling reports on lifecycle health
5. When a sentinel alert fires, before fixing the scraper, add the site to sites.json if not already there
6. Sterling monitors the validation output every 6h via the timer — any degrading alert goes to D2MC2C

---
Staff Paper from Sterling Code, D2M Travel
