# CLAUDE INBOX
# Tasks queued for Claude by Commander or Goose.
# Claude reads this at session start and on every "Read your inbox and execute" trigger.
# Schema: JSON block per task. Append new tasks — never overwrite existing ones.
# Claude marks each task COMPLETE in routing_log.md when done.

---
INBOX EMPTY — ready for tasks.

---
## GOOSE TASK — ON BEHALF OF COMMANDER
task_id: GT-20260330-1727-RESE
submitted_by: GOOSE
authority: ON BEHALF OF COMMANDER
submitted_at: 2026-03-30T17:27:41 MT
task_type: research
priority: NORMAL
pii: false
context_files: [OpsCenter/collaboration/goose_output.md]
instructions: Research the top 3 luxury cruise lines competing with Silversea in the ultra-luxury segment. Focus on pricing, new ships launching 2026-2027, and any loyalty program changes. Write findings to goose_output.md context for Claude to synthesize.
output_destination: /home/john/Thunderbird/OpsCenter/collaboration/claude_output.md
deadline: ASAP
