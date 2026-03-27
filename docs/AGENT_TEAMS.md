# Thunderbird Agent Teams (Experimental)

Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

- **Staff Meeting:** COS spawns A2/A3/A5/A9 in parallel → synthesizes unified brief
- **Client Research:** A2 intel + A3 logistics + A9 cost → EXEC proposal narrative
- Use for highest-complexity multi-domain work only; `consult_persona` MCP tool for lightweight queries

```
# From within a Claude Code session:
"Create a team with A2, A3, A9 to research Mediterranean options for the Kuklinski group"
claude --agent wing-coordinator
```
