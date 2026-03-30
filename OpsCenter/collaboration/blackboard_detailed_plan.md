# D2M OPSCENTER — BLACKBOARD DETAILED IMPLEMENTATION PLAN
**Author:** Claude Sonnet 4.6 | **Date:** 2026-03-30
**Based on:** blackboard_implementation_plan.md (Goose-revised)
**Status:** AWAITING COMMANDER APPROVAL

---

## CORE OPERATING REALITY

Claude operates on a daily token budget with a hard constraint:
- **0000–0500 MT** — Claude's primary work window (batch, research, synthesis)
- **0600–1800 MT** — Commander's operational hours; Claude usage minimized
- **0500–0600 MT** — handoff window; Claude writes outputs, Goose picks up

Any task that can be initiated before 0500 and completed before 0600 is a
"clean Claude task." Anything else defaults to Goose-first, Claude-finish.

---

## PART 1: DIRECTORY STRUCTURE & FILE INITIALIZATION

### 1.1 Full Directory Layout
```
~/Thunderbird/OpsCenter/collaboration/
  blackboard.md              ← master shared state (all agents read first)
  claude_inbox.md            ← Commander or Goose queues tasks for Claude
  claude_output.md           ← Claude writes all completed work here
  goose_inbox.md             ← Commander or Claude queues tasks for Goose
  goose_output.md            ← Goose writes completed work here
  deepseek_inbox.md          ← arbitration requests only
  deepseek_ruling.md         ← Deepseek arbitration decisions
  conflict_log.md            ← all disputes + resolutions, append-only
  routing_log.md             ← every task routed, model used, outcome
  rate_limit_status.md       ← manually updated; current token budgets
```

### 1.2 Standard Task Schema (all inbox files — JSON block format)

```json
{
  "task_id": "20260330-0142-C",
  "submitted_by": "COMMANDER | GOOSE | CLAUDE",
  "submitted_at": "2026-03-30T01:42:00MT",
  "task_type": "classify | summarize | research | synthesize | code | extract | client_output | arbitrate",
  "priority": "HIGH | NORMAL | LOW",
  "token_estimate": 500,
  "pii": false,
  "context_files": ["/path/to/file1.md"],
  "instructions": "Plain language description of exactly what to do.",
  "output_destination": "/home/john/Thunderbird/OpsCenter/collaboration/claude_output.md",
  "deadline": "2026-03-30T05:00:00MT"
}
```

**token_estimate** is required — this is how the router decides if Claude
has budget remaining or if Goose takes the task during operational hours.

**pii: true** hard-blocks routing to Deepseek or Groq. No exceptions.

### 1.3 Output Header (all output files — prepend to every entry)

```
---
AGENT: Claude Sonnet 4.6
TASK_ID: 20260330-0142-C
COMPLETED_AT: 2026-03-30T02:15:00MT
CONFIDENCE: HIGH | MEDIUM | LOW
---
[output content below]
```


---

## PART 2: ROUTING RULES — TOKEN-AWARE VERSION

### 2.1 Primary Decision Tree

```
TASK ARRIVES
    │
    ├─ PII: TRUE? ──────────────────→ Goose or Claude only. Never Deepseek/Groq.
    │
    ├─ Time: 0600–1800 MT?
    │       │
    │       ├─ token_estimate > 1000? → GOOSE first, Claude finish if needed
    │       └─ token_estimate ≤ 1000? → Groq if classify/summarize, else Goose
    │
    ├─ Time: 0000–0500 MT?
    │       │
    │       ├─ Claude budget remaining? → Route per capability table below
    │       └─ Claude depleted?         → Gemini Flash fallback (existing router)
    │
    └─ Dispute/conflict? ─────────────→ Deepseek inbox (no PII)
```

### 2.2 Capability Routing Table

| Task Type | Primary | Fallback | Never |
|-----------|---------|----------|-------|
| classify / keyword / sentiment | Groq | Goose | Claude (wasteful) |
| summarize < 500 tokens | Groq | Goose | Claude (wasteful) |
| web research / real-time | Goose | Claude | Groq |
| structured data extraction | Deepseek | Goose | — |
| code analysis (no PII) | Deepseek | Goose | — |
| long-context synthesis | Claude | Goose | Groq |
| client-facing writing | Claude | Goose draft + Claude finish | Deepseek/Groq |
| strategic reasoning | Claude | Goose | Groq |
| inter-agent arbitration | Deepseek | Commander | — |
| intel scans (daily/weekly) | Goose | Gemini Flash | Claude (reserved) |

