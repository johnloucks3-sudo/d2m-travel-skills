# BUILD SPEC: State Bridge — Session Continuity Daemon

**Mission:** MISSION-172
**Builder:** Opus (headless, via ask-opus)
**Priority:** P1
**Hale Status:** Spec written 2026-06-08, build pending

---

## Problem

Every OpenCode session starts from scratch. The agent reads the blackboard and mission board — a static snapshot — but has no narrative of prior sessions. What decisions were made? What half-built files are dirty? What Commander preferences changed last week that the system still violates? This costs minutes per session in context recovery.

## Solution

A persistent daemon that lives between sessions, tracks state evolution in SQLite, and produces a structured "State Briefing" injected on session startup.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  state_bridge_daemon.py  (persistent service)       │
│  ┌──────────────────────────────────────────────┐   │
│  │  watchers/                                    │   │
│  │  ├─ git_watcher.py       — monitors git log   │   │
│  │  ├─ file_watcher.py     — monitors key files  │   │
│  │  └─ mission_watcher.py  — monitors board      │   │
│  ├──────────────────────────────────────────────┤   │
│  │  event_store.py — SQLite CRUD + query         │   │
│  ├──────────────────────────────────────────────┤   │
│  │  delta_briefing.py — produces state briefing  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Files to Create

All under `OpsCenter/state_bridge/`:

### 1. `event_store.py` — SQLite Event Store

**Schema:**
```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,  -- 'checkpoint' | 'commit' | 'decision' | 'file_change' | 'mission_update'
  entity_type TEXT,          -- 'file' | 'mission' | 'decision' | 'preference'
  entity_key TEXT,           -- file path, mission ID, decision key
  summary TEXT,              -- human-readable summary
  detail_json TEXT,          -- full payload
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE sessions (
  id TEXT PRIMARY KEY,       -- session UUID
  started_at TEXT NOT NULL,
  ended_at TEXT,
  model TEXT,
  task_count INTEGER DEFAULT 0,
  open_issues TEXT           -- JSON array of unfinished business
);
```

**Methods:**
- `record_event(session_id, event_type, entity_type, entity_key, summary, detail)`
- `get_events_since(timestamp, limit=50)` — events after a given time
- `get_latest_session()` — most recent session record
- `get_session_chain(last_n=5)` — last N sessions with event summaries
- `get_decision_drift(entity_key)` — find decisions superseded by newer ones
- `prune_older_than(days=30)` — archive old events (except tagged `decision`)
- `close_session(session_id, issues)` — mark session ended

### 2. `watchers/git_watcher.py` — Git Monitor

- On startup: `git log --oneline -20` to capture recent commits
- Track commit hashes to detect new work between sessions
- For each new commit: `record_event('commit', 'commit', hash, subject)`
- On daemon tick: check for new commits since last check

### 3. `watchers/file_watcher.py` — File Monitor

Watch for changes to:
- `OpsCenter/collaboration/blackboard.md` — tail last 50 lines, detect new entries
- `OpsCenter/opencode_memory.md` — detect new decision entries
- `dossiers/*.md` — track which dossiers were modified
- `AGENTS.md` — detect changes to architecture/roles

Use `stat()` mtime polling (no inotify needed — simpler). Compare against stored mtime per file.

### 4. `watchers/mission_watcher.py` — Mission Board Monitor

- On startup: query `mission_board_sync.py list`, capture full state
- On each tick: re-query, diff against previous state
- Detect: new missions, status changes, assignment changes, priority changes
- Record each change as an event

### 5. `delta_briefing.py` — State Briefing Generator

Takes the delta between "last session's end state" and "current state" and produces a structured Markdown briefing:

```markdown
## 🏗 STATE BRIDGE BRIEFING — 2026-06-08

### Since last session (2026-06-07 14:30):
- **Commits:** 3 new (Furlow dossier, fare_watch fix, AGENTS.md v1.1)
- **Dirty files:** dossier/furlow.md (insurance fields incomplete)
- **Mission board:** #42 → IN_PROGRESS, #56 → COMPLETED, #78 → new
- **Decision drift detected:** Harlan's commission threshold changed from $500→$250
  but `learning_principles.json` still references $500

### Pending from last session:
- "Send Furlow pre-departure checklist" — no follow-up found
- "Fix fare_watch crash on null response" — appears unresolved

### Suggested next actions:
1. Apply decision drift fix (threshold)
2. Complete Furlow dossier insurance fields
3. Dispatch Furlow pre-departure checklist
```

### 6. `state_bridge_daemon.py` — Main Entry Point

**Command-line interface:**
```
python3 OpsCenter/state_bridge/state_bridge_daemon.py --daemon    # Start as background service
python3 OpsCenter/state_bridge/state_bridge_daemon.py --briefing  # One-shot: produce briefing now
python3 OpsCenter/state_bridge/state_bridge_daemon.py --status    # Show daemon health
python3 OpsCenter/state_bridge/state_bridge_daemon.py --prune     # Archive old events
python3 OpsCenter/state_bridge/state_bridge_daemon.py --inject    # Inject briefing into session start
```

**Daemon mode:**
- Tick interval: 60 seconds
- Each tick: run all watchers, record events
- Log file: `OpsCenter/state_bridge/state_bridge.log`
- PID file: `OpsCenter/state_bridge/state_bridge.pid`
- Graceful shutdown on SIGTERM

**MCP Registration:**
Register as an MCP tool so OpenCode can call it:
```python
Tool(
    name="state_bridge_briefing",
    description="Get session continuity briefing — delta since last session"
)
Tool(
    name="state_bridge_checkpoint",
    description="Record a session checkpoint event"
)
```

### 7. Integration File: `OpsCenter/state_bridge/session_startup_hook.py`

Script that OpenCode's `AGENTS.md` startup block calls:
```bash
python3 /home/john/Thunderbird/OpsCenter/state_bridge/session_startup_hook.py
```

This script:
1. Calls `state_bridge_daemon.py --briefing`
2. Opens a new session record
3. Returns the briefing text for injection

## Integration Points

| Existing System | Integration |
|---|---|
| `opencode_memory.md` | Read + watch for new decision entries |
| `blackboard.md` | Read + watch for new entries (tail) |
| `mission_board_sync.py` | Parse output for state changes |
| `wing_relay.py` | Read relay messages as events |
| `hale_state.json` | Load as state snapshot |
| Git | `git log --oneline -20` on startup |
| Dossiers | `stat()` mtime polling |

## Edge Cases

1. **First run (no history):** Briefing says "No prior session data — building baseline"
2. **Daemon crash recovery:** On restart, read last event timestamp, replay from there
3. **Concurrent sessions:** Use session IDs — detect if a session is still open
4. **Empty delta:** Briefing says "No changes since last session — continuing clean"
5. **Corrupt SQLite:** Keep WAL mode, auto-rebuild from current state on corruption
6. **Large event volume:** Prune threshold at 30 days for non-decision events

## Success Criteria

1. Session startup hook produces a non-empty, accurate briefing within 2 seconds
2. Briefing correctly identifies git commits since last session
3. Briefing flags decision drift when learning_principles.json contradicts temporal facts
4. Briefing lists pending work from last session's open issues
5. Daemon runs without crashing for 7+ days
6. MCP tools `state_bridge_briefing` and `state_bridge_checkpoint` are registered and callable

## Out of Scope

- Real-time collaborative session tracking (multiple OpenCode instances)
- Full-text search across all events
- Predictive "likely next actions" (future enhancement)

---

*Spec by Hale. Build by Opus. Route via ask-opus.*
