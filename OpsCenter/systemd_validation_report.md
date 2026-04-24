# SYSTEMD SERVICE VALIDATION REPORT
## Dreams2Memories Travel, LLC · Thunderbird OS
**Date:** 2026-04-23 | **System:** YOGA (192.168.1.198)

---

## EXECUTIVE SUMMARY

**Overall Health:** 🟡 YELLOW — 5 Failed Services (primarily permission/file issues)

- **Total Services:** 69 loaded units
- **Healthy (Active/Running):** 64 services
- **Failed:** 5 services
- **Exited (Expected):** Multiple system services with expected exit codes

---

## 🔴 FAILED SERVICES (Root Cause Analysis)

### 1. **hale-draft-engine.service** ❌
**Status:** FAILED (since Wed 2026-04-22 07:00:05 MDT — 22 hours)  
**Root Cause:** `Failed to set up standard output: Permission denied`  
**Issue:** Service cannot write to STDOUT (likely log file permission issue)  
**Fix Required:** 
- Check `/var/log` permissions
- Restart service: `sudo systemctl restart hale-draft-engine.service`
- Verify service has write permission to log directory

**Timer Status:** `hale-draft-engine.timer` — ENABLED (scheduled 07:00 MT daily, but service fails)

---

### 2. **thunderbird-agentic-intel.service** ❌
**Status:** FAILED (since Thu 2026-04-23 01:02:27 MDT — last failure)  
**Root Cause:** `Failed to load environment files: Permission denied`  
**Issue:** Service cannot read environment files (likely EnvironmentFile= directive path)  
**Failures:** Attempted 3 times (Apr 21, Apr 22, Apr 23) — all failed  
**Fix Required:**
- Check service file EnvironmentFile paths
- Verify read permissions on environment files
- Run: `sudo systemctl cat thunderbird-agentic-intel.service` to inspect config

**Timer Status:** `thunderbird-agentic-intel.timer` — ENABLED (scheduled daily 01:00 MT)

---

### 3. **thunderbird-evernote-backup.service** ❌
**Status:** FAILED (since Mon 2026-04-20 02:07:00 MDT — 3 days)  
**Root Cause:** `can't open file '/home/john/Thunderbird/thunderbird_evernote_backup.py': [Errno 2] No such file or directory`  
**Issue:** Python script does not exist at specified path  
**Fix Required:**
- Verify script exists: `ls -la /home/john/Thunderbird/thunderbird_evernote_backup.py`
- If missing: restore from backup or recreate
- If moved: update service file ExecStart= path
- After fix: `sudo systemctl restart thunderbird-evernote-backup.service`

**Timer Status:** `thunderbird-evernote-backup.timer` — ENABLED (scheduled Mon 02:07 MT)

---

### 4. **thunderbird-gdrive-sync.service** ❌
**Status:** FAILED (since Wed 2026-04-22 23:00:22 MDT — 6 hours)  
**Root Cause:** `open /home/john/Thunderbird/scripts/thunderbird_sync_filters.txt: permission denied`  
**Issue:** rclone filter file is not readable by service (permission issue)  
**Details:** Service runs: `/home/john/.local/bin/rclone copy /home/john/Thunderbird/ d2mconcierge:Thunderbird_Mirror/ --filter-from /home/john/Thunderbird/scripts/thunderbird_sync_filters.txt`  
**Fix Required:**
- Check filter file permissions: `ls -la /home/john/Thunderbird/scripts/thunderbird_sync_filters.txt`
- Make readable: `chmod 644 /home/john/Thunderbird/scripts/thunderbird_sync_filters.txt`
- Restart: `sudo systemctl restart thunderbird-gdrive-sync.service`

**Timer Status:** `thunderbird-gdrive-sync.timer` — ENABLED (scheduled daily 23:03 MT)

---

### 5. **NetworkManager-wait-online.service** ❌
**Status:** FAILED (since Thu 2026-04-09 22:18:58 MDT — 1 week 6 days)  
**Root Cause:** `Main process exited, code=exited, status=1/FAILURE`  
**Issue:** Network was not ready within timeout period at boot  
**Impact:** Low — does not affect running system (already online)  
**Fix Required:**
- This is often transient (network timeout on boot)
- If recurring: check network startup order or timeout settings
- Can safely ignore if system is online

