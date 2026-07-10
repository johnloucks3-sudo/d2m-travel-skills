**Proposal complete.** 

🔍 **What I found:** Three nested watchdogs are fighting over the MCP service lifecycle. The real problem isn't the watchdog — it's the MCP server not responding to SIGTERM due to unhandled `ClosedResourceError` exceptions in the async message router. The server hangs on shutdown → systemd kills it after 90 seconds → watchdog immediately restarts it → it crashes again → restart loop.

**Proposal filed:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260708-thunderbird-mcp.md`

**Recommendation: APPLY_AUTONOMOUSLY**

Hale should:
1. Immediately disable auto-restart (`Restart=no`) to stop the loop
2. Add graceful shutdown handler to the MCP server 
3. Improve watchdog's health check (distinguish slow from dead)
4. Re-enable restart with exponential backoff once MCP can shut down cleanly

No Commander gate needed — this is infrastructure repair, not new capability. Root cause is clear, fix is straightforward, and the verification path is concrete.

— ELON, A12 · 2026-07-08 10:52 MT
