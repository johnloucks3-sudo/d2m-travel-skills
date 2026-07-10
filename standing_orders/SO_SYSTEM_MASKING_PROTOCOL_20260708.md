# Standing Order — System Masking Protocol
**Effective:** 2026-07-08  
**Owner:** Sterling (A7) audit; Hale execution  
**Classification:** Infrastructure / System Hygiene  

---

## Service Masking: drkonqi GUI Crash Handler

**Services masked (links to /dev/null):**
- `drkonqi-coredump-launcher@.service` (template)
- `drkonqi-coredump-handler.service`
- `drkonqi.service`

**Rationale:**  
yoga is a headless server system (100.69.222.124, no X11 display, no desktop environment). drkonqi is a KDE Plasma GUI crash handler designed for interactive crash debugging on workstations. It has zero operational value on a headless system and was generating a recurring 5x/7d auto-heal cycle via the COO watchdog.

Root cause: Some process (likely stray SSH X11 tunneling or RDP/VNC client) attempts GUI operations, fails without a display, drkonqi spawns trying to report a crash it cannot debug, fails, watchdog restarts. Masking prevents the service from ever spawning.

**Implementation date:** 2026-07-08 17:32 MDT (ELON proposal PROPOSAL-20260708-drkonqi-coredump-launcher@0-4097-1823_36988-0.md)

**Verification metric:**  
- **Target:** Zero drkonqi restarts in the 7-day window 2026-07-08 through 2026-07-15
- **Baseline:** 5 restarts observed in the prior 7 days (2026-07-01 through 2026-07-08)
- **Success criteria:** Next heartbeat_scan (scheduled 2026-07-15) shows zero new drkonqi events
- **Fallback:** If upstream crash pattern emerges (different symptom), escalate to root-cause analysis on the actual crashing process

**Reversibility:**  
Full reversal is available if needed:
```bash
systemctl --user unmask drkonqi-coredump-launcher@.service drkonqi-coredump-handler.service drkonqi.service
systemctl --user daemon-reload
```

---

**Applied by:** Hale (autonomous under SO-2026-05-04 Weapons Free)  
**Audit:** Sterling to verify zero recurrences in weekly Baldrige sweep (beginning 2026-07-15)
