# SILVERSEA SILVER SPIRIT — DAILY INTELLIGENCE COMMISSION
**Deployed: 2026-04-27 | Col Victoria Hale, COS | Thunderbird Wing**

---

## OVERVIEW

**What:** Automated daily intelligence sweep for Silversea Silver Spirit sailings  
**When:** Every day at 06:30 MDT (runs first thing in the morning before COS brief)  
**Who:** Hale COS — autonomous operation, no Commander action required  
**Delivery:** Report to Commander inbox / Telegram  
**Purpose:** Monitor Silver Spirit market position, pricing, availability, and ship intelligence for competitive analysis and client recommendations  

---

## WHAT GETS SEARCHED DAILY

| Category | Details |
|----------|---------|
| **Current Sailings** | Active Silver Spirit itineraries, dates, nights, departure ports |
| **Pricing** | Per-person base pricing, all-inclusive positioning, comparison to Regent/Cunard |
| **Suite Availability** | Suite categories open, occupancy signals, premium suite availability |
| **Deck Plans & Specs** | Confirm deck plans current in Drive, ship specifications (36,821 GT, 633 pax, 267 suites) |
| **Recent Announcements** | New itineraries, sail date changes, onboard amenity updates |
| **Competitive Intel** | How Silver Spirit positions vs other ultra-luxury lines (positioning, pricing, service model) |

---

## AUTOMATION STACK

### Systemd Timer + Service

**Files:**
- `/home/john/Thunderbird/deploy/systemd/silver-spirit-daily-intel.timer` — Schedules daily execution
- `/home/john/Thunderbird/deploy/systemd/silver-spirit-daily-intel.service` — Runs the Python script

**Schedule:** `OnCalendar=*-*-* 06:30:00` (every day at 06:30 MDT)  
**Randomization:** ±2 minutes (prevents clock-skew failures)  
**Persistence:** `Persistent=true` (if system is down at 06:30, it will run on next boot)  

### Python Script

**File:** `/home/john/Thunderbird/OpsCenter/silver_spirit_daily_intel.py`

**Execution:**
```bash
.venv/bin/python /home/john/Thunderbird/OpsCenter/silver_spirit_daily_intel.py
```

**Output:**
- Structured JSON report in memory
- Formatted Telegram message (~4K chars)
- Archive in `/home/john/Thunderbird/intel/silver_spirit_YYYYMMDD_HHMMSS.md`
- Logs to `/home/john/Thunderbird/logs/silver_spirit_intel_YYYYMMDD.log`

---

## DEPLOYMENT

### Enable the Timer

```bash
# Copy systemd files (if not already in place)
sudo cp /home/john/Thunderbird/deploy/systemd/silver-spirit-daily-intel.* \
  /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable the timer (persistent across reboots)
sudo systemctl enable silver-spirit-daily-intel.timer

# Start the timer
sudo systemctl start silver-spirit-daily-intel.timer

# Verify it's active
sudo systemctl status silver-spirit-daily-intel.timer --no-pager
# Expected: Active: active (waiting)

# View next scheduled run
sudo systemctl list-timers silver-spirit-daily-intel.timer

# Test run (manual execution)
sudo systemctl start silver-spirit-daily-intel.service

# Check logs
journalctl -u silver-spirit-daily-intel.service -n 50 -f
```

### Post-Deployment Verification

```bash
# Check that the timer fired successfully
sudo systemctl list-timers silver-spirit-daily-intel.timer
# Should show: Last trigger time, Next trigger time

# Verify log file created
ls -la /home/john/Thunderbird/logs/silver_spirit_intel_*.log

# Verify report archived
ls -la /home/john/Thunderbird/intel/silver_spirit_*.md

# Read latest report
cat /home/john/Thunderbird/intel/silver_spirit_*.md | tail -50
```

---

## WHAT HAPPENS EACH DAY

**06:30 MDT ±2 min:**
1. systemd fires `silver-spirit-daily-intel.service`
2. Python script starts in `/home/john/Thunderbird` directory
3. Script searches Silversea.com for Silver Spirit sailings
4. Gathers pricing, availability, deck plan data
5. Formats as Telegram-compatible message
6. Archives markdown report to `intel/` directory
7. Logs execution and any errors to `logs/` directory
8. Script exits (success = return code 0)

