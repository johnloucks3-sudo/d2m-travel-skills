# ELON PROPOSAL: thunderbird-overwatch Crash Loop
**Event:** INC-20260603T222210Z-c5fdbc  
**Service:** thunderbird-overwatch  
**Severity:** CRITICAL  
**Timestamp:** 2026-06-03T22:22:10Z

---

## ROOT CAUSE

The `thunderbird-overwatch.service` file contains a systemd syntax error: the `OnFailure=` directive appears on line 17 in the `[Service]` section, where it is not recognized. The `OnFailure=` key is valid only in the `[Unit]` section. systemd silently ignores the malformed directive, and the underlying service crashes repeatedly. Combined with the `StartLimitBurst=5` and `StartLimitIntervalSec=60` settings in `[Unit]`, the service hits the restart limit (5 restarts in 60 seconds) and systemd ceases attempting restarts, leaving the service dead.

---

## PROPOSED FIX

**Type:** `config_change`

Move the `OnFailure=thunderbird-alert@%n.service` line from the `[Service]` section (line 17) to the `[Unit]` section (immediately after line 5).

**Rationale:** This is a pure syntax correction. systemd will then recognize the directive and the service can function normally. The alert mechanism (OnFailure) is a unit-level behavior, not a service-level behavior.

---

## IMPLEMENTATION

**Hale can execute autonomously (no Commander approval needed — syntax fix, no semantic change):**

1. Read current service file (✓ done above)
2. Edit file: move `OnFailure=thunderbird-alert@%n.service` to `[Unit]` section
3. Reload systemd user daemon: `systemctl --user daemon-reload`
4. Restart service: `systemctl --user restart thunderbird-overwatch`
5. Verify: `systemctl --user status thunderbird-overwatch` (active, not looping)
6. Check journal for new errors: `journalctl --user -u thunderbird-overwatch -n 20`

**Estimated time:** 2 minutes  
**Rollback:** Revert the file, `daemon-reload`, `restart`

---

## VERIFICATION TEST

**Immediate (after restart):**
- `systemctl --user is-active thunderbird-overwatch` → should return `active`
- `systemctl --user status thunderbird-overwatch` → no "restart loop" or "reached start limit" messages

**5-minute soak test:**
- Monitor journal: `journalctl --user -u thunderbird-overwatch -f`
- Service should remain running without restarts
- No "Unknown key 'OnFailure'" warnings in journal

**End-to-end functional test:**
- Verify the overwatch script (thunderbird_overwatch.sh) executes its intended function
- Check that any alert mechanism (thunderbird-alert@%n.service) would fire if needed

---

## ESCALATION: SECONDARY CODE ISSUES DISCOVERED

**Status after systemd fix:** The service file syntax error is FIXED. However, the underlying Python code has multiple critical import errors that prevent the service from running.

### Issues Found:
1. ✅ **FIXED:** `task_processor.py` line 52 imported unused `QWEN_PLUS_FREE_MODEL` (removed)
2. ❌ **NEW:** `thunderbird_overwatch.py` line 56 imports `GROQ_MODELS` from `thunderbird_model_router` — this export does not exist in the router module
3. ⚠️ **POTENTIAL:** Other missing exports in the model_router may exist; full audit needed

### Root Cause
The `thunderbird_model_router.py` module underwent refactoring that removed or renamed exports (QWEN_PLUS_FREE_MODEL, GROQ_MODELS), but downstream consumers were not updated. This is a **cross-module API breakage** — not just a single-file bug.

---

## REVISED HALE DECISION

**ESCALATE_TO_COMMANDER**

**Reasoning:**
- The systemd config syntax fix is complete and autonomous (✅ applied).
- The immediate Python import fix is applied (✅ removed unused import).
- **However:** The full scope of code breakage is larger than a "spot-it-fix-it" fix. The model_router API has diverged from its consumers.
- **Recommendation:** Commander should direct a STERLING code review of:
  - What exports should the model_router have?
  - Which downstream modules use it and what are their actual needs?
  - Should this be a deprecation+migration plan, or a single refactor?
- This is an ARCHITECTURE-level decision, not an autonomy-band operational fix.

---

## CURRENT STATUS

| Item | Status | Details |
|------|--------|---------|
| Systemd syntax error | ✅ FIXED | OnFailure moved to [Unit] section |
| Config reload | ✅ DONE | `systemctl --user daemon-reload` applied |
| Unused import | ✅ REMOVED | QWEN_PLUS_FREE_MODEL dropped from task_processor imports |
| Service startup | ⏸️ BLOCKED | Still fails due to GROQ_MODELS missing from model_router |
| Code audit | ⏳ NEEDED | Sterling to review model_router API consistency |

---

**Next:** Commander decision on whether to:
- (A) Quick-fix: Add `GROQ_MODELS = [...]` stub to unblock service, schedule full audit
- (B) Full audit: Sterling reviews and fixes all model_router consumers before restart
- (C) Temporary disable: Disable thunderbird-overwatch until code is fixed

*— ELON (A12 Innovation & Disruption)*
