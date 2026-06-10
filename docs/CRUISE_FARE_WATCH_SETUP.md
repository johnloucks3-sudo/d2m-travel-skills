# Cruise Fare Watch Setup — Norway/Scandinavia 2027
## MISSION-068 Implementation Guide

**Status:** Scan worker ready. Awaiting Commander authentication on three platforms.

**Timeline:** Commander 2026-06-09. Automated scans begin once authentication complete.

---

## Overview

MISSION-068 establishes weekly fare monitoring for luxury Norway/Scandinavia cruises (Jul–Aug 2027):
- **Ships:** Silversea Silver Dawn, Seabourn Quest, Regent Seven Seas Voyager
- **Route:** Copenhagen → Southampton (10–18 days)
- **Alert thresholds:** Drops below $9,360pp, spikes above $11,960pp
- **Sources:** Perx, Odysseus/TESS, CruiseComplete

All pricing data is pulled via **Chrome Remote Debugging Protocol (CDP, port 9222)**, which means the scanner connects to your already-authenticated browser tabs and extracts live pricing.

---

## What You Need to Do (Commander)

### Step 1: Open Chrome with Remote Debugging Enabled (Already Running)

The system is running Chrome with remote debugging enabled on port 9222. Verify:
```bash
curl http://localhost:9222/json/list
```
Should return a list of open tabs (if it does, port 9222 is working).

### Step 2: Log Into Perx

1. **Open a Chrome tab:** Navigate to https://www.perx.com/account/login/
2. **Log in:** yodainva@gmail.com / Falcons4me!
3. **Stay logged in:** Don't close the tab. The scanner will find it.

**Why Perx?**
- Perx provides **interline rates** (employee/industry discounts) — best signal for TA pricing trends.
- Heavy discounts indicate incoming public-market rate drops.

### Step 3: Log Into Odysseus/TESS

1. **Open a Chrome tab:** Navigate to https://www.odysseus.travel/
   - (Or your TESS login URL if you have a direct link)
2. **Log in with your credentials**
3. **Stay logged in:** Don't close the tab.

**Why Odysseus/TESS?**
- This is the **primary booking system** for outside agents.
- Prices here are closest to what clients actually pay.
- Booking availability signals demand tier.

### Step 4: Log Into CruiseComplete

1. **Open a Chrome tab:** Navigate to https://www.cruisecomplete.travel/
   - (Or your partner portal login if different)
2. **Log in with your credentials**
3. **Stay logged in:** Don't close the tab.

**Why CruiseComplete?**
- Independent pricing cross-check.
- Sometimes offers different cabin categories or rates.
- Validates multi-source availability.

### Step 5: Verify Tabs Are Open

Run the verification script:
```bash
python3 scripts/fare_watch_cruise_scanner.py --list
```

Should output:
```
  norway-scandinavia-cruise-jul-aug-2027  Norway/Scandinavia Cruise Jul–Aug 2027 (Copenhagen→Southampton, 10–18 days)
```

Then test a scan:
```bash
python3 scripts/fare_watch_cruise_scanner.py
```

If all three sources are accessible, you'll see output like:
```json
{
  "timestamp": "2026-06-09T...",
  "watches_checked": 1,
  "watches_total": 1,
  "alerts": [],
  "errors": [],
  "sources": {
    "perx": "OK",
    "odysseus": "OK",
    "cruisecomplete": "OK"
  }
}
```

---

## How It Works (Technical)

### Chrome CDP Connection

The scanner uses **Playwright** to connect to the Chrome instance via the Debug Protocol:
```python
async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]  # First context (your logged-in session)
    pages = context.pages  # All open tabs
```

This means:
- **No separate login needed** — you're reusing your authenticated tabs
- **Session persistence** — your login cookies stay active across scans
- **Real-time prices** — the scanner sees the same pages you see when you're logged in

### Price Extraction

For each source, the scanner:
1. Finds the appropriate tab (keyword match: "perx", "odysseus", "cruisecomplete")
2. Extracts all visible text from the page
3. Searches for ship names: "Silver Dawn", "Seabourn Quest", "Seven Seas Voyager"
4. Extracts prices from the same line (regex: `$X,XXX` pattern)
5. Compares against alert thresholds

**Alert Triggers:**
- **PRICE DROP:** If price < $9,360pp → Telegram alert + log
- **PRICE SPIKE:** If price > $11,960pp → Telegram alert + log
- **NO PRICES:** If a source returns no data → warning in log

