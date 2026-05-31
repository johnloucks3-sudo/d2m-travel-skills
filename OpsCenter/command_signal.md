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


## SIGNAL: TEST | JET | 2026-05-16 21:58 MT
status: COMPLETE
body: |
  Signal channel verified. Commander ↔ JET ↔ TALON communication path is live.
  Protocol: append signal at bottom of file, reader scans for status: UNREAD.
  This is a test signal. Marked COMPLETE.

---

## SIGNAL: ALERT | JET | 2026-05-31 07:45 MT
status: ACKED
body: |
  T2-COMMS-BUILD-20260518: Hard stop (2026-05-23) has passed. 3 deferred items still pending with Hale-CC:
  ⏳ A: core/comms/thunderbird_signal_docker.py — signal-cli Docker image build (deferred)
  ⏳ B: deploy/systemd/thunderbird-signal-gw.service — systemd service unit (deferred)
  ⏳ C: core/comms/thunderbird_signal_gw.py — ConversationBridge fix (deferred)
  
  Per instructions (line 38): "If you see them in your inbox after this date, escalate to Commander via Telegram."
  This signal serves as the escalation. Commander, please evaluate whether deferred items are worth completing or if T2 Hale Seamless Comms should be downgraded to omit Signal gateway.

---
## SIGNAL: COS-DIRECTIVE | COMMANDER → HALE | 2026-05-31 07:58 MT
status: COMPLETE
completed: 2026-05-31T09:30:00Z
body: |
  Commander to Hale (COS, SES-6):
  
  "Ensure correct persona routing and gate check, then build. Convene a staff meeting if needed."
  
  Context: 4 new capability missions produced today. CC reviewed and found issues.
  
  Routing assignments:
  - M-088 WF-7 Pipeline (HOLD — 2 blockers) → Sterling A7
  - M-089 CronCreate (HOLD — all 38 cron expressions wrong) → Sterling A7 + ELON A12
  - M-090 Worktree Sweep (CONDITIONAL PASS) → Reyes A8
  - M-091 Schema Agents (PASS) → Dembe A2
  
  Detail in wing_comms.md under "COMMANDER DIRECTIVE" heading.
  
  Hale actions requested:
  1. Route each mission to correct persona
  2. Gate check fixes before build
  3. Convene staff meeting if cross-persona coordination needed
  4. Authorize build after gate checks pass
  5. Notify Commander when each clears gate
