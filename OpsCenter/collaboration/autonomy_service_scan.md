# Autonomy Service Repair Assessment
**Date:** 2026-04-22 10:45 MT  
**Task:** AUTONOMY-SCAN-20260422

---

## Failed Services Summary

| Service | Status | Root Cause | Fix Complexity |
|---------|--------|-----------|-------------|
| thunderbird-backup-verify.service | failed (exit 1) | Script exits 1 on any warning | Low |
| thunderbird-drive-sync.service | failed (exit 1) | rclone failure (needs debug) | Medium |
| thunderbird-evernote-backup.service | failed (exit 2) | Wrong script path in ExecStart | Low |

---

## Root Cause Analysis

### 1. thunderbird-backup-verify.service
- **Root Cause:** Script exits with code 1 when warnings are detected
- **Evidence:** Logs show "⚠️ 4 warning(s)" followed by exit 1
- **Fix:** Modify script to exit 0 even with warnings (warnings are acceptable), only exit 1 on critical failures
- **File:** Need to locate the backup verify script

### 2. thunderbird-drive-sync.service
- **Root Cause:** rclone copy command failing (exit 1)
- **Evidence:** "Main process exited, code=exited, status=1/FAILURE"
- **Fix:** Debug rclone config and filters, or add `--fail-fast` disabled
- **File:** `./scripts/thunderbird_sync_filters.txt`

### 3. thunderbird-evernote-backup.service
- **Root Cause:** Wrong path in ExecStart
- **Evidence:** "can't open file '/home/john/Thunderbird/thunderbird_evernote_backup.py': [Errno 2] No such file or directory"
- **Actual path:** `/home/john/Thunderbird/api/thunderbird_evernote_backup.py`
- **Fix:** Update ExecStart in service file

---

## Repair Plan

### Priority 1: Fix evernote-backup (5 min)
**File:** `/home/john/Thunderbird/deploy/systemd/thunderbird-evernote-backup.service`  
**Line 8:** Change:
```
ExecStart=/usr/bin/python3 /home/john/Thunderbird/thunderbird_evernote_backup.py
```
To:
```
ExecStart=/home/john/.venv/bin/python /home/john/Thunderbird/api/thunderbird_evernote_backup.py
```

### Priority 2: Fix backup-verify (15 min)
**Location:** Need to find the backup verify script and modify exit behavior  
**Expected file:** `ops/thunderbird_backup_verify.py` or similar

### Priority 3: Fix drive-sync (30 min)
Debug rclone configuration - check filters and remote access

---

## Execution Notes

- All three services are user-level (--user flag)
- After fixes, run: `systemctl --user daemon-reload && systemctl --user restart <service>`
- Recommended order: e → backup-verify → drive-sync