**Expected duration:** 30-60 seconds  
**Output:** 1-2 Telegram messages to Commander (delivered immediately after completion)

---

## REPORT STRUCTURE

Each daily report includes:

```
**SILVERSEA SILVER SPIRIT — DAILY INTELLIGENCE**
2026-04-27 06:30 MDT

**CURRENT SAILINGS**
• Mediterranean Riviera (7 nights) — ongoing
• Iberian Peninsula & Atlantic Islands (10 nights) — ongoing

**PRICING POSITION**
[Current per-person pricing, all-inclusive positioning analysis]

**SUITE AVAILABILITY**
[Open suites, occupancy signals, booking recommendations]

**DECK PLAN & SPECS**
[Specs confirmed, link to Drive deck plans]

**NEXT SEARCH:** Tomorrow 06:30 MDT
**SOURCE:** Silversea.com + internal research
— Hale, COS
```

---

## FAILURE HANDLING

If the script fails:

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Network timeout | Log shows "requests.Timeout" | Automatic retry at next 06:30 |
| Silversea page structure change | Log shows "NOT_PARSEABLE" | Manual script update required; alert to COS |
| Telegram delivery fails | Log shows "Telegram send failed" | Report still archived in intel/; manual send if critical |
| Service crashes | systemd logs error, returns code 1 | systemd will NOT auto-restart (oneshot type); next run at 06:30 |

**Check logs if no report appears:**
```bash
journalctl -u silver-spirit-daily-intel.service -n 100
cat /home/john/Thunderbird/logs/silver_spirit_intel_$(date +%Y%m%d).log
```

---

## FUTURE ENHANCEMENTS

- [ ] Integration with MCP ship intelligence tool for deeper scraping
- [ ] Comparison to Regent Seven Seas pricing (automated weekly comparison brief)
- [ ] Deck plan changes detection (new suites, itinerary updates)
- [ ] TA/interline rate signal detection (travel advisor rates available?)
- [ ] CruiseCritic reviews monitoring (new reviews of Silver Spirit daily)
- [ ] n8n workflow integration (combine with Spring 2027 watch for unified report)

---

## RELATED SYSTEMS

- **Weekly Spring 2027 Monitor:** `docs/SILVERSEA_SPRING_2027_WATCH.md` (n8n, Mondays 08:00)
- **Ship Intelligence MCP:** `core/intel/thunderbird_ship_intel.py` (broader cruise line scraping)
- **Nightly Intel Sweep:** `thunderbird-agentic-intel.service` (01:00 MDT, all lines)
- **Client Dossiers:** Individual Silver Spirit booking notes in dossier records

---

## COMMANDER ACTIONS

**No action required.** Report arrives daily at 06:30 MDT.

If you want to:
- **Adjust timing:** Edit timer `OnCalendar=` in `/etc/systemd/system/silver-spirit-daily-intel.timer`
- **Add custom search terms:** Edit `silver_spirit_daily_intel.py` (sections 1-5)
- **Pause temporarily:** `sudo systemctl stop silver-spirit-daily-intel.timer`
- **Resume:** `sudo systemctl start silver-spirit-daily-intel.timer`
- **Disable permanently:** `sudo systemctl disable silver-spirit-daily-intel.timer`

---

## STATUS COMMANDS (For Ops)

```bash
# See next 5 scheduled runs
systemctl list-timers silver-spirit-daily-intel.timer

# See last 10 executions
journalctl -u silver-spirit-daily-intel.service -n 10 --no-pager

# Real-time logs while running
journalctl -u silver-spirit-daily-intel.service -f

# Force immediate run (for testing)
systemctl start silver-spirit-daily-intel.service

# Disable auto-start (but keep timer)
systemctl mask silver-spirit-daily-intel.service

# Re-enable auto-start
systemctl unmask silver-spirit-daily-intel.service
```

---

*Commissioned 2026-04-27 | Hale, COS | Thunderbird Wing*
