
# PROPOSAL: DIRECT-INTELLIGENCE PIPELINE (DIP)

## 1. Executive Summary
We are transitioning from the "Blackboard/Watcher" orchestration pattern to a "Direct-Intelligence Pipeline (DIP)" to optimize for:
1.  **Lower Latency:** Bypass file-system polling (claude_inbox.md) for routine intel tasks.
2.  **Lower Token Usage:** Offload tool orchestration to a lean Python bot (dossier_intelligence_bot.py) that uses mcp2cli via the safe_cli_gate.py. Use LLMs only for final synthesis.
3.  **Autonomous Flow:** Direct sequence: Search → Parse → Synthesize → Recommend → Publish.

## 2. Proposed Architecture
- **Orchestrator:** dossier_intelligence_bot.py (Local Python script).
- **Tool Access:** Invokes mcp2cli via safe_cli_gate.py (validated, secure, audit-logged).
- **Execution Path:**
    1. Tool Call (e.g., runInnovationScan)
    2. Local Parsing (JSON filter, no token cost)
    3. Synthesis (LLM call with minimal, specific context)
    4. Publishing (Direct file write to /intel/ directory)

## 3. The "Switchblade" Request
Commander specifically requests **SWITCHBLADE Analysis** of this architecture:
- Evaluate the risk of "Tool-Direct Execution" bypassing the blackboard's oversight.
- Identify potential "Switchblade" failure modes (what happens if the direct-invocation layer loses sync with the Blackboard?).
- Recommend a "Dead-Man's Switch" for the autonomous pipeline to prevent runaway token usage or hallucinated tool calls.
