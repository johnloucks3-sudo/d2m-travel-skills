# Command Signal Channel — Commander ↔ JET ↔ TALON
## 2026-05-16 | Dreams2Memories Travel, LLC

**Purpose:** Out-of-band communication when Telegram is degraded or unavailable.
**Protocol:** File-based. Writer appends, reader detects new signals at session start.

---

## Signal Format

```
## SIGNAL: [TYPE] | [FROM] | [YYYY-MM-DD HH:MM MT]
status: UNREAD | ACKED | COMPLETE
body: |
  Free-form message content. Multiple lines OK.
  Commander speaks at intent level.
```

## Signal Types

| Type | When | From |
|------|------|------|
| `ALERT` | Something broke or needs immediate attention | Any |
| `TASK` | Task assignment with clear outcome | Commander |
| `DECISION` | Commander decision on pending question | Commander |
| `QUERY` | Request for information or status | Any |
| `ACK` | Acknowledgment of receipt | Any |

## Actors

| Signal | Reads | Writes |
|--------|-------|--------|
| **Commander** (John Loucks) | Session start, on notification | ALERT, TASK, DECISION |
| **JET** (OpenCode) | Session start + background poll | ACK, QUERY, findings |
| **TALON** (Claude MAX) | Via watcher, dispatch | ACK, analysis |

## Protocol

1. **Writer** appends a new `## SIGNAL:` block at the bottom of this file
2. **Reader** detects new signals by scanning for `status: UNREAD`
3. **Reader** marks `status: ACKED` after reading
4. **Reader** marks `status: COMPLETE` after action taken
5. **Avoid deleting or rewriting** the file — append only

## Polling

- **JET** checks for UNREAD signals at every session start (via AGENTS.md instruction)
- **TALON** (Claude) checks via the watcher service when this file changes
- **Commander** reads this file via filesystem (Termius/zfold)

---

## Signal Log

<!-- New signals appended below this line -->

