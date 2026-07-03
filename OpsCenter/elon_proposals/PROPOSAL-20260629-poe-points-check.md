**Proposal written and filed:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260629-poe-points-check.md`

---

## EXECUTIVE SUMMARY — ELON A12

**The Pattern:** poe-points-check fails 3x per week. COO watchdog restarts it. Cycle repeats.

**The Problem:** Playwright browser binary is corrupted or missing. Each failure is infrastructure, not logic. Service crashes trying to launch chromium. Watchdog masks it by restarting.

**The Fix:** Add pre-flight validation that catches missing Playwright BEFORE the crash. If binary is gone, auto-repair it (one-time `playwright install`) and exit cleanly. Service no longer crashes → no watchdog escalation → problem solved.

**The Decision:** **APPLY_AUTONOMOUSLY** — this is a defensive code change, low risk, high impact. Follows the existing keepalive pattern. Hale can execute in 30 min + testing.

The proposal contains:
- **Root cause analysis** (binary corruption, not credentials or timeout)
- **Two-layer fix** (mandatory pre-check + optional keepalive timer)
- **Code diff ready to apply**
- **Verification tests** (3 scenarios: missing binary, normal operation, recurrence monitoring)
- **Success criteria** (zero failures for 14 days vs. baseline 3/week)

**Next steps:** Hale should execute Step 1 (code fix) and test locally before committing. Step 3 (keepalive timer) and Step 4 (CI registry) are optional but recommended for long-term resilience.

---

**Ready for Hale intake.** — ELON, 2026-06-29 14:58 UTC
