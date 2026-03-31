
# GUARDED IMPLEMENTATION PLAN: DOSSIER_INTELLIGENCE_BOT (DIP)
## Version 1.0 — MANDATORY COMPLIANCE

This document serves as the GOLDEN SPECIFICATION for the dossier_intelligence_bot.py implementation. All 5 P0/P1 Dead-Man's Switch (DMS) controls defined by the Switchblade analysis are mandatory.

### 1. DMS-1: Blackboard Heartbeat (P0)
- Start: Register to blackboard: "START | DIP-{task_id} | {timestamp}"
- Complete: Update: "COMPLETE | DIP-{task_id} | {output_path} | {timestamp}"
- Abort: Update: "ABORT | DIP-{task_id} | {reason} | {timestamp}"

### 2. DMS-2: Token Budget Hard Cap (P0)
- Logic: if budget == 'YELLOW' or 'RED': halt synthesis -> write partial results -> alert.
- Logic: if cumulative_tokens > 30000: halt -> alert.

### 3. DMS-3: Write-Scope Lock (P0)
- ALLOWED: /home/john/Thunderbird/intel/
- BLOCKED: /home/john/Thunderbird/dossiers/, /home/john/Thunderbird/output/, /home/john/Thunderbird/OpsCenter/collaboration/
- Action: Any attempt to write outside allowed paths must trigger an immediate SIGTERM + Telegram Alert.

### 4. DMS-4: PII Pre-Filter (P1)
- Logic: Run local regex scan for email, SSN, CC, Phone before passing JSON to LLM.
- Action: If PII found -> strip PII in memory -> log to dissent_log.md -> mark output as "[PII STRIPPED]".

### 5. DMS-5: Watchdog Timer (P1)
- Logic: Instantiate a 300-second wall-clock timer upon process start.
- Action: If timer expires, force SIGTERM + write to blackboard/dissent_log + send Telegram alert.

---
### INSTRUCTION TO CLAUDE:
Implement dossier_intelligence_bot.py following this plan. You are authorized to use safe_cli_gate.py for all MCP tool calls.
