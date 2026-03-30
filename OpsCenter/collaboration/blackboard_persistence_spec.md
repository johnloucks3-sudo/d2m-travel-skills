# BLACKBOARD PERSISTENCE SPEC
# Date: 2026-03-30 | Author: Claude Sonnet 4.6
# Status: AWAITING COMMANDER APPROVAL — no code written yet
# Principle: Read everything first, code second. Extend what exists, don't duplicate.

---

## WHAT EXISTS (discovered by reading docs)

Six init files already in use — all paste-in or auto-load pattern:

| Entry Point | File | How it loads |
|-------------|------|--------------|
| Claude Code / YOGA | CLAUDE.md | Auto-loaded by Claude Code on every session |
| Claude Desktop / Chromebook | OpsCenter/CLAUDE_DESKTOP_INIT.md | Commander pastes at session start |
| Goose | OpsCenter/GOOSE_INIT.md | Commander pastes at session start |
| Termius / SSH | .bashrc | Executes on every login |
| Telegram | task_processor.py | Hale reads on every message |
| Session checkpoint | session_autosave_latest.md | Written by Claude at session end (already exists) |

The pattern is already consistent. No new architecture needed.
The blackboard just needs to be injected into what already exists.

---

## SOLUTION: blackboard_sync.py

One lightweight script. Runs on a systemd timer (every 5 minutes).
Reads blackboard.md → extracts current state summary → injects into all six files.

### What it injects (blackboard summary block)

```
## BLACKBOARD STATE (auto-updated — do not edit manually)
Last sync: [timestamp]
Claude budget: GREEN | YELLOW | RED
Active tasks: [count] — [brief description]
Last Deepseek ruling: [task_id or NONE]
Open items: [bullet list from japan_departure_checklist or routing_log]
Standing directives: [any Commander overrides active]
## END BLACKBOARD STATE
```

Each init file gets this block injected between two sentinel comments:
  <!-- BLACKBOARD_START --> ... <!-- BLACKBOARD_END -->
  # BLACKBOARD_START ... # BLACKBOARD_END (for markdown files)

Script finds the sentinels and replaces content between them.
If sentinels don't exist yet, appends them to the file.
Append-safe — never corrupts existing content.

---

## SIX ENTRY POINT IMPLEMENTATIONS

### 1. CLAUDE.md — Claude Code on YOGA
Mechanism: Claude Code auto-reads CLAUDE.md on every session start.
Action: blackboard_sync.py injects summary block at bottom of CLAUDE.md.
Result: Every Claude Code session starts with current blackboard state.
No Commander action required.

### 2. CLAUDE_DESKTOP_INIT.md — Claude Desktop / Chromebook
Mechanism: Commander pastes this file at start of Desktop/Chromebook session.
Action: blackboard_sync.py keeps the blackboard block current in this file.
Result: When Commander pastes the init, blackboard state is already fresh.
Commander action: paste init file as normal — blackboard is already in it.

### 3. GOOSE_INIT.md — Goose
Mechanism: Commander pastes this file at Goose session start.
Action: blackboard_sync.py injects summary block into GOOSE_INIT.md.
Also adds: "Read collaboration/blackboard.md for full state" line.
Result: Goose knows blackboard state from first message.

### 4. .bashrc MOTD — Termius / SSH
Mechanism: .bashrc executes on every SSH login.
Action: blackboard_sync.py writes a summary to ~/thunderbird_status.txt.
.bashrc already has (or gets) one line added: cat ~/thunderbird_status.txt
Result: Every Termius login shows current blackboard state before prompt.
One-time .bashrc edit — never touched again.

### 5. Telegram — Hale
Mechanism: task_processor.py _build_hale_system_prompt() already runs on every message.
Action: Add one call to _build_hale_system_prompt(): read blackboard.md and
inject summary into Hale's context.
Result: Hale is always aware of blackboard state.
On first message of session, Hale announces: "Blackboard active — [N] tasks, budget [status]"

### 6. session_autosave_latest.md — Session Continuity
Mechanism: Already written at session end (existing protocol).
Action: Align checkpoint format with blackboard schema.
blackboard_sync.py reads session_autosave_latest.md and pulls
"open items" and "next priorities" into blackboard.md automatically.
Result: Session checkpoint and blackboard stay in sync bidirectionally.

---

## blackboard_sync.py — WHAT IT DOES (no code yet)

Reads:
  - collaboration/blackboard.md (source of truth)
  - collaboration/rate_limit_status.md (Claude budget)
  - collaboration/routing_log.md (last N entries)
  - session_autosave_latest.md (open items)

Writes:
  - Injects blackboard block into CLAUDE.md
  - Injects blackboard block into OpsCenter/CLAUDE_DESKTOP_INIT.md
  - Injects blackboard block into OpsCenter/GOOSE_INIT.md
  - Writes ~/thunderbird_status.txt (for .bashrc MOTD)
  - Logs sync to collaboration/routing_log.md

Runs as: thunderbird-blackboard-sync systemd timer, every 5 minutes.
Falls back gracefully if any file is missing — never crashes.
Zero LLM calls — pure Python file I/O.

---

## ONE-TIME SETUP REQUIRED

1. Add sentinel comments to CLAUDE.md, CLAUDE_DESKTOP_INIT.md, GOOSE_INIT.md
2. Add one line to .bashrc: cat ~/thunderbird_status.txt 2>/dev/null
3. Add blackboard.md read to _build_hale_system_prompt() in task_processor.py
4. Write blackboard_sync.py
5. Install as systemd timer: thunderbird-blackboard-sync.timer (every 5 min)
6. Add to watchdog SERVICES monitoring

---

## WHAT DOES NOT CHANGE

- CLAUDE.md content and structure — only adds blackboard block at bottom
- GOOSE_INIT.md content — only adds blackboard block
- CLAUDE_DESKTOP_INIT.md content — only adds blackboard block
- task_processor.py handler logic — one read call added to system prompt builder
- session_autosave_latest.md format — sync reads it, doesn't rewrite it
- .bashrc — one line appended, nothing else

---

## JAPAN RELEVANCE

With blackboard_sync.py running every 5 min:
- Commander opens Termius in Tokyo → sees YOGA status immediately on login
- Commander opens Claude.ai on Chromebook → pastes CLAUDE_DESKTOP_INIT.md → blackboard state is current
- Goose runs a session → sees active tasks without Commander explaining context
- Hale always knows what's on the board

No manual sync. No stale context. Works across all time zones and devices.

---
*Spec complete. No code written. Awaiting Commander approval.*
