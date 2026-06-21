# MISSION-243 Quickstart — Kuklinski Jul 15 Trigger
## Pre-Deployment Checklist & Monitoring Guide

---

## Installation (One-Time Setup)

```bash
# 1. Copy systemd files to user directory
cp /home/john/Thunderbird/OpsCenter/kuklinski-jul15-trigger.timer ~/.config/systemd/user/
cp /home/john/Thunderbird/OpsCenter/kuklinski-jul15-trigger.service ~/.config/systemd/user/

# 2. Reload systemd daemon to recognize new files
systemctl --user daemon-reload

# 3. Enable the timer (auto-starts at next boot)
systemctl --user enable kuklinski-jul15-trigger.timer

# 4. Start the timer immediately
systemctl --user start kuklinski-jul15-trigger.timer

# 5. Verify installation
systemctl --user status kuklinski-jul15-trigger.timer
systemctl --user list-timers --all | grep kuklinski
```

---

## Pre-Trigger Verification (Jun 14 - Jul 14)

- [ ] Systemd timer is enabled
  ```bash
  systemctl --user is-enabled kuklinski-jul15-trigger.timer
  # Expected output: enabled
  ```

- [ ] Service file is valid
  ```bash
  systemd-analyze verify ~/.config/systemd/user/kuklinski-jul15-trigger.service
  # Expected output: (no errors, no output = valid)
  ```

- [ ] Script is executable
  ```bash
  test -x /home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py && echo "✅ Executable"
  ```

- [ ] Dry-run works
  ```bash
  python3 /home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py
  # Expected: "Trigger date not yet reached" message + exit code 0
  ```

---

## Jul 15 Morning — What to Expect

### 05:30 MT — Automatic Trigger Fires

The systemd timer automatically executes the Python script:

```
systemd-timer ← 05:30 MT Jul 15
    ↓
kuklinski-jul15-trigger.service
    ↓
kuklinski_jul15_creative_chain_trigger.py
    ↓
Updates hale_state.json + mission_board.json
    ↓
Logs to /home/john/Thunderbird/logs/kuklinski_jul15_trigger.log
```

### 05:31 MT — Verify Trigger Fired

Check the system journal:
```bash
journalctl --user -u kuklinski-jul15-trigger.service --since "2026-07-15 05:00" --until "2026-07-15 06:00"
```

Expected output:
```
Jul 15 05:30:46 yoga systemd[...]: Started Kuklinski Jul 15 Creative Chain Trigger.
Jul 15 05:30:46 yoga kuklinski-jul15-trigger[...]: KUKLINSKI JUL 15 TRIGGER FIRED
Jul 15 05:30:47 yoga kuklinski-jul15-trigger[...]: Added deferred alert: KUKLINSKI-JUL15-VALIDATION-CHAIN
Jul 15 05:30:47 yoga kuklinski-jul15-trigger[...]: CREATIVE CHAIN INITIATED SUCCESSFULLY
```

### 06:00+ MT — Hale Session Starts

When Hale loads her session:
- Reads MISSION-243 from mission_board.json
- Spawns creative chain: Luna → Harlan → Dani → TALON+JET
- Stages Gmail draft in d2mconcierge with THUNDERBIRD-Commander-Review label

### 06:30+ MT — Morning Brief

Brief surfaces: "Kuklinski validation email draft ready for WF-17 review"

---

## Monitoring Commands

### Check Trigger Status

```bash
# Is the timer enabled?
systemctl --user is-enabled kuklinski-jul15-trigger.timer

# When will it fire next?
systemctl --user list-timers --all | grep kuklinski

# Status of the service
systemctl --user status kuklinski-jul15-trigger.service
```

### Check Execution Results (Post Jul 15)

```bash
# Check deferred alert was added
grep "KUKLINSKI-JUL15-VALIDATION-CHAIN" /home/john/Thunderbird/hale_state.json

# Check mission was created
grep "MISSION-243" /home/john/Thunderbird/OpsCenter/mission_board.json

# Check script logs
tail -50 /home/john/Thunderbird/logs/kuklinski_jul15_trigger.log

# Check system journal
journalctl --user -u kuklinski-jul15-trigger.service --since "2026-07-15"
```

---

## Troubleshooting

### Timer Didn't Fire

**Symptom:** Jul 15 passed, no trigger, system was on

**Recovery:**
```bash
# Check if timer is still enabled
systemctl --user status kuklinski-jul15-trigger.timer

# Manually run the script
python3 /home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py

# Check logs
tail -50 /home/john/Thunderbird/logs/kuklinski_jul15_trigger.log
```

### Script Ran but No State Updated

**Symptom:** Timer fired, script exited 0, but no changes in hale_state.json

**Recovery:**
```bash
# Check file permissions
ls -la /home/john/Thunderbird/hale_state.json
ls -la /home/john/Thunderbird/OpsCenter/mission_board.json

# Check logs for errors
tail -100 /home/john/Thunderbird/logs/kuklinski_jul15_trigger.log

# Check if creative chain already initiated
grep "MISSION-243" /home/john/Thunderbird/OpsCenter/mission_board.json
```

### Creative Chain Didn't Spawn

**Symptom:** MISSION-243 exists but no Luna/Harlan/Dani agents spawned

**Recovery:**
```bash
# Check if Hale session has run since Jul 15
grep "MISSION-243" /home/john/Thunderbird/hale_state.json

# Manually trigger by starting Hale session
# (Hale automatically detects MISSION-243 at session start)

# Or manually route through creative chain via Agent tool
```

---

## Key Files

| Purpose | Location |
|---------|----------|
| Timer definition | `/home/john/Thunderbird/OpsCenter/kuklinski-jul15-trigger.timer` |
| Service definition | `/home/john/Thunderbird/OpsCenter/kuklinski-jul15-trigger.service` |
| Python orchestrator | `/home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py` |
| Full documentation | `/home/john/Thunderbird/docs/KUKLINSKI_JUL15_TRIGGER_GUIDE.md` |
| Execution results | `/home/john/Thunderbird/output/executor_results/MISSION-243_20260614.md` |
| Script logs | `/home/john/Thunderbird/logs/kuklinski_jul15_trigger.log` |
| Hale state | `/home/john/Thunderbird/hale_state.json` |
| Mission board | `/home/john/Thunderbird/OpsCenter/mission_board.json` |

---

## Contact & Notes

- **Client:** Kuklinski Group (3 couples)
- **Voyage:** Viking Mars — Panama Canal (Dec 17-27, 2026)
- **Primary Contact:** kyle.kuklinski@gmail.com
- **Trigger Purpose:** Initiate validation email on Jul 15 (excursion booking window opens Aug 2)
- **Creative Chain:** Luna (narrative) → Harlan ($$ verify) → Dani (voice) → TALON+JET (quality)
- **Final Gate:** WF-17 (Commander sends)

---

**Last Updated:** 2026-06-14  
**Mission Status:** ✅ COMPLETE  
**Target Execution:** 2026-07-15 @ 05:30 MT
