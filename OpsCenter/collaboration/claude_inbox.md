# CLAUDE INBOX
# Tasks queued for Claude by Commander or Goose.
# Claude reads this at session start and on every "Read your inbox and execute" trigger.
# Schema: JSON block per task. Append new tasks — never overwrite existing ones.
# Claude marks each task COMPLETE in routing_log.md when done.

---
INBOX EMPTY — ready for tasks.

---
## GOOSE TASK — ON BEHALF OF COMMANDER
task_id: GT-20260330-2137-TECH
submitted_by: GOOSE
authority: ON BEHALF OF COMMANDER
submitted_at: 2026-03-30T21:37:00 MT
task_type: tech_opportunity
priority: HIGH
pii: false
context_files: [none]
instructions: Perform an 'incubator scan' (using Thunderbirdmcp.runInnovationScan). Document the results in . Include a confirmation of your receipt of this task, the action taken, and the posting of the results in that file.
output_destination: /home/john/Thunderbird/OpsCenter/collaboration/claude_output.md
deadline: ASAP
