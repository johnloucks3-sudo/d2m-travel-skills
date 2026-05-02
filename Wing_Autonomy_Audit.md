# Wing Autonomy Audit - Self-Healing Mandate

## Overview
Initiated 2026-05-01: A wing-wide mandate to replace blind "death spiral" retry patterns with intelligent, self-healing loops that include diagnosis, programmatic fix, and limited-retry-to-escalation flow.

## Upgraded Components

| Component | Error Modes Handled | Escalation Logic | Status |
| :--- | :--- | :--- | :--- |
| `core/self_healing.py` | Rate-limit (429), Auth errors | Decorator: 1 retry → Escalate | COMPLETED |
| `OpsCenter/nexus.py` | API Connection/Timeout | Decorated `dispatch_to_claude`/`opencode` | COMPLETED |
| `core/mcp/travel_mcp_server.py` | Scraping/Stealth failure | Decorated scraper tools | COMPLETED |

## Escalation Logic
All self-healing loops now follow this deterministic flow:
1. `try`: Execute task.
2. `except`: Diagnose error (categorize: Auth, Rate-Limit, Module/Network).
3. If fixable: Apply programatic fix (e.g., backoff, rotation).
4. `retry`: Exactly one (1) attempt post-fix.
5. If still failed: Transition to `ESCALATED` state. No infinite loops.
