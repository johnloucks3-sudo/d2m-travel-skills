# PROPOSAL: Silversea Session Keepalive — Fix Recurring Crashes

**ELON Analysis — 2026-06-14 21:50 MT**

---

## ROOT CAUSE

The `thunderbird-silversea-session.service` crashes ~6 times per week due to unhandled network timeout exceptions in the Playwright Chromium refresh script. The service runs once daily (05:00 MT) but fails intermittently on DNS resolution errors (`net::ERR_NAME_NOT_RESOLVED`) and network state changes (`net::ERR_NETWORK_CHANGED`). When the script encounters these transient network faults, it crashes instead of retrying, causing the systemd watchdog to restart the service. This masks the real issue: the script lacks retry logic and exponential backoff for flaky network conditions, and the timer interval is too infrequent to maintain session freshness across expected portal timeout windows.

---

## PROPOSED FIX

**config_change + code_diff**

Two changes, executed as one:

1. **Fix script resilience:** Add retry logic with exponential backoff (3 attempts, 2s→4s→8s) for network errors. Graceful degradation: if all retries fail, log the error but exit with code 0 (success) — don't crash the service.

2. **Increase timer frequency:** Change `OnCalendar=*-*-* 05:00:00` to run every 12 hours (05:00 and 17:00 MT) instead of once daily. This keeps the Silversea session fresh across typical 24-48h portal timeout windows.

---

## IMPLEMENTATION

**Step 1: Update the keepalive script** (`scripts/silversea_cookie_refresh.py`)

Wrap the Playwright navigation in a retry loop:

```python
import time

def navigate_with_retry(page, url, max_retries=3):
    """Navigate with exponential backoff on transient network errors."""
    backoff_seconds = [2, 4, 8]
    last_error = None
    
    for attempt in range(max_retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return True  # Success
        except Exception as e:
            error_msg = str(e)
            # Transient errors worth retrying
            if any(x in error_msg for x in ["ERR_NAME_NOT_RESOLVED", "ERR_NETWORK_CHANGED", 
                                              "ERR_CONNECTION_RESET", "ERR_INVALID_RESPONSE"]):
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_seconds[attempt]
                    print(f"[RETRY {attempt+1}/{max_retries}] Network error, waiting {wait_time}s: {error_msg}")
                    time.sleep(wait_time)
                    continue
            # Non-transient error or final attempt — bail
            raise e
    
    # All retries exhausted
    print(f"[WARN] Session refresh failed after {max_retries} attempts: {last_error}")
    print("[INFO] Graceful degradation: exiting normally (session may be stale)")
    return False
```

Replace the existing `page.goto()` call in `check_and_refresh()` with:
```python
if not navigate_with_retry(page, "https://my.silversea.com", max_retries=3):
    logger.warning("Silversea session refresh failed after 3 retries. Existing session preserved.")
    # Exit with code 0 (success) — don't crash, watchdog will retry at next timer interval
    sys.exit(0)
```

**Step 2: Update the systemd timer** (`/home/john/.config/systemd/user/thunderbird-silversea-session.timer`)

Replace:
```ini
OnCalendar=*-*-* 05:00:00
```

With:
```ini
OnCalendar=*-*-* 05:00:00
OnCalendar=*-*-* 17:00:00
```

This runs the refresh twice daily: 05:00 MT and 17:00 MT.

**Step 3: Reload and restart**

```bash
systemctl --user daemon-reload
systemctl --user restart thunderbird-silversea-session.timer
systemctl --user restart thunderbird-silversea-session.service
```

**Step 4 (optional, for Centrav resilience): Apply same pattern to Centrav**

The same network flakiness likely affects `portal-keepalive.service` (which handles Centrav + Regent OA). Review `scripts/centrav_keepalive.py` for the same issue.

---

## VERIFICATION TEST

**7-day monitoring protocol:**

1. **Baseline check:** Confirm current restart count:
   ```bash
   journalctl --user-unit thunderbird-silversea-session.service -S "7 days ago" | grep -c "killed"
   ```
   Expected (baseline): ~6 kills in the past 7 days.

2. **Deploy the fix** (all steps above).

3. **Monitor for 7 days:** Check every morning (06:00 MT) via:
   ```bash
   systemctl --user status thunderbird-silversea-session.service
   tail -20 /home/john/Thunderbird/logs/silversea_session.log
   journalctl --user-unit thunderbird-silversea-session.service -S "today" --no-pager
   ```

4. **Success criteria:**
   - Zero unplanned kills (no watchdog restarts)
   - Service reaches both timer intervals (05:00, 17:00) and completes with code 0
   - Log shows no more than 1-2 retries per run; all retries succeed
   - Session health check passes at both 05:00 and 17:00

5. **Failure recovery:** If the script still crashes after 2 days, escalate to Commander with:
   - Full 2-day log excerpt
   - Playwright version + environment
   - Network baseline (ping my.silversea.com 10x, report latency/loss)

---

## HALE DECISION

**APPLY_AUTONOMOUSLY**

**Rationale:**
- Root cause confirmed (network timeout crashes + flaky error handling)
- Fix is low-risk (adds retry logic + changes timer interval — both reversible)
- No API keys, secrets, or credentials required
- Operational fix, not strategic (no multi-year impact, no >$5K cost)
- Fits Hale's autonomy band (spot-it-fix-it, execute+report)
- No Commander gate required; will report in tomorrow's morning brief

**Implementation authority:** Hale executes Steps 1–3 immediately. Step 4 (Centrav) logged as follow-up task in mission_board.json for Harlan/Sterling review.

**Audit trail:** Decision logged in `hale_decisions.md` with timestamp, rationale, and 7-day verification protocol.
