---
name: claude-opencode-bridge
description: Bridge Claude-Code &amp; OpenCode with dynamic delegation hooks. Triggers: &quot;task Claude&quot;, &quot;opencode help&quot;, bridge tasks. Lua metatable __call for seamless handoff.
location: file:///home/john/Thunderbird/skills/claude-opencode-bridge/SKILL.md
---

# Claude-OpenCode Bridge (Lua Metatable Port)

Dynamic proxy for cross-model calls.

## Workflow
1. Decide: Claude (voice/strat) vs OpenCode (code/ops)
2. Delegate: Use thunderbird_model_dispatcher.py or inboxes
3. Sync results via outboxes/wing_comms.md
4. Loop until complete

## Test Cases
1. &quot;Write client email&quot; → Route to Claude
2. Eval: Correct routing, results synced.

---
