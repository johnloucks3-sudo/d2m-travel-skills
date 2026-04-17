---
name: nexus-agent-coord
description: Enhance Nexus daemon for agent coordination using dynamic metatable-like hooks. Routes tasks between OpenCode/Claude via inboxes/outboxes, updates mission_board.json. Use for &quot;route task&quot;, &quot;delegate agent&quot;, &quot;nexus coord&quot;, &quot;cross-model task&quot;, or any multi-agent workflow in Thunderbird. Proactively suggest for inbox tasks needing escalation.
location: file:///home/john/Thunderbird/skills/nexus-agent-coord/SKILL.md
---

# Nexus Agent Coordination Skill (Lua Metatable Port)

Port of Lua dynamic metatables to Thunderbird agent routing. Use __index-like hooks for fallback delegation, __newindex for task injection.

## Workflow
1. **Analyze task**: Read OpsCenter/mission_board.json, claude_inbox.md, opencode_inbox.md
2. **Dynamic hook**: Define agent metatable:
   - Claude: strategy/judgment (append to claude_inbox.md with status: UNREAD)
   - OpenCode: ops/code (append to opencode_inbox.md with NEXUS:)
   - Fallback: self-handle if simple
3. **Inject task**: Use exact format from AGENTS.md
4. **Update board**: Edit mission_board.json with status, assignee
5. **Verify**: Check outboxes for completion

## Test Cases
1. Prompt: &quot;Route intel sweep to Claude&quot; → Append TASK to claude_inbox.md
2. Prompt: &quot;Fix MCP bug&quot; → NEXUS: task to opencode_inbox.md
3. Eval: 100% tasks routed correctly, board updated.

---
