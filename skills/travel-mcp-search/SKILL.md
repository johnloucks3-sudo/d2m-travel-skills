---
name: travel-mcp-search
description: MCP tools for travel DB/search (ships/air/hotels). Dynamic query hooks like Lua __index. Triggers: &quot;search ship&quot;, &quot;hotel rates&quot;, &quot;flight options&quot;, MCP travel queries.
location: file:///home/john/Thunderbird/skills/travel-mcp-search/SKILL.md
---

# Travel MCP Search (Lua Metatable Port)

Dynamic search agents for MCP server tools.

## Workflow
1. Connect MCP: core/mcp/travel_mcp_server.py tools
2. Hook queries: ships (itineraries), air (Google Flights), hotels (Room-Res/etc)
3. Parallel bash/webfetch for real-time data
4. Output JSON/table for proposals/quotes

## Test Cases
1. &quot;Silver Muse 2026 med&quot; → Itin + rates
2. Eval: Accurate, sourced data.

---
