# Hale Daily Transformation Audit

Automated daily audit that updates the TRANSFORMATION section in `hale_brief.md` with:
- Phase status
- Standards enforcement
- Operations status
- Decision count
- Open task count
- System health

## Execution Status

**Script:** `OpsCenter/hale_daily_audit.py`
**Log:** `logs/hale_audit.log`
**Schedule:** Systemd user timer (06:00 MDT daily)

### Check Timer Status
```bash
systemctl --user status hale-daily-audit.timer
```

### View Next Trigger
```bash
systemctl --user list-timers hale-daily-audit.timer
```

### View Recent Audit Logs
```bash
tail -20 logs/hale_audit.log
```

### Manual Trigger
```bash
python3 OpsCenter/hale_daily_audit.py
```

## Alternative: Cron Scheduling

If systemd timer is not available, use cron instead:

```bash
crontab -e
```

Add this line (runs at 06:00 MDT):
```cron
0 6 * * * cd /home/john/Thunderbird && python3 OpsCenter/hale_daily_audit.py
```

## Files

- **Service:** `~/.config/systemd/user/hale-daily-audit.service`
- **Timer:** `~/.config/systemd/user/hale-daily-audit.timer`
- **Script:** `OpsCenter/hale_daily_audit.py`
- **Output:** `hale_brief.md` (TRANSFORMATION section)
- **Log:** `logs/hale_audit.log`

## Metrics Updated

- `Decisions:` Count from `hale_decisions.md`
- `Open Tasks:` Count from `hale_state.json` (status != COMPLETE)
- `System Health:` From `hale_state.json`
- `Phase Status:` Hard-coded (updated manually as needed)

---

**Deployed:** 2026-04-12 22:20 MDT
**Status:** ✅ ACTIVE — First execution: SUCCESS
