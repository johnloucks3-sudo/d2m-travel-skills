# Standing Order — GUI Daemons Disabled on Headless Server
**Effective:** 2026-07-08  
**Authority:** ELON A12  
**Scope:** Thunderbird Wing infrastructure  

---

## POLICY

Thunderbird is a headless automation server. It runs no display manager, no X server, no KDE/Plasma GUI environment, and no user login sessions. GUI-related system services are inherently misaligned with this environment and will crash repeatedly as they attempt to handle display events that don't exist.

**All KDE/Plasma user-level GUI daemons are masked and excluded from all watchdog monitoring.**

---

## SERVICES MASKED

| Service | Reason | Masked Date |
|---------|--------|-------------|
| `drkonqi-coredump-launcher@*` | KDE crash handler; generates core dump alerts on non-existent GUI | 2026-07-08 |
| `kded6*` (reserved) | KDE daemon collection; not needed on headless | On-demand if seen |
| `plasmashell*` (reserved) | Plasma shell GUI; not present on headless | On-demand if seen |
| `kglobalshortcuts*` (reserved) | KDE shortcut handler; GUI-only | On-demand if seen |

---

## HOW TO APPLY

**When a new GUI service is discovered crashing:**

1. Identify the service: `systemctl --user status --no-pager` or `journalctl --user`
2. Determine if it's a KDE/Plasma service (look for `kded`, `plasmashell`, `kglobalshortcuts`, `drkonqi`, `plasma-*`, `kwin_*`)
3. Mask it: `systemctl --user mask <service-name>`
4. Remove from watchdog if it's explicitly listed in any config (rare; masking alone stops restarts)
5. Commit: `git add -A && git commit -m "chore: mask <service> GUI daemon"`

---

## VERIFICATION

After masking a service, verify it stays down:

```bash
# Should show "masked"
systemctl --user is-enabled <service-name>

# Should show no activity for 7+ days
journalctl --user -u <service-name> --since="7 days ago"

# Watchdog logs should show zero restarts
grep "<service-name>" /home/john/Thunderbird/logs/coo_watchdog.log
```

---

## RATIONALE

- **Eliminates false alarms:** Watchdog sees service down, tries to restart, service crashes again immediately. Masking stops this loop.
- **Reduces noise:** Watchdog logs are cleaner; real infrastructure issues surface clearly.
- **Correct semantics:** A masked service signals "should not run" — the OS respects this and won't restart it.
- **No side effects:** Masking affects only the specific service; other infrastructure is unaffected.

---

## RELATED

- PROPOSAL-20260708-drkonqi-recurrence.md (root cause analysis, auto-heal data)
- `OpsCenter/thunderbird_coo_watchdog.py` (watchdog implementation)

---

*Standing Order · Thunderbird Wing · Dreams2Memories Travel, LLC*
