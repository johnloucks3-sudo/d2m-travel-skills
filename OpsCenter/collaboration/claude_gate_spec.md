
You are tasked with implementing the "Safe-CLI Gate" (safe_cli_gate.py).
This script will act as the secure entry point for all 'mcp2cli' tool executions in the Thunderbird Wing.

### REQUIREMENTS:
1.  **Input:** Reads an 'ExecutionManifest' (JSON) from stdin or a passed argument.
2.  **Manifest Schema:**
    {
      "task_id": "UUID",
      "timestamp": "ISO8601",
      "originating_agent": "Goose|Claude|Hale",
      "requested_tool": "string",
      "arguments": "object",
      "security_context": {
        "pii_check": "boolean",
        "wf17_gate": "boolean"
      }
    }
3.  **Policy Engine:**
    - Reject if 'requested_tool' contains 'email' or 'send' (Drafts-only policy).
    - Regex-check arguments for PII (email, credit card, phone).
    - If any check fails, log to 'dissent_log.md' and print/return an error.
4.  **Audit:**
    - Log every attempt (PASSED or BLOCKED) to 'star_protocol_log.csv'.
5.  **Execution:**
    - If valid, execute 'mcp2cli' via subprocess.
    - Return the output.

Read the architectural spec in OpsCenter/collaboration/safe_cli_architecture.md before coding.
