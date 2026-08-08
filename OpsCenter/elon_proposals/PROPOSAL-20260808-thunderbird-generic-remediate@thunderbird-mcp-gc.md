Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260808-thunderbird-generic-remediate@thunderbird-mcp-gc.md`.

**ELON assessment:** The service crashes every 2–3 days, auto-heal restarts it, but the root condition (stale MCP state or resource leak) re-emerges. We're masking symptoms, not fixing causes. 

**Recommendation:** Shift from reactive restarts to **proactive MCP health probe** (new daemon, runs every 4h, rebuilds before crash). Tests in 7 days; if clean, retire the auto-heal gate entirely and move detection upstream.

This is queued for your approval — daemon + SO change are straightforward once you sign off on the shift (reactive→proactive).
