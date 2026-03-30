# BLACKBOARD PERSISTENCE SPEC v2 — NO PASTE REQUIRED
# Date: 2026-03-30 | Author: Claude Sonnet 4.6
# Replaces: blackboard_persistence_spec.md (paste-in model — rejected)
# Principle: Zero Commander action on any entry point. Fully automatic.

---

## KEY DISCOVERY: GOOSE TOM EXTENSION

Goose config.yaml has the "Top Of Mind" (tom) extension already enabled.
It injects context into EVERY Goose turn via:
  GOOSE_MOIM_MESSAGE_FILE = path to a file Goose reads automatically

This is the no-paste solution for Goose.
blackboard_sync.py writes current state to a file.
GOOSE_MOIM_MESSAGE_FILE points to that file.
Goose sees blackboard state on every single message — zero Commander action.

---

## NO-PASTE ARCHITECTURE — ALL SIX ENTRY POINTS

### 1. Claude Code / YOGA
Mechanism: CLAUDE.md auto-loads on every Claude Code session — already working.
Solution: blackboard_sync.py keeps CLAUDE.md blackboard block current.
Commander action: NONE — Claude Code reads it automatically.

### 2. Goose (Desktop)
Mechanism: TOM extension reads GOOSE_MOIM_MESSAGE_FILE on every turn.
Solution: Set GOOSE_MOIM_MESSAGE_FILE=/home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt
          blackboard_sync.py writes current state to blackboard_summary.txt every 5 min.
Commander action: NONE — one-time config.yaml update, then permanent.

### 3. Telegram / Goose Gateway
Mechanism: Goose already has Telegram gateway paired (user_id: 7554895206).
           TOM extension applies to ALL Goose sessions including Telegram.
Solution: Same blackboard_summary.txt via TOM — applies automatically to Telegram too.
Commander action: NONE — falls through from Goose TOM config.

### 4. Termius / SSH
Mechanism: .bashrc executes on every SSH login.
Solution: Add to .bashrc: cat /home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt
Commander action: NONE after one-time .bashrc edit.

### 5. Hale / Telegram C2
Mechanism: _build_hale_system_prompt() runs on every Hale message.
Solution: Add one read of blackboard.md to system prompt builder.
Commander action: NONE — persistent once task_processor.py is updated.

### 6. Claude Desktop / Chromebook / Claude.ai
Mechanism: NO automatic file injection in Claude Desktop or Claude.ai.
           These are web interfaces — cannot read local files automatically.
Honest solution options:
  A. Claude Projects feature — upload blackboard_summary.txt as a Project file.
     Claude.ai reads it on every conversation in that project.
     Commander updates the Project file periodically (or sync script uploads it).
  B. Reverie web interface — when built, serves blackboard state at a URL
     Commander bookmarks it for quick copy.
  C. Telegram bridge — Commander asks Hale "give me blackboard state"
     Hale responds with current state, Commander has it for context.
  D. Accept one paste for web sessions only — paste is 5 lines, not a full init file.

RECOMMENDATION: Option C is zero-paste and works today.
Option A is cleanest long-term — requires Claude Projects setup.

---

## IMPLEMENTATION PLAN — ZERO PASTE

### Step 1: blackboard_sync.py (core engine)
Reads: blackboard.md, rate_limit_status.md, routing_log.md, session_autosave_latest.md
Writes:
  - blackboard_summary.txt (5-10 lines, plain text — Goose TOM + SSH MOTD)
  - CLAUDE.md blackboard block (sentinel-delimited)
  - task_processor.py context (via a sidecar file Hale reads)
Runs: systemd timer every 5 minutes
Cost: Zero LLM calls, pure Python file I/O

### Step 2: Goose TOM config (one-time)
Edit config.yaml — add to tom extension envs:
  GOOSE_MOIM_MESSAGE_FILE: /home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt
Result: Goose sees blackboard on every message, every session, including Telegram gateway.

### Step 3: .bashrc MOTD (one-time, one line)
Append to /home/john/.bashrc:
  cat /home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt 2>/dev/null && echo ""
Result: Every Termius/SSH login shows blackboard state before prompt.

### Step 4: task_processor.py (one-time, surgical)
In _build_hale_system_prompt(): add read of blackboard_summary.txt
Inject into system prompt as "## CURRENT BLACKBOARD STATE"
Result: Hale always knows blackboard state. Can report it on demand.

### Step 5: CLAUDE.md sentinel block (one-time)
Add sentinel comments at bottom of CLAUDE.md:
  # BLACKBOARD_START (auto-updated by blackboard_sync.py — do not edit)
  # BLACKBOARD_END
blackboard_sync.py fills this in on every run.
Result: Claude Code gets current state on every session start.

### Step 6: Claude Desktop / Chromebook (decision required)
Ask Hale via Telegram: "blackboard state" → she reports it → paste 5 lines.
OR set up Claude Project with blackboard_summary.txt as a project file.

---

## blackboard_summary.txt FORMAT (what gets injected everywhere)

```
=== THUNDERBIRD BLACKBOARD [2026-03-30 02:15 MT] ===
Claude budget: YELLOW | Goose: GREEN | Groq: GREEN | Deepseek: GREEN
Active tasks: 3 — SSE migration spec, Phase 3 spec, Japan checklist
Last Deepseek ruling: NONE
Open items: websockets compat test, key rotation (THUNDERBIRD_GOOSE_ARCHITECTURE.md)
Japan departure: April 10 (11 days) — watchdog hardening PRIORITY
Next priority: blackboard_sync.py implementation
================================================
```

Short. Scannable. Works as SSH MOTD, Goose TOM injection, and Hale context.

---

## WHAT STILL REQUIRES ONE PASTE (honest assessment)

Claude Desktop and Claude.ai on Chromebook have no file system access.
The CLAUDE_DESKTOP_INIT.md paste is unavoidable for those surfaces
UNLESS you use Claude Projects (upload blackboard_summary.txt as project file).

For Japan: Telegram → Hale → "give me blackboard state" → copy 8 lines into Claude.ai.
That is the minimum friction path for web surfaces.

---

## ADDITIONAL DISCOVERY: EXPOSED API KEYS

config.yaml contains plaintext:
  - GROQ_API_KEY (same key as in earlier document — already flagged)
  - DEEPSEEK_API_KEY (same key as earlier — already flagged)
  - OPENROUTER_API_KEY
  - POE_API_KEY

These are in a local config file, not a public repo — lower risk than git exposure.
But rotate all of these before Japan departure.
Commander acknowledged manual rotation — tracking here for completeness.

---
*Spec v2 complete. No code written. Awaiting Commander approval.*
