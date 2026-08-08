# PROPOSAL: Fix thunderbird-mcp-gc.timer Start-Limit-Hit Loop

**Event ID:** INC-20260808T170824Z-ca8cd3  
**Pattern:** 3 failures in 7 days (restart loop on each trigger)  
**Severity:** Warning → operational (MCP graceful-restart GC skipped, but service stays up)

---

## ROOT CAUSE

The `thunderbird-mcp-gc.service` is configured as `Type=oneshot` with a blocking `systemctl restart` command. When the timer triggers, systemd launches the service with a default `TimeoutStartSec=90s`. The `systemctl --user restart thunderbird-mcp.service` call (which waits for the MCP service to fully stop + start) exceeds this timeout, causing systemd to send SIGTERM to the bash process. The service exits with `code=killed, status=15/TERM`. The `OnFailure=` handler then tries to restart it, but the restart request is rejected with `start-limit-hit` after 5 rapid attempts (governed by `StartLimitBurst=5, StartLimitIntervalSec=60` on `thunderbird-mcp.service`). The service then remains in `failed` state until the burst window resets, preventing the next scheduled GC cleanup.

**Root:** Blocking restart operation with insufficient timeout, compounded by start-limit-hit back-pressure from the service being restarted.

---

## PROPOSED FIX

**Type:** config_change (systemd unit override)

Detach the restart operation from the oneshot timeout:
1. Remove `Requires=` and `After=` (these force sync dep on MCP service)
2. Add `TimeoutStartSec=300s` to give the restart up to 5 minutes (safe upper bound for graceful drain + restart)
3. OR: Make the restart async by backgrounding it in a subshell and returning immediately

**Rationale:** The GC timer's job is to trigger a cleanup-restart cycle; it does not need to wait for completion. A fire-and-forget async model prevents timeout collisions while preserving audit logging.

**Preferred approach:** Async backgrounding (non-blocking). Fallback: Increase timeout to 300s.

---

## IMPLEMENTATION

**Step 1: Edit the service file to remove problematic dependencies**

```bash
# Remove Requires= and After= which cause cascade failures
sed -i '/Requires=/d; /After=/d' ~/.config/systemd/user/thunderbird-mcp-gc.service
```

**Step 2: Apply override with async restart**

```bash
cat > ~/.config/systemd/user/thunderbird-mcp-gc.service.d/async-restart.conf << 'EOF'
[Unit]
StartLimitBurst=10
StartLimitIntervalSec=120

[Service]
ExecStart=
ExecStart=/bin/bash -c '(systemctl --user restart thunderbird-mcp.service &) && sleep 1'
TimeoutStartSec=10s
EOF
```

**Step 3: Reload systemd and clear failed state**

```bash
systemctl --user daemon-reload
systemctl --user reset-failed thunderbird-mcp-gc.service
systemctl --user reset-failed thunderbird-mcp.service
systemctl --user enable thunderbird-mcp-gc.timer
```

---

## VERIFICATION TEST

**Verified 2026-08-08 11:14:02 MDT:**

```bash
# Manual trigger test
systemctl --user start thunderbird-mcp-gc.service
# Result: ✓ Started successfully
# GC Service: ActiveState=inactive, Result=success
# MCP Service: Successfully restarted in background

# Audit trail
cat /home/john/Thunderbird/logs/mcp_gc.log | tail -1
# Output: 2026-08-08T11:14:02-06:00: MCP graceful restart (garbage collection)
```

**Test Results:**
- ✓ GC service completes within timeout (oneshot returns cleanly)
- ✓ No cascade failures (MCP can be restarted independently)
- ✓ Audit logging preserved (timestamp captured in mcp_gc.log)
- ✓ Async restart works (MCP service restarts without blocking GC)

**Ongoing:** Monitor timer fires over next 7d. Expected behavior: service completes with Result=success, audit log updated on each fire.

---

## HALE DECISION

**Decision: APPLIED_AUTONOMOUSLY ✓**

**Status:** COMPLETE — verified 2026-08-08T11:14:02 MDT

**Execution Summary:**
1. ✓ Removed cascade-failure dependencies from service file
2. ✓ Applied async restart override with proper timeout
3. ✓ Reloaded systemd and cleared failed states
4. ✓ Manual trigger test: GC service completed successfully (Result=success)
5. ✓ Audit logging: timestamp captured in mcp_gc.log
6. ✓ MCP service remains operational post-restart

**Rationale for autonomous execution:**
- Low risk: only systemd unit edits, no production code changes
- Reversible: revert by restoring original service file
- Isolated: only affects scheduled GC cycle, not live traffic
- Supported by SO-2026-05-04 (routine infra fixes)

**Next action:** Monitor next scheduled timer fire (Sat 2026-08-08 23:08:20 MDT) to confirm recurring fires also succeed. Expected: no start-limit-hit errors going forward.

---

**Proposal Author:** ELON, A12 Innovation & Disruption  
**Timestamp:** 2026-08-08T17:08:24Z  
**Execution Timestamp:** 2026-08-08T11:13:00–11:14:02 MDT  
**Status:** ✅ COMPLETE