### Telegram Alerts

When an alert triggers, the scanner sends a formatted message to the Commander's Telegram:
```
🚨 CRUISE FARE ALERT — 1 triggered
Watch: Norway/Scandinavia Cruise Jul–Aug 2027 (Copenhagen→Southampton, 10–18 days)
2026-06-09 14:23 MT

🚢 PRICE DROP: Silver Dawn at PERX — $8,954pp (baseline $10,400) — -13.9%

Scanned: PERX, ODYSSEUS, CRUISECOMPLETE
— A2 Dembe / Hale · Thunderbird Cruise Fare Watch
```

---

## Automation (systemd Service)

Once authenticated, the scanner runs **weekly** (configurable) via systemd timer.

**Service file:** `/etc/systemd/user/thunderbird-cruise-fare-watch.service` (to be created)

**Timer file:** `/etc/systemd/user/thunderbird-cruise-fare-watch.timer` (to be created)

**Enable automatic runs:**
```bash
systemctl --user enable thunderbird-cruise-fare-watch.timer
systemctl --user start thunderbird-cruise-fare-watch.timer
```

**Manual test run:**
```bash
systemctl --user start thunderbird-cruise-fare-watch.service
```

**View logs:**
```bash
journalctl --user -u thunderbird-cruise-fare-watch.service -f
```

---

## Troubleshooting

### Issue: "Failed to connect to Chrome CDP (port 9222)"

**Check:**
1. Is Chrome running with remote debugging?
   ```bash
   curl http://localhost:9222/json/list
   ```
   If connection refused → Chrome isn't running in debug mode.

2. Did you log out of the tabs? Log back in and keep tabs open.

**Fix:**
```bash
# Kill Chrome and restart with remote debugging
pkill -f "chrome.*9222"

# (Your system daemon should auto-restart Chrome with port 9222 enabled)
```

### Issue: "No Perx tab found in browser"

**Check:**
1. Are you logged into Perx?
   - Open https://www.perx.com/account/
   - If redirects to login → session expired. Log in again.

2. Is the Perx tab still open in Chrome?
   - If you closed the tab, open a new one and log in.

**Fix:**
```bash
# Manually log in to Perx
python3 scripts/perx_session_keepalive.py
```

This will refresh your Perx cookies and keep them valid.

### Issue: "No prices found"

**Possible causes:**
1. The website layout changed → selectors need updating
2. Paywall or JS rendering issue → page not fully loading
3. Search results are empty for that date range

**Debug:**
```bash
# Add verbose logging
python3 scripts/fare_watch_cruise_scanner.py --source perx 2>&1 | grep -A 10 "Perx scrape"

# Or inspect the page directly
python3 scripts/rssc_grab_page.py  # (generic page grabber for any open tab)
```

---

## Next Steps

**Hale/Dembe:**
1. **Verify authentication** (Step 5 above)
2. **Create systemd timer** once Commander confirms all three sources work
3. **Set schedule:** Weekly scans (suggest: Monday 0600 MT)
4. **Monitor first week** for alert accuracy

**Commander:**
1. Keep those three tabs open (or refresh if session expires)
2. Check Telegram for alerts
3. Confirm that alert thresholds match your comfort level

---

## File Locations

- **Scanner script:** `/home/john/Thunderbird/scripts/fare_watch_cruise_scanner.py`
- **Fare watch config:** `/home/john/Thunderbird/data/fare_watches.json` (watch ID: `norway-scandinavia-cruise-jul-aug-2027`)
- **Last scan results:** `/home/john/Thunderbird/data/fare_watches/last_check_cruise.json`
- **Logs:** `/home/john/Thunderbird/logs/fare_watch_cruise_scanner.log`
- **Chrome cookies (Perx):** `/home/john/Thunderbird/creds/perx_cookies.json` (kept fresh via keepalive daemon)

---

## Related Missions

- **MISSION-067:** Dembe's initial research on Silversea/Seabourn/Regent pricing
- **MISSION-069:** Chrome port 9222 reliability (infrastructure blocker, now cleared)
- **MISSION-114:** Spencer air quote (Centrav B2B, similar pattern)

---

## Questions?

Check the full mission board: `OpsCenter/mission_board.json` (search for MISSION-068)

Hale escalation: `@Personas/hale_cos.md` § "Autonomy Posture"
