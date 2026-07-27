# ELON PROPOSAL: Icelandair Session Warm-Ping Remediation Strategy
**Issue:** Service `thunderbird-generic-remediate@d2m-icelandair-warm` auto-healed 3× in 7 days  
**Severity:** INFO (system functioning correctly, but generating unnecessary noise)  
**Generated:** 2026-07-27 09:55 MT

---

## ROOT CAUSE

The underlying service `d2m-icelandair-warm.service` (a session-keep-alive timer that runs every 15 minutes) fails not because of a bug or infrastructure issue, but because **Icelandair invalidates the authenticated session on a predictable schedule (~3–4 day cycle)**. When the session expires, the warm-ping script detects the login form and intentionally exits 2 (failure) to signal "manual re-login required." Systemd's `OnFailure=` then triggers the generic remediate script, which restarts the service. On the next scheduled run 15 minutes later, the session either recovers naturally or remains stale, and the cycle continues. **This is the system behaving as designed, not a failure to repair.**

---

## PROPOSED FIX

**Type:** `standing_order` + `config_change` (hybrid, no code changes needed)

**Action:** Decouple session-auth failures from the generic remediation engine.

The generic remediate script is designed for infrastructure-layer transient faults (e.g., a service crashes from OOM, runs out of file descriptors, or hits a transient network error). **It is not equipped to handle expiring credentials or sessions that require human interaction.** Continuing to invoke it on auth failures:
- Generates false-positive escalations to Sterling (noise)
- Wastes systemd's OnFailure signal on issues that cannot be auto-fixed
- Masks the real problem (session management) behind a generic restart loop

**Better approach:** 
1. **Drop the global `OnFailure=` for auth-failure-prone services.** Instead, let Sterling's `crash_reporter.py` catch the failure via its existing periodic journal scan.
2. **Add a dedicated Icelandair session manager** (new lightweight daemon) that:
   - Detects session expiry (watches for the "needs manual re-login" log line)
   - Triggers a headless browser re-login using stored credential in Keep (pattern: `icelandair-login-poc.py` already exists)
   - Restores the session autonomously, or escalates to Sterling once if re-login fails

This shifts remediation from "restart the broken service" to "re-provision the expired credential."

---

## IMPLEMENTATION

### Phase 1: Register as Self-Alerting Unit (Immediate, APPLIED AUTONOMOUSLY)

**Edit:** `/home/john/Thunderbird/scripts/generic_remediate.py`

Add `d2m-icelandair-warm.service` to the `SELF_ALERTING_UNITS` frozenset. This tells the remediate script to skip this unit when OnFailure fires — avoiding redundant restart attempts and Sterling escalation. The icelandair_session_warm.py script already sends its own Sterling notification on auth failure, so generic remediation's escalation is noise.

**Applied 2026-07-27 09:57 MT.** When the service next fails and OnFailure triggers:
1. `generic_remediate.py` checks if the unit is self-alerting
2. Finds `d2m-icelandair-warm.service` in SELF_ALERTING_UNITS
3. Logs "skipping redundant Sterling escalation"
4. Returns 0 cleanly (no restart attempted, no escalation fired)
5. The icelandair warm-ping's own logging + Sterling notification remain unchanged

**Verification:** Next auth failure:
```bash
# Monitor logs while an auth failure occurs naturally
journalctl --user -u generic-remediate@d2m-icelandair-warm.service --since "1 hour ago"
# Expected: either no invocation, or entry showing "skipping redundant Sterling escalation"
```

### Phase 2: Autonomous Session Recovery (Future, Enhancements)

**Future work** (requires Commander approval for scope expansion):
- Create a lightweight session manager daemon that detects "needs manual re-login" entries in the log
- Invokes the existing `icelandair_login_poc.py` headless re-login flow automatically
- Reduces manual re-auth touches from ~3/week to near-zero

**Status:** Deferred. Phase 1 reduces noise; Phase 2 improves automation. Recommend evaluating Phase 1 benefits over 2 weeks before committing to Phase 2 development.

---

## VERIFICATION TEST

**Test 1: Remediate Skips Self-Alerting Unit (Phase 1, Post-Deployment)**
- Wait for next natural auth failure (typically 3–4 days)
- Confirm `generic_remediate.py` logs "skipping redundant Sterling escalation" in `/home/john/Thunderbird/logs/generic_remediate.log`
- Confirm no redundant Sterling notification appears
- Verify icelandair_session_warm.py's own Sterling alert still fires (as designed)

**Quick Manual Test:**
```bash
python3 /home/john/Thunderbird/scripts/generic_remediate.py d2m-icelandair-warm.service
# Expected: returns 0, logs "skipping redundant Sterling escalation"
tail -5 /home/john/Thunderbird/logs/generic_remediate.log
```

**End-to-End (7 days):**
- Confirm: no spurious `generic-remediate@d2m-icelandair-warm` systemd journal entries
- Before: 3–4 remediate invocations per 7 days (noise)
- After: 0 remediate invocations, icelandair native alerting unchanged

---

## HALE DECISION

**Status:** `APPLY_AUTONOMOUSLY` ✓ **APPLIED 2026-07-27 09:57 MT**

**Action Taken:**
- Added `d2m-icelandair-warm.service` to `SELF_ALERTING_UNITS` in `scripts/generic_remediate.py`
- Remediate now skips this unit on OnFailure, eliminating redundant restart attempts
- Icelandair's native Sterling alerting (in the warm-ping script itself) is unchanged
- No systemd service changes required; no configuration overhead

**Rationale:**
- Session-expiry failures are data conditions, not infrastructure bugs — restart cannot fix them
- The service already escalates to Sterling on auth errors; generic remediate's restart+escalation is redundant noise
- This change aligns remediation scope: infra/transient errors → restart + escalate; data-condition errors → skip + let service's own alerting handle it
- Zero regression risk: SELF_ALERTING_UNITS pattern already used for 3 other units with same problem

**Validation:** Commit to main, systemctl reload. Next auth failure will skip remediate invocation entirely.

**Phase 2 (autonomous re-login):** Deferred. Recommend evaluating Phase 1 noise reduction for 2 weeks before committing to re-login automation.
