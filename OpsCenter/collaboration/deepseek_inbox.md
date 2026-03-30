# DEEPSEEK INBOX
# Arbitration requests ONLY. No PII ever — hard fence.
# Written by Claude, Goose, or Commander when inter-agent conflict detected.
# Commander triggers Deepseek: "Read deepseek_inbox and issue ruling"

ARBITRATION REQUEST FORMAT:
  task_id: [original task_id]
  requested_by: CLAUDE | GOOSE | COMMANDER
  submitted_at: [ISO timestamp MT]
  pii: FALSE (verify before submitting — if TRUE, do not submit)
  agent_a_summary: [3 sentences max]
  agent_b_summary: [3 sentences max]
  question: [one clear question for Deepseek to answer]

---
INBOX EMPTY — no disputes pending.
