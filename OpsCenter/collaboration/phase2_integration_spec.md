# PHASE 2 — BLACKBOARD INTEGRATION SPEC
# task_processor.py modifications to connect Telegram → Blackboard
# Author: Claude Sonnet 4.6 | Date: 2026-03-30
# Status: AWAITING COMMANDER APPROVAL
# NO CODE CHANGES MADE — spec only

---

## WHAT EXISTS TODAY

Telegram → telegram_pager_c2.py → 01_TASK_QUEUE.json → task_processor.py (Hale)
                                                               ↓
                                          HANDLERS dispatch table routes to:
                                          - _handle_commander_message()  ← Gemini 3.1 Pro
                                          - _handle_innovation_scan()
                                          - _handle_morning_briefing()
                                          - _queue_for_claude_max()      ← 03_CLAUDE_MAX_QUEUE.json

Blackboard lives in collaboration/ — task_processor.py has zero awareness of it.

---

## WHAT NEEDS TO CHANGE — 4 TARGETED MODIFICATIONS

### MOD 1: Add blackboard_router() function
New function inserted BEFORE the HANDLERS dispatch table.

Purpose: Inspect incoming task and decide if it belongs on the blackboard
instead of (or in addition to) normal Hale routing.

Logic:
  IF task_type == "commander_message":
    AND content contains blackboard trigger keywords
    (research, synthesize, analyze, compare, fuse, incubator, collaboration)
    AND token_estimate > 1000
    → route to blackboard, write to correct inbox file
    → return "BLACKBOARD" signal to process_one()
  ELSE:
    → normal Hale routing (unchanged)

Trigger keywords are configurable — stored in blackboard.md standing directives
so Commander can update without touching code.


### MOD 2: Add rate_limit_checker() function
New function that reads rate_limit_status.md before any Claude routing decision.

Purpose: Enforce the 0600-1800 MT token budget rule automatically.

Logic:
  Read rate_limit_status.md → parse Claude budget status (GREEN/YELLOW/RED)
  Read current MT time
  IF time is 0600-1800 MT AND claude_status != GREEN:
    → force Goose-first routing regardless of task type
    → log routing decision to routing_log.md
  IF commander message contains "/use claude":
    → override budget check, route to Claude regardless
    → log override to routing_log.md
  ELSE:
    → normal routing per capability table

This function is called once per task in process_one() before handler dispatch.
Zero LLM cost — pure file read + time check.

### MOD 3: Add _write_blackboard_task() helper
New helper function for writing properly formatted task entries to inbox files.

Purpose: Standardize all inbox writes — no freeform entries, always valid schema.

Takes:
  - target_inbox: path to inbox file
  - task_id, submitted_by, task_type, priority, token_estimate
  - pii flag (bool) — if True, hard-blocks Deepseek/Groq routing
  - context_files list
  - instructions string
  - output_destination path
  - deadline

Writes JSON block to target inbox file (append mode).
Appends entry to routing_log.md.
Updates blackboard.md active task count.

### MOD 4: Add "blackboard_task" to HANDLERS dispatch table
New handler: _handle_blackboard_task()

Purpose: When Hale receives a task tagged task_type: "blackboard_task",
she writes it to the correct inbox and notifies Commander via Telegram.

Behavior:
  1. Call blackboard_router() to determine target inbox
  2. Call rate_limit_checker() to determine which model gets it
  3. Call _write_blackboard_task() to write the formatted entry
  4. Send Telegram notification: "Task [ID] queued for [MODEL]. Say 'Read your inbox
     and execute' to trigger."
  5. Log to routing_log.md

This is the ONLY new handler. Everything else in HANDLERS is unchanged.


---

## WHAT DOES NOT CHANGE

- run_daemon() — unchanged
- process_one() — only addition is one rate_limit_checker() call at top
- All existing HANDLERS — untouched
- telegram_pager_c2.py — untouched
- 01_TASK_QUEUE.json format — untouched
- 03_CLAUDE_MAX_QUEUE.json — untouched
- Morning briefing, innovation scan, FPD alert, sentinel sweep — all untouched
- Hale-Loop poll interval — unchanged

Blackboard is additive. Nothing existing breaks.

---

## TELEGRAM TRIGGER PROTOCOL (no code changes required)

Commander sends via Telegram to COS:
  "Research [topic] — blackboard task"

Hale detects "blackboard task" suffix, calls blackboard_router(),
writes to correct inbox, sends back:
  "Task BB-[ID] queued for Goose. Budget: YELLOW.
   Say 'Read your inbox and execute' to Goose to trigger."

Commander then goes to Goose and says: "Read your inbox and execute."
Goose reads opencode_inbox.md, executes, writes to opencode_output.md.
If claude_finish: true — Commander then triggers Claude.

One Telegram message initiates the full cycle.
Commander trigger to each agent is still required — that is by design.

---

## DEEPSEEK ARBITRATION VIA TELEGRAM

If Commander wants to invoke arbitration:
  "Arbitrate — [brief description of conflict]"

Hale detects "arbitrate" keyword, writes conflict entry to deepseek_inbox.md,
sends back: "Arbitration request written. Trigger Deepseek to rule."

---

## PHASE 2 IMPLEMENTATION ORDER

1. Write rate_limit_checker() — simplest, standalone, zero risk
2. Write _write_blackboard_task() helper — pure file I/O, no routing logic
3. Write blackboard_router() — routing logic, testable independently
4. Add _handle_blackboard_task() to HANDLERS — final wire-up
5. Add rate_limit_checker() call to process_one() — last step, after all above tested

Each step is independently testable before the next begins.
No step touches existing handler logic.

---

## SUCCESS CRITERIA FOR PHASE 2

- Commander sends "Research X — blackboard task" via Telegram
- Hale routes it to correct inbox without Commander specifying model
- rate_limit_status.md governs routing automatically during 0600-1800 MT
- routing_log.md records every decision
- Existing Hale-Loop operations continue unaffected
- Zero new LLM API calls added to routing logic (pure Python)

---
*Phase 2 spec complete. Awaiting Commander approval to begin code.*
