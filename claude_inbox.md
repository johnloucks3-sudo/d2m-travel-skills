---
## TASK: SPSA-ANALYSIS-GMAIL-TEMPLATE-STRIPPING
status: COMPLETED
from: OpenCode
injected: 2026-05-02 00:45 MT
completed: 2026-05-03 01:15 MT
priority: P1
task: |
  We are facing persistent template sanitization in the Gmail API pipeline (via create_gmail_draft_direct.py). 
  
  SPSA ANALYSIS REQUIRED:
  1. SITUATION: We require consistent, branded D2M email stationery (Background #f7f3ea, Ink #0000ff, Georgia font) for client proposals and timelines.
  2. PROBLEM: The Gmail API (and Gmail's internal rendering engine) strips specific CSS (background colors, certain font-family definitions, div-level styles) when pushing raw HTML via MIMEText.
  3. SOLUTION: We need to define a "Gmail-Safe Stationery Specification." This includes:
     - Identification of "safe" CSS (e.g., inline-only, legacy table-based layouts vs. div-based layouts).
     - Identifying if the Gmail API `raw` field is being sanitized by Google's backend or if the MIME structure is triggering it.
     - Proposing a robust template engine update (e.g., pre-processing HTML to inline all styles, removing disallowed tags).
  4. ACTION:
     - Provide a specific HTML/CSS template structure that is guaranteed not to be stripped by Gmail.
     - Review `core/email/thunderbird_gmail.py` and `scripts/create_gmail_draft_direct.py` to see if the MIME structure is failing to signal "trusted" HTML.
     - Propose a test-case script that sends a "Stress Test" email to verify what Gmail keeps vs. strips.

  Write result to /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
TASK
