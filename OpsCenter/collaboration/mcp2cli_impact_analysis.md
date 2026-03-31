# Impact Analysis: mcp2cli Adoption for Thunderbird Wing

## 1. Executive Summary
The Thunderbird operational environment currently relies on a "blackboard" architecture—heavy use of Python glue scripts, file-based task queues (claude_inbox.md), and systemd daemons (claude_inbox_watcher.py, thunderbird-overwatch.py). Integrating mcp2cli presents an opportunity to bypass significant amounts of this infrastructure by providing direct command-line access to MCP (Model Context Protocol) capabilities, effectively removing the need for custom Python wrappers for many routine operations.

## 2. Current Architecture (The Python/Daemon/Inbox Model)
- **Task Dispatch:** Requires goose_tasker.py to write to claude_inbox.md.
- **Observation:** Requires claude_inbox_watcher.py to watch the file, hash-check, and trigger an API call.
- **Complexity:** High maintenance; every new tool added to the system requires manual updates to dispatchers, observers, and wrappers.
- **Latency:** Dependent on file-system events and watcher loops (typically introduces a 1-5 second delay).

## 3. Proposed Architecture (The mcp2cli Model)
- **Direct Dispatch:** mcp2cli would allow direct invocation of MCP tools from shell/scripts (e.g., mcp2cli call <tool_name> <params>).
- **Unified Interface:** Acts as a universal bridge, potentially replacing task_processor.py logic entirely for simple tool executions.
- **Efficiency:** Drastic reduction in custom Python code. Logic is offloaded to the standardized MCP layer.

## 4. Impact Analysis
### Benefits
- **Zero-Codegen Integration:** New MCP tools become instantly available in the CLI without writing Python wrappers or adding them to the watchdog.
- **Maintenance Reduction:** Eliminates the need to maintain claude_inbox_watcher.py and complex hashing logic for every interaction.
- **Standardization:** Aligns Thunderbird with industry-standard protocols, reducing "proprietary" debt.

### Challenges/Risks
- **Security:** Current watcher scripts include dissent logging, PII filtering, and WF-17 gates. Moving to direct CLI calls risks bypassing these safety mechanisms.
- **Tool Orchestration:** mcp2cli may lack the context awareness of our current "blackboard" logic (Hale-Loop daemon).

## 5. Roadmap & Recommendation
1.  **POC (Proof of Concept):** Create a secure wrapper around mcp2cli that re-introduces the dissent/PII filtering logic (a "Safe-CLI" layer).
2.  **Hybridization:** Keep the blackboard for high-level reasoning (Hale-Loop), but replace the low-level execution task-queue for routine tool calls (e.g., dossier updates, file ops).
3.  **Deprecation:** Gradually sunset custom dispatchers that provide simple tool-call passthroughs.

## 6. Verdict
**Highly Recommended.** Adoption will improve velocity and stability, provided we build a security gate that mimics our existing standing directive enforcements.