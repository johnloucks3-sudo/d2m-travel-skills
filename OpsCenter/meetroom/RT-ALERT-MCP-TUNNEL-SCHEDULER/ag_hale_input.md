# USAF POINT PAPER: WAR ROOM INVESTIGATION (RT-ALERT-MCP-TUNNEL-SCHEDULER)
**AUTHOR:** HALE-AG (4-Star Lead Equivalent / Antigravity Engine)  
**DATE:** 2026-08-08 12:08 MT | **CLASSIFICATION:** WING UNCLASSIFIED  

---

### BLUF
**MCP crash was an automated remediation cascade loop; tunnel/scheduler alerts are 100% false positives from stale unit names in `deploy/health_check.py`.** All live canonical units are healthy.

---

### THREAD 1: THUNDERBIRD-MCP 11:08-11:11 CRASH & STOP-HANG ROOT CAUSE
- **Rapid Restart Storm (11:08:18–21, 5 restarts / 5s):** 
  - `thunderbird-mcp-gc.service` (12h garbage collection timer) exited with `SIGTERM` at 11:08:18.
  - Failure fired `OnFailure=thunderbird-generic-remediate@thunderbird-mcp-gc.service`.
  - `scripts/generic_remediate.py` executed `systemctl --user start thunderbird-mcp-gc.service`, whose `ExecStart` ran `systemctl --user restart thunderbird-mcp.service`.
  - Mutual recursion triggered 5 restart cycles in <3s until systemd tripped `StartLimitBurst=5` (`start-limit-hit`). Peak RAM was 253.9MB (well below 512MB/1GB thresholds; not an OOM).
- **90s Stop-Hang & SIGKILL (11:09:49–11:11:19):**
  - At 11:09:49, GC failed again, triggering `systemctl --user stop thunderbird-mcp.service`.
  - FastMCP/uvicorn (PID 1157152) hung in `stop-sigterm` ignoring graceful SIGTERM.
  - Systemd reached `TimeoutStopSec=90s` and issued `SIGKILL` at 11:11:19. Restarted cleanly at 11:11:20; current uptime >50m.

---

### THREAD 2: TUNNEL & SCHEDULER UNIT VERIFICATION & HEALTH CHECKER FIX
- **Independent Ground Truth Verification (Live Systemd State):**
  - `thunderbird-tunnel.service`: **disabled / inactive** (Dead duplicate)
  - `cloudflared.service`: **enabled / active** (PID 1268528, multi-hostname config `/home/john/.cloudflared/config.yml`)
  - `thunderbird-scheduler.service`: **disabled / inactive** (Dead duplicate; lost lock race on Aug 7)
  - `d2m-scheduler.service`: **enabled / active** (PID 1844, 9 jobs + Overwatch active, 14h+ uptime)
  - `thunderbird-api.service`: **enabled / active** | `d2m-api.service`: **disabled / inactive**
- **Recommended Fix for `deploy/health_check.py`:**
  1. Update `SERVICES` list (lines 26–31) to true canonical units:
     `["thunderbird-mcp.service", "thunderbird-api.service", "cloudflared.service", "d2m-scheduler.service"]`
  2. In `check_service()`, verify `is-enabled` alongside `is-active`; if unit is disabled, bypass alert or log explicitly as decommissioned.

---
— V. Hale, VCS (AG Engine)