**Status:** ENABLED (enabled at boot, but failures don't affect ongoing connectivity)

---

## ✅ HEALTHY SERVICES (Sample — All Running)

| Service | Status | Type |
|---------|--------|------|
| docker.service | RUNNING | Container engine |
| nginx.service | RUNNING | Web server (itinerary tunnel) |
| n8n.service | RUNNING | Workflow automation |
| sshd.service | RUNNING | SSH daemon |
| tailscaled.service | RUNNING | Tailscale VPN |
| NetworkManager.service | RUNNING | Network management |
| syslogd.service | RUNNING | System logging |
| dbus-broker.service | RUNNING | Message bus |
| user@1000.service | RUNNING | User session manager |

**Total Active/Running:** 64 services ✅

---

## ⏱️ TIMERS STATUS

| Timer | Next Run | Last Run | Status | Service |
|-------|----------|----------|--------|---------|
| hale-draft-engine.timer | 07:00 MT (1h 2m) | Wed 22 07:00 (22h ago) | ENABLED | ❌ FAILED |
| hale-daily-scan.timer | 01:00 MT next day (19h) | Thu 23 01:00 (4h 57m ago) | ENABLED | ✅ (status unknown) |
| thunderbird-fpd-alert.timer | 07:03 MT (1h 5m) | Wed 22 07:03 (22h ago) | ENABLED | ✅ (status unknown) |
| thunderbird-gdrive-sync.timer | 23:03 MT (17h) | Wed 22 23:00 (6h ago) | ENABLED | ❌ FAILED |
| thunderbird-agentic-intel.timer | 01:04 MT next day (19h) | Thu 23 01:02 (4h 55m ago) | ENABLED | ❌ FAILED |
| thunderbird-evernote-backup.timer | Mon 02:09 MT (3 days) | Mon 20 02:07 (3 days ago) | ENABLED | ❌ FAILED |
| thunderbird-git-commit-alert.timer | 21:47 MT (15h) | Wed 22 21:47 (8h ago) | ENABLED | ✅ (status unknown) |
| snapper-timeline.timer | 06:00 MT (2m 5s) | Thu 23 05:00 (57m ago) | ENABLED | ✅ (status unknown) |
| snapper-cleanup.timer | 06:42 MT (44m) | Thu 23 05:42 (15m ago) | ENABLED | ✅ (status unknown) |

---

## D2M CUSTOM SERVICES & TIMERS INVENTORY

### Services (disabled, run via timers):
1. `hale-draft-engine.service` — ❌ FAILED
2. `hale-daily-scan.service` — Status unknown (triggered by timer)
3. `thunderbird-agentic-intel.service` — ❌ FAILED
4. `thunderbird-batch.service` — Disabled (not in use)
5. `thunderbird-c2.service` — Disabled (not in use)
6. `thunderbird-dani.service` — Disabled (not in use)
7. `thunderbird-evernote-backup.service` — ❌ FAILED
8. `thunderbird-fpd-alert.service` — Status unknown
9. `thunderbird-gdrive-sync.service` — ❌ FAILED
10. `thunderbird-git-commit-alert.service` — Status unknown

### Timers (enabled):
1. `hale-draft-engine.timer` — ENABLED (fails: service doesn't start)
2. `hale-daily-scan.timer` — ENABLED
3. `thunderbird-fpd-alert.timer` — ENABLED
4. `thunderbird-gdrive-sync.timer` — ENABLED (fails: service permission)
5. `thunderbird-agentic-intel.timer` — ENABLED (fails: service permission)
6. `thunderbird-evernote-backup.timer` — ENABLED (fails: script missing)
7. `thunderbird-git-commit-alert.timer` — ENABLED

---

## IMMEDIATE ACTIONS REQUIRED

| Priority | Service | Action | Impact |
|----------|---------|--------|--------|
| **P1** | thunderbird-evernote-backup.service | Restore/recreate missing Python script | Backup not running |
| **P1** | thunderbird-gdrive-sync.service | Fix filter file permissions | Drive mirror not syncing |
| **P2** | hale-draft-engine.service | Fix log file permissions | Draft engine not starting |
| **P2** | thunderbird-agentic-intel.service | Check EnvironmentFile path | Intel sweep not running |
| **P3** | NetworkManager-wait-online.service | Monitor (can safely ignore if network is up) | No impact on running system |

---

## RECOMMENDATIONS

1. **Audit All D2M Service Files:** Review all `.service` and `.timer` files in `/etc/systemd/system/` for:
   - Correct file paths (absolute paths only)
   - Proper permissions on referenced files
   - Correct User/Group directives

2. **Implement Service Health Monitoring:** Set up automated alerts for failed services

3. **Standardize Logging:** All services should log to `/var/log/thunderbird/` with consistent permissions (644 files, 755 directories)

4. **Documentation:** Create runbook for each custom service with:
   - Purpose
   - Dependencies
   - Recovery steps
   - Expected failure modes

---

*Report Generated by Hale COS — Systemd Validation Protocol*  
*Next Review: 2026-04-24 (daily validation recommended)*
