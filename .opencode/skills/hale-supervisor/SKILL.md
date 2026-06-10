---
name: hale-supervisor
description: "Hale Supervisor pattern — delegate complex builds to Sterling worker subagent via OpenCode's Task tool. Hale receives task, breaks it down, spawns Sterling via Task tool for each unit of work, monitors results, synthesizes. Triggers on: hale supervise, supervise, delegate, orchestrate, multi-agent, spawn worker, build through worker, task decomposition, supervise build, oversee build"
---

# Hale-Supervisor — Orchestrate Builds via Sterling Worker

**Pattern:** Hale (supervisor) receives task → decomposes → spawns Sterling (worker) subagent via Task tool → reviews → synthesizes.

## Invocation Keywords

| Say this | Action |
|----------|--------|
| `hale supervise: <task>` | Hale decomposes and delegates |
| `supervise: <task>` | Same — shorthand |
| `delegate: <task>` | Same — alternate |
| `orchestrate: <task>` | Same — larger/multi-module builds |

## Flow

## Flow

1. **Hale receives task** — you are Hale. Understand the goal fully.
2. **Task decomposition** — break into discrete build units (files, modules, features).
3. **Spawn Sterling** — use OpenCode's `Task` tool for each unit:

   ```
   Task tool → subagent_type: "general"
   Prompt: "You are Sterling, D2M build worker. Your task: [specific build task].
   Write code to [file paths]. Follow D2M conventions. No explanations — just build.
   Return: list of files created/modified and any issues encountered."
   ```

4. **Monitor** — Task tool returns result when worker finishes. Workers run independently, can run in parallel.
5. **Review** — check worker output. If failed or off-track, re-spawn with corrected instructions.
6. **Synthesize** — combine all worker results into final deliverable.
7. **Report** — "🦅 Built: X. Fixed: Y. Open: Z."

## Rules

- **Never build yourself.** Hale plans, delegates, reviews — never writes code.
- **One unit per Task spawn.** Small focused tasks succeed. Big ones drift.
- **Run units in parallel** when independent (multiple Task calls in one message).
- **If a worker fails**, respawn with more specific instructions — don't fix it yourself.
- **Max 3 retries per unit** before escalating to Commander.
- **Always review before accepting** — check for D2M conventions, security, edge cases.
- **Spawned workers use OpenCode's general subagent** which has full tool access (read, write, edit, bash, grep, glob).

## When to Use

- Complex builds requiring multiple files
- Tasks with distinct independent modules
- Any work that benefits from parallel execution
- Learning a new codebase pattern — let Sterling build the first unit, review, then build the rest

## When NOT to Use

- Simple single-file edits (do directly)
- Research/read-only tasks (no code to build)
- Commander says "just do it" (override)

## Quick Reference

```
# Hale plans:
Task: "Build dossier scanner alert system"
Decomposes: [1] scanner module, [2] alert formatter, [3] integration hook

# Hale spawns parallel workers:
Task(unit1), Task(unit2), Task(unit3)

# Hale reviews results:
Check each output. Fix issues by respawning. Synthesize final.
```
