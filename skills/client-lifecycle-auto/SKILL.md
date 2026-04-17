---
name: client-lifecycle-auto
description: Automate client lifecycle emails/tasks (FPD alerts, follow-ups). Triggers: &quot;lifecycle email&quot;, &quot;FPD alert&quot;, &quot;client task auto&quot;, dossier changes. Dynamic hooks for state transitions like Lua __newindex.
location: file:///home/john/Thunderbird/skills/client-lifecycle-auto/SKILL.md
---

# Client Lifecycle Automation (Lua Metatable Port)

Hooks for lifecycle events: 60/45/30d FPD, booking changes → emails/tasks.

## Workflow
1. Read dossiers/, business/client_lifecycle/
2. Detect triggers (dates via bash date)
3. Generate emails using d2m-internal-comms/templates/
4. Draft Gmail via MCP or python api/thunderbird_api.py
5. Update dossier/master plan

## Test Cases
1. &quot;Auto FPD for Lyons&quot; → Draft 30d alert
2. Eval: Correct dates, D2M voice.

---
