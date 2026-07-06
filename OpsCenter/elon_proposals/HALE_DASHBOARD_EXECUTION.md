# EXECUTED: hale-dashboard-refresh Timeout Fix
**Date:** 2026-07-06 16:08 MT
**Service:** `hale-dashboard-refresh.service`
**Status:** FIXED and verified live

---

## ROOT CAUSE

`core/ops/hale_dashboard_gen.py::svc_status()` made **2 systemctl (D-Bus) calls per
service** (`is-failed` + `show`) for 7 services in a serial `for` loop = **14 D-Bus
round trips per run**, each with an individual `timeout=3`. Under D-Bus/systemd
contention, cumulative wall time exceeded the unit's `TimeoutStartSec=30`, and
systemd SIGTERM'd the process (`status=15/TERM`, `Result: timeout`).

Journal evidence — repeated failures through 2026-07-06 12:12:38 MT:
```
hale-dashboard-refresh.service: Main process exited, code=killed, status=15/TERM
hale-dashboard-refresh.service: Failed with result 'timeout'.
```

A prior same-day fix attempt (12:16-12:19 MT) misdiagnosed this as a watchdog
oneshot-misclassification issue and proposed a watchdog-allowlist config change.
That proposal did not address the actual timeout mechanism and left a stub note
in this directory claiming the real fix was "already written" when it was not —
corrected by this execution.

## FIX APPLIED

**File:** `core/ops/hale_dashboard_gen.py`

1. Replaced per-service `is-failed` + `show` (2 calls) with a single `systemctl
   --user show <unit1> <unit2> ... -p Id,ActiveState,Result` call covering all
   7 services at once — `systemctl show` accepts multiple units natively and
   returns one property block per unit separated by a blank line. **14 D-Bus
   calls → 1.**
2. Added `load_service_statuses()` with belt-and-suspenders fallback: if the
   batched call fails/times out, falls back to per-service calls run in
   **parallel** via `ThreadPoolExecutor` (was: serial) so one hung unit can't
   stall the rest.
3. Batched call timeout: 45s (was 3s × 14 serial = worst case 42s, right at
   the edge of the 30s unit timeout). Fallback per-call timeout: 10s.
4. `svc_status()` removed; call site in `build_html()` now calls
   `load_service_statuses(SERVICES)` once.

**File:** `~/.config/systemd/user/hale-dashboard-refresh.service`

5. `TimeoutStartSec=30` → `TimeoutStartSec=300` (safety margin; not the primary
   fix — the primary fix is the 14→1 D-Bus call reduction above).

## TEST RESULTS (live system)

```
$ time .venv/bin/python3 core/ops/hale_dashboard_gen.py
[16:06:58] Dashboard written → /home/john/Thunderbird/output/hale_dashboard.html
real  0m0.069s   (was: routinely exceeding 30s and getting killed)
```

All 7 services resolved correctly via the single batched call (verified against
output HTML): nexus=RUNNING, d2m-scheduler=RUNNING, d2m-preflight=OK,
d2m-email-scanner=OK, d2m-correspondence-sync=OK, d2m-airline-monitor=OK,
thunderbird-backup-verify=OK.

```
$ systemctl --user daemon-reload
$ systemctl --user restart hale-dashboard-refresh.service
● Active: inactive (dead) ... Main PID ... status=0/SUCCESS, CPU: 68ms
```

Journal monitored live across 5 subsequent timer-triggered runs (16:06:38 →
16:08:03): every run starts and finishes within the same second. Zero
`Result: timeout`, zero `status=15/TERM` since the fix landed.

## EXPECTED GOING FORWARD

No more `TimeoutStartSec` failures — runtime dropped ~2 orders of magnitude
(30s+ risk → ~0.07s typical). The relaxed 300s `TimeoutStartSec` is now a
generous safety margin, not a load-bearing workaround.
