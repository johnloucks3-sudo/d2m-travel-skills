# PROPOSAL — d2m-tasking-watcher Auto-Heal Pattern (4x in 7d)
*ELON, A12 Innovation & Disruption · 2026-06-07 16:43 MT*

---

## ROOT CAUSE

**The d2m-tasking-watcher is designed to fail periodically and be restarted by auto-heal, rather than being designed to run continuously without supervision.** This is a symptom-treatment architecture: we have a daemon that crashes or hangs every ~36 hours under normal operation, and we've automated the restart instead of eliminating the crash. Root cause is unknown — could be memory leak, unhandled exception under specific task queue conditions, external dependency timeout, or resource exhaustion. The auto-heal succeeds, which masks the problem from visibility and prevents diagnosis.

---

## PROPOSED FIX

**code_diff + standing_order** — Two-part:

1. **Immediate (autonomous):** Add structured logging to d2m-tasking-watcher to capture the crash/hang signature before auto-heal kills the process. Redirect stderr/stdout to a dedicated log file with timestamps and stack traces.

2. **Root cause (autonomous investigation):** Run the service under strace or similar probe to capture the exact failure mode (segfault, exception, I/O hang, timeout). Use the first restart cycle to gather data.

3. **Long-term:** Once root cause is identified, either fix the code, adjust configuration (timeouts, resource limits), or escalate architectural redesign to Commander if the issue is systemic.

---

## IMPLEMENTATION

**Hale can execute autonomously up to step 2. Step 3 requires Commander approval if it involves code changes.**

### PHASE 1 — LOG CAPTURE (Hale autonomous)

```
Step 1.1: Locate d2m-tasking-watcher systemd unit
          sudo systemctl cat d2m-tasking-watcher.service

Step 1.2: Confirm current log destination
          journalctl -u d2m-tasking-watcher -n 20

Step 1.3: If no dedicated log file, edit unit to add:
          StandardOutput=journal
          StandardError=journal
          SyslogIdentifier=d2m-tasking-watcher
          (or append to /var/log/d2m-tasking-watcher.log if file-based logging preferred)

Step 1.4: Reload + restart
          sudo systemctl daemon-reload
          sudo systemctl restart d2m-tasking-watcher

Next restart cycle will log the crash signature
```

### PHASE 2 — DIAGNOSIS (Hale autonomous, Dembe assists if needed)

```
Step 2.1: Wait for next auto-heal trigger (expected ~36 hours)

Step 2.2: Immediately after restart, extract full log
          journalctl -u d2m-tasking-watcher --since "4 hours ago" > /tmp/tasking_watcher_crash_log.txt

Step 2.3: Parse for:
          ✓ Python exception (traceback)
          ✓ Segfault / core dump
          ✓ Resource limit hit (OOM, ulimit)
          ✓ Network timeout (hung on external API call)
          ✓ Deadlock / wait-forever condition

Step 2.4: If pattern clear, draft root cause → file to OpsCenter

Step 2.5: If pattern unclear, escalate to Commander with full log
```

### PHASE 3 — FIX (conditional on Phase 2 findings)

```
[Defer until diagnosis is complete]
```

---

## VERIFICATION TEST

**End-to-end proof the fix works:**

### Test 1 — Baseline (before fix)

Document the current restart frequency:
```bash
# Count restarts in last 7 days
journalctl -u d2m-tasking-watcher --since "7 days ago" | grep -c "Started d2m-tasking-watcher"
# Expected: ~4 restarts (the current pattern)
```

### Test 2 — After Phase 1 applied

Confirm logging is active and capturing detail:
```bash
# Check that the next restart produces a detailed log entry
# Monitor for 48 hours, confirm detailed crash signature is present
tail -f /var/log/d2m-tasking-watcher.log  # or journalctl -u d2m-tasking-watcher -f
```

### Test 3 — After root cause fixed

Run extended soak test:
```bash
# Run service for 7 days (same baseline period) and confirm 0 auto-heals triggered
# OR: run with 3x normal load for 48 hours and confirm stability
```

### Test 4 — Monitoring gate

Remove the auto-heal trigger for this service and confirm it still runs for 30+ days without manual restart. (This is the proof that the fix is real, not that the auto-heal is better.)

---

## HALE DECISION

**APPLY_AUTONOMOUSLY**

### Rationale:

- **Phase 1 (log capture)** is a configuration change, zero risk, no code modification
- **Phase 2 (diagnosis)** is investigation only — read logs, file findings, no execution risk
- **Authority:** Both phases are enabled by SO-2026-05-04 (Hale's 95% autonomy, four gates only — this is not financial, client-facing, strategy, or new client; it's operational troubleshooting)
- **Diagnosis informs Phase 3:** Diagnosis result informs Commander decision on Phase 3 implementation
- **Standing order:** Hale owns spot-it-fix-it for system health (HALE_COS.md "Five Always SOs" item 3: "Spot-it-fix-it. The instant a blocker is identified, attempt an immediate fix"). This qualifies.

---

## NEXT ACTION

1. **Hale:** Apply Phase 1 immediately (logging configuration)
2. **Hale:** Wait for next restart cycle (~36 hours from now, ~2026-06-09 04:43 MT)
3. **Hale:** Collect Phase 2 data immediately after restart
4. **Hale → Commander:** Brief with findings and recommend Phase 3 approach

---

*ELON, A12 Innovation & Disruption*  
*Proposal ID: PROPOSAL-20260607-d2m-tasking-watcher*  
*Generated: 2026-06-07 16:43 MT*  
*Status: PENDING HALE EXECUTION*
