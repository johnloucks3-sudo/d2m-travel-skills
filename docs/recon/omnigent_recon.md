# Omnigent Recon — omnigent-ai/omnigent
*ELON A12 · 2026-06-21*

## What It Is
Omnigent (omnigent-ai/omnigent, 4,296 stars, Apache-2.0, Python 3.12+, alpha status) is an open-source AI agent meta-harness: a common orchestration layer over Claude Code, Codex, Cursor, Pi, and custom YAML-defined agents. Core features: hot-swap agent harnesses without rewriting, budget caps and policy governance (pause for approval before risky actions, cap spend, limit tool reach), cloud sandbox execution via Modal/Daytona/Islo, real-time multi-user session sharing, and cross-device session continuity (start terminal, continue browser, pick up on phone).

## Wrapping a Headless Spawn with Budget + Sandbox
To wrap one of our existing headless Claude spawns inside Omnigent's budget and sandbox controls:

1. Install: `pip install omnigent`
2. Define the agent in YAML with a `policy` block:
   ```yaml
   agents:
     thunderbird-worker:
       harness: claude-code
       policy:
         max_spend_usd: 0.50
         pause_on: [file_delete, git_push, send_email]
         sandbox: modal  # disposable cloud sandbox
   ```
3. Launch via: `omnigent run thunderbird-worker --prompt "WRITE output to /path/file.txt"`
4. The policy layer intercepts tool calls matching `pause_on` and surfaces to the operator before execution — eliminating our current manual WF-17 gate burden for internal tasks.

## D2M Relevance
High for internal agent ops. Budget cap + policy pause maps directly to our S/O/T doctrine gates (financial commit, client send). The client-send path canary is still required per Sterling's guardrail, but Omnigent could enforce the spend cap and tool-restriction gates automatically. Currently alpha — not production-ready for client-path tools. Watch for stable release.

*Source: github.com/omnigent-ai/omnigent · cloned to tools/omnigent · 2026-06-21*
