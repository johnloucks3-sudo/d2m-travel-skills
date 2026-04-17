---
name: agentic-intel-extend
description: Extend agentic_intel.py for web/tech/world intel using dynamic agent hooks. Triggers on &quot;intel sweep&quot;, &quot;research web&quot;, &quot;tech intel&quot;, &quot;world news travel&quot;, extend core/intel/thunderbird_agentic_intel.py. Use Lua metatable patterns for chaining intel agents.
location: file:///home/john/Thunderbird/skills/agentic-intel-extend/SKILL.md
---

# Agentic Intel Extension (Lua Metatable Port)

Dynamic chaining of intel agents mimicking Lua __call hooks.

## Workflow
1. Read core/intel/thunderbird_agentic_intel.py
2. Extend with hooks: web_search → tech_analysis → world_travel_impact
3. Use webfetch/grep for sources, bash for intel/intel.json update
4. Output to intel/ with JSON + MD summary
5. Chain: if complex, delegate via nexus-agent-coord

## Test Cases
1. &quot;Intel on Silversea strikes&quot; → Fetch news, analyze impact
2. Eval: JSON structured, accurate sources.

---
