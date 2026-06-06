# PROPOSAL: MCP Server Crash Loop — Root Cause & Fix

**Incident:** INC-20260605T220404Z-578f83  
**Severity:** CRITICAL (all external integrations down)  
**Proposed by:** A12 ELON · Timestamp: 2026-06-05 22:40 MT

---

## ROOT CAUSE

The MCP server is crashing during initialization or request handling, triggering systemd's auto-restart. The watchdog's attempt to diagnose via `journalctl` is timing out (>10s), which blocks log retrieval and prevents root-cause analysis. This creates a blind restart loop: the service crashes → watchdog tries `journalctl` → timeout blocks → watchdog gives up. **The crash itself is unknown.** Likely causes (in priority order): (1) config file corruption or missing credentials, (2) import/dependency failure, (3) unhandled exception in MCP __init__, (4) port binding conflict from prior crashed instance still holding the port.

---

## PROPOSED FIX

**Type:** `config_change` + immediate manual diagnostics

**Core idea:** Bypass systemd's journalctl (which is timing out) by redirecting stderr to a file. Then manually start MCP with output visible so we can see the crash reason.

### Step 1: Make systemd write MCP stderr to a direct file
Edit `/etc/systemd/user/thunderbird-mcp.service`:
```ini
StandardError=file:/home/john/Thunderbird/logs/mcp-stderr.log
StandardOutput=file:/home/john/Thunderbird/logs/mcp-stdout.log
```

Rationale: Bypass journald entirely. Direct file output will not timeout and will capture the full crash.

### Step 2: Reload systemd
```bash
systemctl --user daemon-reload
```

### Step 3: Kill any zombie MCP processes
```bash
pkill -9 -f "thunderbird.mcp\|mcp.*server" || true
```

### Step 4: Manual foreground run (with immediate visibility)
```bash
python3 /path/to/thunderbird_mcp.py 2>&1 | tee /tmp/mcp-manual.log &
sleep 2
# Observe output. If it crashes, read /tmp/mcp-manual.log
```

### Step 5: Fix the root cause
- If config error → fix config, restart
- If missing creds → verify credentials file, restart
- If import error → check Python deps, reinstall/fix, restart
- If port conflict → `lsof -i :$MCP_PORT` to find holder, kill it, restart

### Step 6: Enable and start systemd service
Once manual run succeeds:
```bash
systemctl --user enable thunderbird-mcp.service
systemctl --user start thunderbird-mcp.service
```

---

## IMPLEMENTATION

**Autonomy:** Hale can execute steps 1–4 immediately without Commander approval (operational crisis, within autonomy band per SO-2026-05-04 spot-it-fix-it rule). Step 5 depends on what we find.

**Blockers:** None — this is pure ops.

**Timeline:** 
- Steps 1–3: <1 min
- Step 4 (manual run): 5–10 sec (watch for crash)
- Step 5 (root fix): 1–5 min once we know what broke
- Step 6: <1 min

**Hand-off:** Once we have logs from the manual run, Hale surfaces to Commander if the fix requires code changes or credential updates outside her lane.

---

## VERIFICATION TEST

**SUCCESS criteria:**
1. ✅ Systemd service is `active (running)` and stays that way for >30 seconds
2. ✅ Stderr/stdout files contain no `Traceback` or `FATAL` lines in the last restart cycle
3. ✅ MCP responds to a simple request:
   ```bash
   curl -s http://localhost:$MCP_PORT/health | jq .
   # OR if MCP has no /health endpoint:
   python3 -c "import requests; print(requests.get('http://localhost:PORT/').status_code)"
   ```
4. ✅ Hale's `hale_state.json` shows `"mcp_server": "ONLINE"` after next health check (5 min)

**Failure test:**
- If MCP crashes again → repeat steps 3–4 to get new logs and identify the actual blocker

---

## HALE DECISION

**`APPLY_AUTONOMOUSLY`**

Rationale:
- This is a production outage affecting all external integrations (Gmail, Drive, TESS, scrapers)
- The fix is purely operational: config edit + log redirection + manual test
- It's within Hale's autonomy band per SO-2026-05-04 (spot-it-fix-it) and PRODUCTION-LOCK (operational artifacts, no domain-owner lane crossed)
- No financial, client-facing, or strategy gate involved
- Hale should execute immediately and page Commander only if root cause requires code changes or credential updates she can't access

**Escalation trigger:** If step 4 (manual run) crashes with an error Hale cannot fix (e.g., missing source code file, invalid credentials she doesn't have access to), she escalates to Commander with the error message and asks for the fix.

---

*— A12 ELON · Thunderbird Wing · 2026-06-05 22:40 MT*
