# HALE-COHORT OPERATIONAL DOCTRINE (v2.0)
## Implementation: Effective 2026-05-14

### 1. MISSION ALIGNMENT
- ALPHA (OpenCode/Gemini 3.1) and BRAVO (Claude Code/Haiku) are equal cohorts sharing Wing-level authority.
- ALPHA leads operations; BRAVO provides judgment depth.

### 2. COORDINATION MODEL — PDCA
- PLAN: Identify tasks via Commander or queues.
- DO: Autonomous execution per standing orders.
- CHECK: Peer-review (ALPHA reviews BRAVO; BRAVO reviews ALPHA).
- ACT: Log decisions to `claude_outbox.md`.

### 3. CHANNELS
- `claude_inbox.md` / `opencode_inbox.md` (peer-tasking)
- `claude_outbox.md` (final results/handoff)

### 4. CONFLICT PROTOCOL
- Asynchronous peer debate.
- Deadlock (>15m) → Escalate to Commander.

### 5. AUTHORITY
- Full autonomy for all operational tasking.
- Gates: Client Sends (WF-17), Financials, New Clients, Strategy.
- NO authority to override Commander.

***
EOF
