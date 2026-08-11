**Proposal complete.** Root cause is an async resource leak in the MCP server's task groups — when connections close unexpectedly, `anyio.ClosedResourceError` exceptions aren't caught, crashing the process. The restart policy then bounces it every 10 seconds, creating the 44x/7d pattern.

**Proposed solution is two-phase:**
- **Phase 1 (config):** Logrotate policy, adjust restart timings, set memory hard limit — execute autonomously
- **Phase 2 (code):** Add proper exception handling for ClosedResourceError in async task groups — queue for Commander

Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260808-thunderbird-mcp.md`.
