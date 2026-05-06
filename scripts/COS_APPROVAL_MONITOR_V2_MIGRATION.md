# COS Approval Monitor v2 — Migration & Deployment Guide

**Version:** 2.0  
**Date:** 2026-05-03  
**Status:** Production-Ready  

---

## EXECUTIVE SUMMARY

COS Approval Monitor v2 is a complete redesign that adds:

✅ **Multi-inbox support** — Both d2mconcierge and johnloucks3  
✅ **Real MCP Gmail integration** — Actual email searches, not file-based fallback  
✅ **Flexible approval detection** — Recognize "approve/approved/yes/proceed" patterns  
✅ **COS/COO/Hale directive detection** — Auto-detect and log directives  
✅ **Tasking detection** — Recognize assignment patterns  
✅ **State tracking** — Avoid duplicate processing  
✅ **Mission board integration** — Log directives and tasks automatically  
✅ **Production-ready code** — Full error handling, logging, and audit trail  

---

## ARCHITECTURE CHANGES

### v1 (Current)
```
File-based approval scanning
  ↓
johnloucks3 only
  ↓
Pattern matching on local files
  ↓
Silent failures if MCP unavailable
  ↓
No deduplication
```

### v2 (New)
```
MCP Gmail multi-inbox scanning (d2mconcierge + johnloucks3)
  ↓
Real email search via Claude subprocess
  ↓
Full thread content analysis
  ↓
Pattern detection: approvals, directives, tasking
  ↓
State tracking with deduplication
  ↓
Automatic mission board logging
  ↓
Full audit trail with error recovery
```

---

## MIGRATION STEPS

### PHASE 1: Pre-Deployment Verification (5 min)

**Step 1.1: Verify MCP Gmail tools are available**
```bash
# Check if Claude can call MCP Gmail tools
cd /home/john/Thunderbird
python3 -c "import subprocess; print('Claude binary accessible')"
which /home/john/.local/bin/claude || echo "Claude not found"
```

**Step 1.2: Check existing v1 state**
```bash
ls -la ~/.thunderbird_approvals/
# Should show: monitor.log, draft_*.json files
```

**Step 1.3: Backup v1 state**
```bash
mkdir -p ~/.thunderbird_approvals/v1_backup
cp ~/.thunderbird_approvals/*.json ~/.thunderbird_approvals/v1_backup/ 2>/dev/null || true
cp ~/.thunderbird_approvals/monitor.log ~/.thunderbird_approvals/v1_backup/ 2>/dev/null || true
echo "v1 state backed up"
```

### PHASE 2: Deploy v2 Script (2 min)

**Step 2.1: Verify v2 script exists**
```bash
ls -la /home/john/Thunderbird/scripts/cos_approval_monitor_v2.py
# File should be ~400 lines
```

**Step 2.2: Make v2 executable**
```bash
chmod +x /home/john/Thunderbird/scripts/cos_approval_monitor_v2.py
```

**Step 2.3: Verify v2 imports work**
```bash
python3 -c "from pathlib import Path; import json; import logging; print('✓ Imports OK')"
```

### PHASE 3: Test v2 in Dry-Run Mode (5 min)

**Step 3.1: Run v2 in dry-run + scan-once mode**
```bash
cd /home/john/Thunderbird/scripts
python3 cos_approval_monitor_v2.py --scan-once --dry-run
```

**Expected output:**
```
2026-05-03 10:30:45 [INFO] COS Approval Monitor v2 initialized (poll_interval=60s, dry_run=True)
2026-05-03 10:30:45 [INFO] *** DRY RUN MODE - No actions will be taken ***
2026-05-03 10:30:45 [INFO] Running single approval scan...
2026-05-03 10:30:46 [DEBUG] Scanning d2mconcierge...
2026-05-03 10:30:47 [DEBUG] Scanning johnloucks3...
2026-05-03 10:30:48 [INFO] Found 0 total detections across both inboxes
```

