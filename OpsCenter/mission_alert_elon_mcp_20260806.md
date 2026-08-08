# [CRITICAL] ELON MCP Incident Alert

SUBJECT: [CRITICAL] thunderbird-mcp Crash Loop — Phase 1 Config Change Failed

TO: Commander (johnloucks3@gmail.com)
FROM: ELON (A12 Innovation & Disruption)
TIME: 2026-08-06 14:26 MT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BLUF: thunderbird-mcp service is in crash loop. Phase 1 mitigation (reduce memory limit 1GB → 256MB) executed but ineffective — service still receives SIGKILL despite staying within limits. Root cause is systemic, not local. **Requires Commander decision on next steps.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INCIDENT SUMMARY
================

Service: thunderbird-mcp (MCP HTTP Server, port 8765)
Status: 🔴 CRITICAL — continuous crash loop, auto-heal disabled
Impact: MCP tools unavailable — blocks all downstream agent/subagent MCP calls

Journal snapshot:
  - Restart cycle: starts → runs ~5–10s → SIGKILL (exit 9/KILL) → systemd restarts
  - Memory peak: 192.5M resident + 20.8M swap (213.3M total)
  - Service functionality: ✓ Starts, ✓ Handles requests, ✓ Returns 200 OK
  - But: Crashes within seconds every cycle

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE 1 EXECUTION (Completed)
=============================

**Action:** Reduced service memory limits
  - MemoryMax: 1GB → 256MB (confirmed applied)
  - MemoryHigh: 805MB → 192MB (confirmed applied)

**Result:** ✗ FAILED
  - Service rebooted
  - Still receives SIGKILL
  - Memory usage: 213.3M (under 256MB limit)
  - Conclusion: Issue is NOT the service's local MemoryMax

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DIAGNOSIS
=========

The service stays within its configured limits but is still killed. Possible causes:

1. **Parent cgroup limit** — a slice or parent unit has a MemoryMax that the service is hitting
   (Check: systemctl show system-thunderbird.slice or user.slice for limits)

2. **systemd-oomd active** — system memory manager killing processes based on system-wide pressure
   (Check: systemctl status systemd-oomd)

3. **Kernel OOM killer** — despite cgroup limits, system is hitting OOM
   (Check: dmesg | grep -i "out of memory")

4. **Code issue** — service has a memory leak or unbounded allocation on init
   (Check: profile travel_mcp_server.py startup)

5. **Other limit** — file descriptor exhaustion, CPU time limit, or network connection limit
   (Check: ulimit -n, systemctl show -p CPUQuota)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS
==========

**Option A: Investigate Systemwide Limits**
  Investigate cgroup hierarchy, systemd-oomd, kernel OOM status. Requires ELON or Sterling audit.

**Option B: Accept Phase 1 & Revert**
  Revert to 1GB MemoryMax, accept that system is memory-constrained, proceed with daily operations.
  (Service will continue crashing in production; not recommended for stability.)

**Option C: Profile & Fix Code**
  Deep dive into travel_mcp_server.py: find the memory leak, fix initialization, rebuild.
  (Requires Sterling or dedicated code review; 2–4 hour turnaround.)

**Option D: Escalate to AG/OC**
  Request Gemini 3.1 Pro or Sonnet to investigate independently.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT STATE
=============
- Phase 1 config change: **LIVE** (256MB limit in effect)
- Service: **STOPPED** (restarting, awaiting decision)
- MCP tools: **UNAVAILABLE**
- Proposal document: /home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260806-thunderbird-mcp.md

Awaiting Commander direction. Standing by.

