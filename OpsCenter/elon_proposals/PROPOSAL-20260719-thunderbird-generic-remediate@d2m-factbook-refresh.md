## Summary

**Issue:** Service `thunderbird-generic-remediate@d2m-factbook-refresh` was auto-healing 10x/week, creating a useless remediation loop.

**Root Cause:** `d2m-factbook-refresh.service` fails because its headless Claude spawn fails (missing OAuth token). This is a **structural credential condition**, not a transient crash. Restarting the service fails identically every time, so the remediation cascade is pointless. A previous 2026-07-18 ELON proposal tried to fix this with a systemd drop-in, but that approach doesn't work — systemd's global OnFailure directive can't be overridden by per-unit drop-ins.

**Fix Applied:**
- Added `d2m-factbook-refresh.service` to `SELF_ALERTING_UNITS` in `scripts/generic_remediate.py` (same pattern as `hale-credential-check.service`)
- When the remediate script fires, it recognizes the unit is in the exclusion set and skips remediation entirely — no restart, no escalation
- Committed: `fix(remediate): exclude d2m-factbook-refresh from auto-remediation`

**Verification:**
- ✅ Code change in place (`git diff` shows the addition)
- ✅ Tested: manual invocation shows it's now skipped (log: `d2m-factbook-refresh.service: self-alerting unit ... -- skipping`)
- ✅ Proposal filed: `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260719-thunderbird-generic-remediate@d2m-factbook-refresh.md`

**Next event:** Mon 2026-07-20 01:30 MDT — timer will fire, service will fail cleanly, no remediation cascade. Zero mission impact (factbook is not consumed by any live workflow).

Thanks