**Step 3.2: Check log file**
```bash
tail -20 ~/.thunderbird_approvals/monitor_v2.log
# Should show all scan activity
```

**Step 3.3: Verify state file created**
```bash
ls -la ~/.thunderbird_approvals/detection_state.json
# File should exist (empty JSON object on first run)
```

### PHASE 4: Parallel Testing (10 min)

**Step 4.1: Start v2 in daemon mode (low priority terminal)**
```bash
cd /home/john/Thunderbird/scripts
python3 cos_approval_monitor_v2.py --daemon --poll-interval 30
# Will run continuously, check logs
```

**Step 4.2: Send test approval email**

Send email to **d2mconcierge@gmail.com** with:
- **Subject:** `[DRAFT] Test Approval`
- **Body:** `approve`

**Step 4.3: Monitor v2 for detection**
```bash
tail -f ~/.thunderbird_approvals/monitor_v2.log | grep "Approval detected"
# Should appear within 30 seconds
```

**Step 4.4: Check state was recorded**
```bash
cat ~/.thunderbird_approvals/detection_state.json | jq .
# Should show one processed detection
```

**Step 4.5: Stop v2 (Ctrl+C)**
```bash
# Graceful shutdown logs message
```

### PHASE 5: Disable v1, Enable v2 (5 min)

**Step 5.1: Stop v1 service**
```bash
sudo systemctl stop cos-approval-monitor.service
sudo systemctl disable cos-approval-monitor.service
echo "✓ v1 service disabled"
```

**Step 5.2: Verify v1 is stopped**
```bash
ps aux | grep "cos_approval_monitor.py" | grep -v grep || echo "✓ No v1 processes"
```

**Step 5.3: Create v2 systemd service**

Create `/etc/systemd/user/cos-approval-monitor-v2.service`:

```ini
[Unit]
Description=COS Approval Monitor v2
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/home/john/.local/bin/python3 /home/john/Thunderbird/scripts/cos_approval_monitor_v2.py --daemon --poll-interval 60
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cos-approval-monitor-v2

[Install]
WantedBy=default.target
```

**Step 5.4: Enable and start v2 service**
```bash
sudo systemctl daemon-reload
sudo systemctl enable cos-approval-monitor-v2.service
sudo systemctl start cos-approval-monitor-v2.service
echo "✓ v2 service started"
```

**Step 5.5: Verify v2 is running**
```bash
ps aux | grep "cos_approval_monitor_v2.py" | grep -v grep || echo "✗ v2 not running"
systemctl status cos-approval-monitor-v2.service --no-pager
```

### PHASE 6: Validation (10 min)

**Step 6.1: Check v2 logs**
```bash
journalctl -u cos-approval-monitor-v2.service -n 50 --no-pager
# Should show active polling
```

**Step 6.2: Send real approval to johnloucks3**

Send email TO **johnloucks3@gmail.com** with:
- **From:** d2mconcierge
- **Subject:** `[DRAFT] Real Test`
- **Body:** `yes, please send this`

**Step 6.3: Monitor for detection**
```bash
tail -f ~/.thunderbird_approvals/monitor_v2.log | grep "yes"
# Should detect within 60 seconds
```

**Step 6.4: Verify state updated**
```bash
cat ~/.thunderbird_approvals/detection_state.json | jq '.[] | .approval_type'
# Should include "yes" detection
```

**Step 6.5: Check mission board log**
```bash
grep -i "directive\|task" ~/.thunderbird_approvals/monitor_v2.log
# Should show any directives/tasking logged
```

---

## TESTING CHECKLIST

Use this checklist to verify v2 is working correctly:

