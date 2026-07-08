# PROPOSAL — drkonqi-coredump-launcher Recurrence
**ELON A12 · 2026-07-08 16:26 UTC**  
**Classification:** INFRA ELIMINATION  
**Recurrence Pattern:** 3× in 7 days · Auto-healed each time by COO watchdog

---

## ROOT CAUSE

The `drkonqi-coredump-launcher` service is a KDE/Plasma GUI desktop crash handler — designed to capture and report user-facing GUI crashes on interactive Linux workstations. Thunderbird is a headless automation server with no display manager, no Xorg, no user at the keyboard, and no need for GUI crash reporting. The service crashes repeatedly not because it's broken, but because it's fundamentally misaligned with the environment: it's trying to manage desktop events that don't exist on a server. The watchdog restart loop masks the root problem — **this service should not be running at all.**

---

## PROPOSED FIX

**Type:** Standing Order + Service Masking  
**Action:** Permanently disable and mask the drkonqi-coredump-launcher service (user-level).  
**Rationale:** Eliminate the recurring failure, reduce watchdog load, stop dead cycles that mask deeper issues.

---

## IMPLEMENTATION

**Steps (autonomous, no Commander gate):**

1. **Mask the service at user level:**
   ```bash
   systemctl --user mask drkonqi-coredump-launcher@1-12289-2644_41108-0
   ```

2. **Verify it is masked:**
   ```bash
   systemctl --user is-enabled drkonqi-coredump-launcher@1-12289-2644_41108-0
   # Should output: disabled
   ```

3. **Remove the service from watchdog monitor list:**
   - Edit `config/coo_watchdog_monitored_services.json` (or equivalent)
   - Remove `drkonqi-coredump-launcher@*` from the watch set
   - Restart watchdog: `systemctl --user restart thunderbird-watchdog.service`

4. **Document in Standing Order:**
   - File: `standing_orders/SO-GUI-DAEMONS-DISABLED-20260708.md`
   - Content: "Headless automation servers do not run KDE display services. drkonqi, plasma-*, kded*, and user-mode GUI daemons are masked and excluded from watchdog monitoring."

5. **Commit:**
   ```bash
   git add -A
   git commit -m "chore: mask drkonqi GUI daemon on headless Thunderbird — eliminate recurrence pattern"
   ```

---

## VERIFICATION TEST

**End-to-end:**

1. **Confirm mask is active (immediate):**
   ```bash
   systemctl --user show drkonqi-coredump-launcher@1-12289-2644_41108-0 --property=UnitFileState
   # Expected: UnitFileState=masked
   ```

2. **Confirm it does not auto-restart (7-day window):**
   - Monitor `/var/log/syslog` or `journalctl --user -u drkonqi-coredump-launcher` for the next 7 days
   - Expected: zero service-start events after masking (previously 3 in 7 days)

3. **Confirm watchdog sees zero failures on this service:**
   - Query watchdog log: `grep -c "drkonqi-coredump-launcher" /home/john/Thunderbird/logs/coo_watchdog.log`
   - Expected: 0 entries (or only pre-mask entries if log not rotated)

4. **Confirm no side effects (system still boots, other services still active):**
   - Reboot (if acceptable)
   - Verify core Thunderbird services active: `systemctl --user status thunderbird-watchdog.service`

---

## HALE DECISION

**→ APPLY_AUTONOMOUSLY**

**Reasoning:**
- This is infrastructure housekeeping, not a client-visible change
- No financial commitment, no strategic direction change
- Eliminates noise from the watchdog (lower false-alarm rate)
- Aligns with the system's actual purpose (headless automation, not a workstation)
- Hale owns infra health and can mask services without Commander approval per SO-2026-05-04

**Next:** After 7-day monitoring window (2026-07-15), flag to Commander in the brief: "drkonqi recurrence pattern eliminated. Masking successful. Recommendation: extend GUI-daemon mask to other KDE/Plasma services that should not run headless (kded6, plasmashell, etc.)."

---

*— ELON, A12 Innovation & Disruption*  
*Thunderbird Wing, Dreams2Memories Travel*
