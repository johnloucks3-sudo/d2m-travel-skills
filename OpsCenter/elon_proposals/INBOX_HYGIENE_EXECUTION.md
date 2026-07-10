# INBOX HYGIENE — EXECUTION RECORD (2026-07-06 16:10 MT)
Executed by: Claude Code (headless), per team-lead task, closing out ELON proposal chain
(PROPOSAL-20260613 / 20260702 / 20260705 / 20260706-inbox-hygiene.md — 4 cycles, zero prior executions)

## Correction to task brief
Task named `OpsCenter/inbox_hygiene.py` — file does not exist. Real file:
`/home/john/Thunderbird/core/email/inbox_hygiene.py`. Timer file is a symlink:
`~/.config/systemd/user/inbox-hygiene.timer` → `/home/john/Thunderbird/ops/inbox-hygiene.timer`
(edited the real target, not the symlink).

## Independent verification BEFORE fixing (ground-truth check)
Per Wing's own Obstacle-Routing & Verification doctrine, checked live journal/systemd state
before accepting the proposal's diagnosis at face value:

- `systemctl --user show inbox-hygiene.service --property=NRestarts,Result,ActiveState`
  → `NRestarts=0`, `Result=success`, `ActiveState=inactive` (clean dead state, oneshot done correctly)
- Last 24h journal: single `Starting`/`Finished` pair per cycle, no duplicate fires, spaced cleanly
  at the configured 10-min interval.
- **Confirmed real:** one actual failure today — `09:32:42 ... Main process exited, code=killed,
  status=15/TERM ... Failed with result 'timeout'.` This matches the proposal's claimed 09:30-09:40
  timeout window exactly.
- **NOT confirmed:** the proposal's claim of a "watchdog misclassifying oneshot exits as failures →
  double-runs, 7,599 phantom restarts." No watchdog in the codebase (`coo_watchdog.py` TIER1/TIER2
  lists) monitors `inbox-hygiene.service` at all, and current telemetry shows zero restarts. This
  looks like an artifact of the proposal being redrafted four times without a fresh telemetry check
  each time — flagging so it isn't re-litigated as if it were confirmed. No fix was written against
  this specific claim since no reproducing mechanism could be located.

## Changes made (3 surgical, all independently justified)

**1. Socket timeout — `core/email/inbox_hygiene.py`**
```diff
 import logging
+import socket
 import sys
 from datetime import datetime
 from pathlib import Path

+socket.setdefaulttimeout(30)
+
 from google.auth.transport.requests import Request
```
Directly addresses the confirmed 09:32 timeout/kill.

**2. Real exit-code signal (was previously always exit 0, no signal at all)**
```diff
     log.info(f"=== Done. {total} messages trashed. ===")
-    return total
+    return svc_jl, svc_d2m, total

 if __name__ == "__main__":
-    run()
+    _jl, _d2m, _total = run()
+    if _jl is None and _d2m is None:
+        log.error("Both accounts unavailable — exiting 1")
+        sys.exit(1)
+    sys.exit(0)
```
Closes a genuine observability gap (total-failure state was previously indistinguishable from
success at the systemd level) — independent of the disputed watchdog theory, this is correct
practice regardless.

**3. Timer frequency 10min → 30min — `ops/inbox-hygiene.timer`**
```diff
-Description=D2M Inbox Hygiene Timer — every 10 min
+Description=D2M Inbox Hygiene Timer — every 30 min
 OnBootSec=2min
-OnUnitActiveSec=10min
+OnUnitActiveSec=30min
```
Maintenance-only task; reduces Gmail API call volume 3x with no functional loss (label-sweep +
clutter rules don't need 6x/hour cadence).

## Test results
- `py_compile` → syntax OK
- Manual run: `python3 core/email/inbox_hygiene.py` → exit code 0, both accounts (johnloucks3 +
  d2mconcierge) reached successfully, 0 messages trashed (clean inbox state at test time)
- `systemctl --user daemon-reload` → OK
- `systemctl --user status inbox-hygiene.timer` → active, description now reads "every 30 min",
  `OnUnitActiveUSec=30min` confirmed via `systemctl show`, next trigger correctly 30min out

## Expected post-fix behavior
- No more silent hangs past 30s per Gmail API call (episodic timeout closed)
- Service correctly reports `Result=failed`/exit 1 only in the genuine both-accounts-down case;
  partial-success (one account down) still reports overall success, matching current sweep
  semantics (best-effort per account)
- 3x fewer runs/day (144 → 48), same functional coverage
- The "watchdog double-run" claim remains open and unresolved — if it resurfaces, it needs a named,
  located mechanism before another fix cycle is spent on it
