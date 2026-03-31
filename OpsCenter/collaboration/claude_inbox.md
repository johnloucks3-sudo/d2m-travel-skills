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

---
## GOOSE TASK — ON BEHALF OF COMMANDER
task_id: GT-20260330-2215-SYST
submitted_by: GOOSE
authority: ON BEHALF OF COMMANDER
submitted_at: 2026-03-30T22:15:40 MT
task_type: system_ops
priority: HIGH
pii: false
context_files: [OpsCenter/collaboration/safe_cli_architecture.md, OpsCenter/collaboration/claude_gate_spec.md]
instructions: Read safe_cli_architecture.md and claude_gate_spec.md, then implement safe_cli_gate.py.
output_destination: /home/john/Thunderbird/OpsCenter/safe_cli_gate.py
deadline: ASAP

---
## GOOSE TASK — ON BEHALF OF COMMANDER
task_id: GT-20260330-2236-STRA
submitted_by: GOOSE
authority: ON BEHALF OF COMMANDER
submitted_at: 2026-03-30T22:36:45 MT
task_type: strategic
priority: HIGH
pii: false
context_files: [/home/john/Thunderbird/OpsCenter/collaboration/dip_proposal.md, /home/john/Thunderbird/OpsCenter/collaboration/safe_cli_architecture.md]
instructions: Review the 'Direct-Intelligence Pipeline (DIP)' proposal. Perform a formal SWITCHBLADE analysis: identify failure modes, assess risks of bypassing the blackboard, and propose a 'Dead-Man's Switch' for this autonomous pipeline. Output to OpsCenter/collaboration/dip_switchblade_analysis.md
output_destination: /home/john/Thunderbird/OpsCenter/collaboration/claude_output.md
deadline: ASAP

---
## GOOSE TASK — ON BEHALF OF COMMANDER
task_id: GT-20260330-2241-SYST
submitted_by: GOOSE
authority: ON BEHALF OF COMMANDER
submitted_at: 2026-03-30T22:41:04 MT
task_type: system_ops
priority: HIGH
pii: false
context_files: [/home/john/Thunderbird/OpsCenter/collaboration/dip_guarded_implementation_plan.md]
instructions: Implement dossier_intelligence_bot.py following the attached Guarded Implementation Plan. You MUST include the 5 mandatory Dead-Man Switch (DMS) controls (Heartbeat, Budget Cap, Write-Scope, PII Filter, Watchdog Timer). Use safe_cli_gate.py for all tool calls. Output to /home/john/Thunderbird/OpsCenter/dossier_intelligence_bot.py.
output_destination: /home/john/Thunderbird/OpsCenter/collaboration/claude_output.md
deadline: ASAP