- [ ] **Multi-inbox scan** — Scans both d2mconcierge and johnloucks3
- [ ] **Approval detection** — Detects "approve" in d2mconcierge
- [ ] **Approval detection (yes)** — Detects "yes" in johnloucks3
- [ ] **Deduplication** — Doesn't process same approval twice
- [ ] **State persistence** — State file survives daemon restart
- [ ] **Error recovery** — Daemon continues after errors
- [ ] **Directive detection** — Detects "COS:" prefix
- [ ] **Tasking detection** — Detects "Assign X to Y" patterns
- [ ] **Log quality** — All actions logged with timestamps
- [ ] **Service reliability** — Service stays running 24h+

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] V1 state backed up to `~/.thunderbird_approvals/v1_backup/`
- [ ] V2 script tested in dry-run mode
- [ ] V2 script tested with real test emails
- [ ] MCP Gmail tools verified working

### Deployment
- [ ] V1 service disabled and stopped
- [ ] V2 systemd service created and enabled
- [ ] V2 service started successfully
- [ ] Service logs checked for errors
- [ ] v2 process visible in `ps aux`

### Post-Deployment
- [ ] Real approval email tested and detected
- [ ] State file created and populated
- [ ] Log file shows continuous polling
- [ ] Mission board logs appear for directives
- [ ] No errors in systemd journal

---

## ROLLBACK PROCEDURE

If v2 has issues, rollback to v1:

```bash
# 1. Stop v2
sudo systemctl stop cos-approval-monitor-v2.service
sudo systemctl disable cos-approval-monitor-v2.service

# 2. Restore v1 state (optional)
cp ~/.thunderbird_approvals/v1_backup/* ~/.thunderbird_approvals/ 2>/dev/null || true

# 3. Restart v1
sudo systemctl enable cos-approval-monitor.service
sudo systemctl start cos-approval-monitor.service

# 4. Verify v1 running
systemctl status cos-approval-monitor.service --no-pager
```

---

## MONITORING & TROUBLESHOOTING

### Check Service Status
```bash
# Real-time logs
journalctl -u cos-approval-monitor-v2.service -f

# Last 50 lines
journalctl -u cos-approval-monitor-v2.service -n 50 --no-pager

# Errors only
journalctl -u cos-approval-monitor-v2.service -p err --no-pager
```

### Check State File
```bash
# View all processed detections
cat ~/.thunderbird_approvals/detection_state.json | jq .

# Count detections by type
cat ~/.thunderbird_approvals/detection_state.json | jq '[.[] | .approval_type] | group_by(.) | map({type: .[0], count: length})'
```

### Common Issues

**Issue: No detections found**
- Check d2mconcierge and johnloucks3 have emails
- Verify Gmail OAuth token is fresh
- Check logs: `journalctl -u cos-approval-monitor-v2.service -p err`

**Issue: Duplicate processing**
- Check state file not corrupted: `jq . ~/.thunderbird_approvals/detection_state.json`
- Clear state and restart: `rm ~/.thunderbird_approvals/detection_state.json`

**Issue: Service not starting**
- Check syntax: `sudo systemd-analyze verify cos-approval-monitor-v2.service`
- Check logs: `journalctl -u cos-approval-monitor-v2.service -p err -n 50`

---

## FEATURE COMPARISON

| Feature | v1 | v2 |
|---------|----|----|
| Multi-inbox support | ❌ | ✅ |
| Real Gmail integration | ⚠️ (planned) | ✅ |
| Approval detection | ✅ | ✅ |
| Flexible keywords | ⚠️ (limited) | ✅ |
| Directive detection | ❌ | ✅ |
| Tasking detection | ❌ | ✅ |
| Deduplication | ❌ | ✅ |
| Mission board logging | ❌ | ✅ |
| Error recovery | ⚠️ | ✅ |
| Full audit trail | ❌ | ✅ |

---

## SUPPORT & ESCALATION

**Normal operation questions:**
- Check logs: `journalctl -u cos-approval-monitor-v2.service`
- Review state: `cat ~/.thunderbird_approvals/detection_state.json | jq .`

**Issues or feature requests:**
- File issue in Thunderbird project
- Include: logs, state file, error message

**Emergency rollback:**
- Run rollback procedure above
- Notify COS of issue

---

*— Thunderbird Operations Team*
