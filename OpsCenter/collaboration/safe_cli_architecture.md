# Architectural Design: The Safe-CLI Gate

## 1. Overview
The 'Safe-CLI-Gate' architecture introduces a mandatory validation layer between the AI Agents (Goose/Claude) and the direct execution tool mcp2cli. This prevents direct execution of unsafe commands and ensures all actions are logged.

## 2. Component Logic
- **The Gatekeeper (safe_cli_gate.py):** A lightweight Python script that acts as the entry point for all commands. It does not run commands directly; it only validates them.
- **The ExecutionManifest:** Every request is a JSON object. If a command lacks a manifest, the gate rejects it.
- **The Policy Engine:** Embedded within the Gatekeeper. It runs the regex and whitelist checks before spawning the mcp2cli process.
- **The Feedback Loop:**
    - On Success: Execution proceeds, and an entry is made to star_protocol_log.csv.
    - On Failure/Dissent: Execution is aborted, an alert is sent via Telegram, and an entry is logged to dissent_log.md.

## 3. Deployment Strategy
- **Isolation:** The Gatekeeper runs in the same environment as the current claude_inbox_watcher.py but is a separate process.
- **Fallback:** In the event the Gatekeeper crashes, we maintain a hard-coded "FAIL-SAFE" that disables all mcp2cli access until a human manually overrides.

## 4. Permission Model
- The mcp2cli binary will have its execution permissions restricted to only be callable by the safe_cli_gate.py process (using Linux group/user permissions). This prevents bypass.