### 2.3 Claude Budget Guard

Before any Claude task during 0600–1800 MT, check rate_limit_status.md.
If Claude is at >80% daily usage → mandatory Goose-first routing regardless of task type.
Exception: Commander explicitly types `/use claude` to override.


---

## PART 3: OPERATING CYCLES IN DETAIL

### 3.1 Standard Task Cycle (step by step)

1. Commander or Goose writes JSON task block to target inbox file
2. Commander issues one-line trigger: "Read your inbox and execute"
3. Agent reads blackboard.md first (shared state), then inbox
4. Agent reads any context_files listed in the task
5. Agent executes task
6. Agent writes output to output_destination with standard header
7. Agent appends one-line entry to routing_log.md:
   `[timestamp] | task_id | agent | task_type | status: COMPLETE`
8. Commander reviews before any client-facing output ships

### 3.2 Goose-First / Claude-Finish Cycle (0600–1800 MT)

1. Task arrives requiring Claude-level quality
2. Task written to goose_inbox.md with flag: `claude_finish: true`
3. Goose executes, writes draft to goose_output.md
4. If Claude budget available and task is client_output or synthesis:
   - Task written to claude_inbox.md with context_file = goose_output.md
   - Claude reads Goose draft, refines for D2M voice, writes to claude_output.md
5. If Claude budget not available:
   - Goose output is final; Commander reviews directly
6. routing_log.md records both legs of the handoff

### 3.3 Arbitration Cycle (Deepseek)

1. Conflict detected between two agent outputs
2. Either agent or Commander writes to conflict_log.md:
   `[timestamp] | CONFLICT | task_id | agent_A claim | agent_B claim`
3. Arbitration task written to deepseek_inbox.md (no PII — hard check first)
4. Commander triggers: "Read deepseek_inbox and issue ruling"
5. Deepseek writes ruling to deepseek_ruling.md with:
   - Ruling: AGENT_A | AGENT_B | SPLIT | ESCALATE_TO_COMMANDER
   - Rationale: factual basis for decision
   - Confidence: HIGH | MEDIUM | LOW
6. If Confidence: LOW → automatic escalation to Commander
7. conflict_log.md updated with resolution
8. Winning output adopted; routing_log.md records outcome

### 3.4 Blackboard State File (blackboard.md) — Updated When:

- Session starts (Commander pastes current state)
- Any task status changes to COMPLETE or BLOCKED
- Rate limit status changes
- Deepseek issues a ruling
- Standing orders change


---

## PART 4: DEEPSEEK ARBITRATION — DETAILED RULES

### 4.1 Arbitration Scope
Deepseek rules on:
- Factual conflicts between Claude and Goose outputs
- Routing disputes (ambiguous task type assignment)
- Schema/format disagreements in shared files
- Conflicting recommendations where both agents have valid cases

Deepseek does NOT rule on:
- D2M brand voice or client communication tone (Claude authority)
- Commander intent or strategic priorities (Commander authority)
- Tasks involving PII (hard fence — no arbitration if PII present)

### 4.2 Arbitration Request Format (deepseek_inbox.md entry)

```
ARBITRATION REQUEST
task_id: [original task_id]
requested_by: CLAUDE | GOOSE | COMMANDER
submitted_at: [ISO timestamp]
pii: FALSE (must verify before submitting)

AGENT_A OUTPUT SUMMARY:
[Claude's position — 3 sentences max]

AGENT_B OUTPUT SUMMARY:
[Goose's position — 3 sentences max]

SPECIFIC QUESTION FOR DEEPSEEK:
[One clear question Deepseek must answer]
```

### 4.3 Deepseek Ruling Format (deepseek_ruling.md entry)

```
RULING
task_id: [original task_id]
ruling_at: [ISO timestamp]
decision: AGENT_A | AGENT_B | SPLIT | ESCALATE
confidence: HIGH | MEDIUM | LOW
rationale: [2-3 sentences factual basis]
action_required: [what happens next]
```

### 4.4 Escalation Triggers
Deepseek auto-escalates to Commander when:
- Confidence is LOW
- Conflict involves strategic or brand decisions
- Neither agent position is factually supportable
- PII was detected in submitted materials (flag and halt)

---

## PART 5: GUARDRAILS & AUDIT

### 5.1 PII Fence
- pii: true blocks Deepseek and Groq routing — no exceptions, no overrides
- Task files with PII tagged explicitly at schema level
- If PII discovered mid-task in Deepseek/Groq: halt, log, escalate to Commander

