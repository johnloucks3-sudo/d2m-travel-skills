# AG Write-Back Capability — Design Plan

**Status:** DRAFT — for AG review and Commander approval
**Owner:** Hale (Victory)
**Date:** 2026-07-22

---

## Problem

AG (Hale-AG / Antigravity) can receive tasks via `contact_ag()` and write deliverables to absolute filesystem paths, but has **no write-back path to shared memory** — the CC memory directory at `~/.claude/projects/-home-john-Thunderbird/memory/`. This means:

- Facts AG learns, corrections she discovers, or decisions she makes in a session are **not durable** across CC/OC sessions
- The shared memory index (`MEMORY.md`) only gets CC/OC entries — AG's institutional knowledge is lost after her session ends
- Cross-Hale "peer verify" findings have no automatic persistence mechanism

---

## Design

### 1. AG Memory Write API

A new module: `core/memory/ag_memory_write.py` — called by AG at the end of any session where she learns something worth persisting.

**Signature:**
```python
def ag_write_memory(
    memory_type: str,      # "user" | "feedback" | "project" | "reference"
    slug: str,             # kebab-case slug, e.g. "ag_verify_flight_routing"
    name: str,             # human-readable short name
    description: str,      # one-line description for MEMORY.md index
    body: str,             # full markdown body
    tags: list[str] = None # optional cross-reference tags
) -> dict:
    """Write a memory file + update MEMORY.md index."""
```

**Effects:**

1. Writes file to `~/.claude/projects/-home-john-Thunderbird/memory/{type}_{slug}.md`
2. Inserts one-line pointer in `MEMORY.md` under the appropriate section
3. Returns `{"ok": true, "path": "...", "index_line": "..."}`

### 2. AG Session Close Hook

A CLI wrapper AG can call at session end:
```bash
python3 core/memory/ag_memory_write.py --type feedback --slug my_observation \
    --name "My Observation" --description "what I learned" --body @body_file.md
```

This means AG doesn't need to import Python — she just runs a shell command with a prepared body file.

### 3. File Format — Identical to CC

AG writes exactly the same YAML-frontmatter format CC uses:

```markdown
---
name: my-observation
description: What AG discovered about X
metadata:
  node_type: memory
  type: feedback
  origin: ag
  engine: gemini-3.1-pro
---

What AG learned, in markdown. Links to other memories with [[slug]].

**Why:** ...
**How to apply:** ...
```

The `origin: ag` field lets the system distinguish AG-authored memories from CC/OC-authored ones for attribution.

### 4. MEMORY.md Update

`ag_memory_write.py` will:
- Read existing `MEMORY.md`
- Insert a new line under the matching section header (or "AG Memories" section if no match)
- Write back, preserving existing content

### 5. Integration with `contact_ag()`

After `contact_ag()` dispatches and AG writes her deliverable, the caller can optionally trigger AG to also persist any findings to shared memory by including in the task prompt:

> "If you discover anything worth remembering long-term, call: `python3 /home/john/Thunderbird/core/memory/ag_memory_write.py --type ...`"

This is the **opt-in model** — AG decides what's worth persisting, she doesn't dump everything.

---

## Why This Works

| Requirement | How Met |
|---|---|
| Same format & directory as CC | Yes — identical YAML frontmatter, same dir |
| AG can write it | CLI wrapper — no Python import needed |
| Survives clean checkout | Yes — `~/.claude/projects/` is gitignored but that's intentional; CC and OC both mount it |
| CC can read it | Yes — CC loads `MEMORY.md` + files on session start |
| No AG-writes-MEMORY.md directly | No — `ag_memory_write.py` handles the index insert atomically |
| Cross-engine durable | Yes — shared filesystem, not engine-specific store |
| Fail-safe | Corrupt MEMORY.md → writes to `ag_memory_write_errors.log`, no data loss |

---

## Files to Create

| File | Purpose |
|---|---|
| `core/memory/ag_memory_write.py` | API + CLI wrapper |
| `core/memory/ag_memory_write_test.py` | Unit tests |

---

## Files NOT Touched

- `MEMORY.md` — updated by the tool, never manually
- `contact_ag.py` — no changes needed (AG calls the CLI tool from her side)
- Any CC/AG memory files — no migration needed

---

## Open Questions for AG Review

1. **Path permissions:** Can AG (`agy`) running as `john` write to `~/.claude/projects/-home-john-Thunderbird/memory/`? (Should be yes — same user, same filesystem.)
2. **Index contention:** If CC and AG write nearly simultaneously, can `MEMORY.md` corrupt? (Unlikely in practice — these are serialized by the task dispatch pattern.)
3. **AG's side:** Does AG's `agy` CLI permit shell commands that write files outside the repo? (Yes — `--dangerously-skip-permissions` allows it, and `~/.claude/projects/` is on the same filesystem.)
4. **Should AG write-back be opt-in (recommended) or automatic?** Opt-in avoids noise from trivial sessions.
