---
name: ask
description: "Spawn Claude CC (Sonnet) headless with full Wing context. Use for client emails, trip validation, itinerary generation, Wing procedures, anything requiring CLAUDE.md knowledge. Triggers on: /ask, ask claude, ask sonnet, dispatch to claude, claude headless, wing procedure, ask cc"
---

# /ask — Spawn Claude CC Headless (Sonnet)

Dispatch a task to Claude Code (Sonnet) running headless with full Wing context loaded.
Use this when the task requires: Wing procedures, creative chain, client email drafting,
trip validation, itinerary generation, or anything that needs CLAUDE.md knowledge.

## How to invoke

```bash
ask 'task description here'
```

The `ask` command is symlinked to `OpsCenter/ask_wrapper.sh` in `~/.local/bin/`.
Available as **`/ask`** (canonical name) or `ask` (bash command — slash is a doc convention).

## When to use /ask

- Writing a client email (Dani's 6-step chain runs in CC with full Wing context)
- Generating or reviewing an itinerary (CC knows photo requirements, procedures)
- Trip validation (CC runs validate_dossier.py with persona awareness)
- Any time you're about to violate a Wing SO because you don't have that context
- When the task requires voice matching, brand standards, or WF-17 gate compliance

## What happens

1. `ask_wrapper.sh` calls `opencode_sonnet_inline.py`
2. `spawn_sonnet_inline()` spawns `claude -p` with MAX OAuth injected
3. CC receives your task with CLAUDE.md context loaded
4. Output is returned inline and saved to `output/ask_[timestamp].md`

## Example

```bash
ask 'Draft the Kuklinski ARC4-B specialty dining lifecycle email. Client profile in dossiers/. Use Dani 6-step chain. Output the complete HTML email.'
```

## Output location

Results print inline. File saved to `/home/john/Thunderbird/output/`.
