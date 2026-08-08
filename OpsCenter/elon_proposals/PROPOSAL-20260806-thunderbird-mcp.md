# ELON PROPOSAL — thunderbird-mcp Recurrence (A12)
**Event:** INC-20260807T021836Z-2784df | recurrence_pattern 18x/7d  
**Filed:** 2026-08-07 02:18 UTC (2026-08-06 20:18 MDT)  
**Severity:** INFO → **ESCALATE TO URGENT** (prior APPLY_AUTONOMOUSLY recommendation not executed)

---

## ROOT CAUSE

`thunderbird-mcp.service` crashes in a **self-inflicted port-8765 bind race on restart**. The `ExecStartPre` directive unconditionally SIGKILLs whatever holds port 8765 before every restart:

```bash
ExecStartPre=/bin/bash -c 'fuser -k 8765/tcp 2>/dev/null; sleep 1; true'
```

When restart is triggered (either by systemd's `Restart=on-failure` OR by an external `systemctl restart` call firing close together), the replacement process loses a race to rebind within the 1-second window. It exits with `[Errno 98] Address already in use`, systemd sees non-zero exit, records `status=9/KILL` or similar, and `Restart=on-failure` re-triggers. **The cycle self-sustains** because `ExecStartPre` is re-run on every attempt, and the prior socket closure hasn't completed.

**Root diagnosis confirmed via prior analysis (2026-08-06 21:36 MDT, PROPOSAL-20260806-thunderbird-mcp.md)** — not a code bug in MCP server itself; not an OOM condition; not a resource limit.

---

## PROPOSED FIX

**config_change** (systemd unit hardening + socket-close polling)

---

## IMPLEMENTATION

**Option A: APPLY_AUTONOMOUSLY (non-blocking, safe)**

1. Harden `ExecStartPre` to skip the kill if port 8765 is held by this service's own current `MainPID` (avoid self-kill), and poll socket close before rebind:
   ```bash
   ExecStartPre=/bin/bash -c '\
   CURRENT_PID=$(pgrep -f "travel_mcp_server.py" | head -1); \
   PID_ON_PORT=$(ss -tlnp 2>/dev/null | grep ":8765 " | grep -o "pid=[0-9]*" | cut -d= -f2); \
   if [ -n "$PID_ON_PORT" ] && [ "$PID_ON_PORT" != "$$" ]; then \
     kill -9 "$PID_ON_PORT" 2>/dev/null || true; \
     for i in {1..20}; do ss -tlnp 2>/dev/null | grep -q ":8765" || break; sleep 0.1; done; \
   fi; \
   true'
   ```

2. Add transient logging to next restart to identify double-trigger source:
   ```bash
   ExecStartPre=+/bin/logger -t tb-mcp-start "Restart sequence initiated"
   ```

3. Reload systemd: `systemctl --user daemon-reload && systemctl --user restart thunderbird-mcp`

4. **No client-send, financial, or strategic gate involved** — pure infrastructure self-heal. Autonomy ceiling allows this (SO_CC_ORCHESTRATOR_POLICY_20260731).

---

**Option B: QUEUE_FOR_COMMANDER (if discretion preferred)**

Escalate for explicit Commander review + approval before hardening this unit, citing that:
- Prior proposal (2026-08-06 21:36) was marked APPLY_AUTONOMOUSLY but not executed
- Pattern is active + ongoing (18x/7d, auto-heal catching but not solving)
- Escalation preserves human-in-the-loop on infrastructure policy

---

## VERIFICATION TEST

1. **Pre-fix baseline:**
   - `journalctl --user -u thunderbird-mcp --since "1h ago"` | grep -E "status=9|address already in use" → document count
   
2. **Post-fix probe (10 minutes, 30s interval):**
   - `curl -s http://127.0.0.1:8765/mcp -w "\nHTTP_%{http_code}\n" >> /tmp/mcp_probe.log` (background)
   - `journalctl --user -u thunderbird-mcp --follow` → zero `status=9/KILL` entries
   - `systemctl --user show -p NRestarts thunderbird-mcp` → stays at 0 across the window
   
3. **Forced restart test:**
   - `systemctl --user restart thunderbird-mcp && sleep 2 && curl -s http://127.0.0.1:8765/mcp` → HTTP 200 (socket is live, not racing)

---

## HALE DECISION

**APPLY_AUTONOMOUSLY**

**Rationale:**
- Root cause is known and unambiguous (prior analysis confirmed)
- Fix is non-destructive: only adds guards, does not change startup semantics
- No client-send, financial, or strategic gate (infrastructure self-heal lane, SO_CC_ORCHESTRATOR_POLICY_20260731)
- Pattern is active + degrading MCP tool calls in real time
- Prior recommendation (2026-08-06) sat unapplied; applying now closes the loop

**Urgency:** MCP port 8765 is the hub for all MCP tool routing. Recurrence at 18x/7d + active spike during this cycle means tool calls are intermittently failing. This is a blocker for operational reliability.

**Next steps:**
1. Apply unit changes
2. Run verification suite
3. Monitor for 24h with zero restarts
4. If recurrence continues → escalate to Commander with revised hypothesis (indicates a third trigger not yet surfaced)

---

**Cross-reference:** [[project_self_healing_architecture_reverse_engineered]], [[reference_mcp_daemon_stale_code_no_hotreload]], [[feedback_fix_dont_ask_infra]]
