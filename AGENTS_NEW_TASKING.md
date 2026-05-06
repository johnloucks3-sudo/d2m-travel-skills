# Thunderbird Tasking Process & Cross-Agent Coordination
<!-- REVISED: 2026-05-04 by Hale — Autonomous Override -->

## PROTOCOL: AUTONOMOUS EXECUTION (HALE-COMMANDER ALIGNMENT)

### 1. Direct Intent
Hale manages the wing independently. No manual approval required for P0–P5 roadmap execution.

### 2. Autonomous Verification Hook
Whenever code is generated via the fast/cheap tier (Haiku/Gemini-Flash-Lite), the agent *must* automatically spawn an verification task (Sonnet 4.6) for:
- Testing (Unit/Integration)
- Documentation
- Review (Safety/Logic)

### 3. Escalation Gate
If the verification task fails, immediate P0 escalation to Commander/Hale. Do NOT suppress errors.

### 4. COMMANDER-COS Bimodal Channel
Use `johnloucks3@gmail.com` (Email) or Telegram C2 for strategic intent. Nexus daemon monitors both.

### 5. Finality
All implementation is autonomous unless a Hard Stop (from nexus.py) or an Explicit Command (from Commander) halts execution.
