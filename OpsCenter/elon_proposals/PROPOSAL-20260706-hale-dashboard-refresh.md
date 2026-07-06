**CORRECTION (2026-07-06 16:09 MT):** This file previously (12:19 MT) contained a
stub claiming a "comprehensive 8.4KB document" with the D-Bus fix already existed
at this path. That claim was false — this file was 5 lines, and `hale_dashboard_gen.py`
still had the original 14-serial-call code. The stub was never verified against
the actual file contents before being asserted as done.

**Actual fix executed 2026-07-06 16:08 MT — see `HALE_DASHBOARD_EXECUTION.md`
in this directory** for root cause, code diff, and live verification
(0.069s runtime, 5 clean consecutive timer runs, zero timeouts since).

The earlier (12:16 MT) watchdog-misclassification theory in this file's git
history was also superseded — it treated the failure as a monitoring/allowlist
problem rather than the actual `TimeoutStartSec` kill it was.