### 5.2 Append-Only Rule
- conflict_log.md — append only, never edit existing entries
- routing_log.md — append only, never edit existing entries
- deepseek_ruling.md — append only (rulings are permanent record)
- Inbox/output files — may be cleared weekly by Commander only

### 5.3 Human-in-the-Loop Gates
- All client-facing output: Commander review before send (WF-17 gate unchanged)
- HIGH priority tasks: Commander acknowledgment before execution
- Deepseek rulings: advisory until Commander confirms
- Any ruling with confidence LOW: mandatory Commander review

### 5.4 Weekly Maintenance (Commander)
- Review routing_log.md for anomalies or inefficient routing
- Update rate_limit_status.md with current budget baselines
- Archive and clear inbox/output files older than 7 days
- Note any routing rule adjustments needed in blackboard.md


---

## PART 6: PHASED IMPLEMENTATION

### Phase 1 — This Week (Manual / No Code)
**Goal:** Prove the cycle works with Commander as manual router

Steps:
1. Create all files in collaboration/ with correct headers (30 min)
2. Create rate_limit_status.md with current Claude/Groq/Deepseek baselines
3. Run one complete standard task cycle end-to-end (test task, no client data)
4. Run one complete arbitration cycle (fabricated conflict, test Deepseek ruling)
5. Commander validates routing_log.md and conflict_log.md look correct
6. Adjust schema fields based on what Phase 1 reveals

Success criteria: Commander can trigger any agent with one line and output
appears in the correct file within expected time.

### Phase 2 — 30 Days (Semi-Automated)
**Goal:** Reduce Commander routing decisions to near-zero for standard tasks

Steps:
1. Add token_estimate field to all Thunderbird task generation points
2. Build routing_decision() function in task_processor.py using capability table
3. Auto-populate correct inbox file based on routing decision
4. Commander still triggers agents manually — automation is routing only
5. Rate limit tracking automated via daily cron writing to rate_limit_status.md
6. First live parallel research: Goose + Claude same prompt, Deepseek fuses output

Success criteria: 80% of tasks routed correctly without Commander intervention.

### Phase 3 — 90 Days (Evaluate Formal Frameworks)
**Goal:** Decide if CrewAI/LangGraph/Google ADK adds value

Steps:
1. Review 90 days of routing_log.md data for patterns
2. Identify task types where current routing still fails or wastes budget
3. Evaluate Google ADK for Goose-side orchestration (Gemini-native)
4. Evaluate CrewAI only if role-based collaboration complexity grows
5. Do not add framework complexity unless routing_log data justifies it

Success criteria: Data-driven decision on whether framework adoption is warranted.

---

## PART 7: INTEGRATION WITH EXISTING THUNDERBIRD ARCHITECTURE

This blackboard layer sits ON TOP of existing systems — nothing is replaced:

```
Existing:  Telegram → telegram_pager_c2.py → 01_TASK_QUEUE.json → Hale (Gemini)
                                                                         ↓
                                                           03_CLAUDE_MAX_QUEUE.json → Claude Code

New layer: Commander → collaboration/[agent]_inbox.md → Agent executes → [agent]_output.md
                                                              ↓
                                                   routing_log.md + blackboard.md
```

The blackboard collaboration/ directory handles RESEARCH, SYNTHESIS, and
INCUBATOR tasks. It does not replace the existing operational task queue.
Hale-Loop continues unchanged. Git commits, Gmail, TESS remain Claude Code's domain.

---

## APPENDIX: FILE TEMPLATES TO CREATE IN PHASE 1

**blackboard.md header:**
```
# D2M BLACKBOARD — SHARED STATE
Last updated: [timestamp] by [agent/COMMANDER]
Claude budget status: [GREEN/YELLOW/RED]
Active tasks: [count]
Last Deepseek ruling: [task_id or NONE]
Standing directives: [any Commander overrides]
---
SESSION LOG (append below):
```

**rate_limit_status.md header:**
```
# RATE LIMIT STATUS
Updated: [timestamp]
Claude Sonnet: [tokens used today / daily limit] — [GREEN/YELLOW/RED]
Groq: [requests today / RPM limit]
Deepseek: [tokens used today]
Goose: [no hard limit — preferred during 0600-1800 MT]
---
```

---
*Detailed plan complete. Awaiting Commander approval before Phase 1 execution.*
