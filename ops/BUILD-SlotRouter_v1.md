# BUILD SPEC: Slot Router — Intelligent Task Dispatcher

**Mission:** MISSION-174
**Builder:** Sonnet (headless, via ask)
**Priority:** P1
**Hale Status:** Spec written 2026-06-08, build pending

---

## Problem

Hale manually routes every incoming task — "this needs A2 research", "this is a Sterling build", "use Opus for this one." That's a bottleneck. When Hale is busy or offline, tasks sit. There's also no consistency guarantee: similar tasks get routed differently depending on who's at bat.

## Solution

A classifier + dispatcher + routing table that takes any incoming task, determines the optimal agent+model combination, spawns it with the right context pack, monitors execution, and escalates on failure.

## Architecture

```
Task arrives (text description)
        │
        ▼
┌──────────────────────┐
│  classifier.py       │  — classify task into type
│  Type: research      │     + sub-type + complexity
│  Sub: cruise_intel   │
│  Complexity: medium   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  routing_table.py    │  — match task to optimal slot
│  Agent: A2 (Intel)   │
│  Model: Sonnet       │
│  Context: cruise     │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  dispatcher.py       │  — spawn the task
│  → ask 'research X'  │
│  → track PID         │
│  → monitor timeout   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  monitor.py          │  — watch execution
│  → success? close    │
│  → failure? escalate │
│  → timeout? retry    │
└──────────┬───────────┘
           ▼
     Report back
```

## Files to Create

All under `OpsCenter/slot_router/`:

### 1. `classifier.py` — Task Classifier

Classifies an incoming task description along three axes:

**Type** (required — one of):
| Type | Description | Example |
|---|---|---|
| `research` | Information gathering | "What's the weather in Bergen in July?" |
| `build` | Code/implementation | "Create the State Bridge daemon" |
| `draft` | Client-facing writing | "Write Furlow welcome email" |
| `validate` | Verification/audit | "Check FPD dates across all bookings" |
| `decide` | Needs Commander | "Should we book this suite?" |
| `monitor` | Watch/report | "Watch this fare for 30 days" |
| `maintain` | System upkeep | "Prune old logs" |

**Sub-type** (contextual — examples):
- `research.cruise_intel`, `research.flight`, `research.destination`
- `build.mcp_tool`, `build.skill`, `build.daemon`, `build.script`
- `draft.email`, `draft.proposal`, `draft.itinerary`
- `validate.financial`, `validate.dossier`, `validate.booking`
- `decide.strategy`, `decide.client`, `decide.finance`

**Complexity** (heuristic — keyword/pattern based):
- `simple` — one-step, deterministic output (< 5 min)
- `medium` — multi-step, needs moderate reasoning (5-20 min)
- `complex` — multi-step, needs deep reasoning, edge cases (20+ min)
- `critical` — financial/legal impact, needs highest assurance

**Scoring heuristic:**
- Mentions of $ amounts, booking IDs, legal terms → bump complexity
- Mentions of specific file paths → maybe `build` type
- Mentions of client names → maybe `draft` or `research`
- Mentions of "urgent", "P0", "deadline" → flag as critical

### 2. `routing_table.py` — Routing Table + Escalation Protocol

**Default routing table:**
```python
ROUTING_TABLE = {
    ('research', 'simple'):     {'agent': 'A2',    'model': 'sonnet',  'dispatch': 'ask'},
    ('research', 'medium'):     {'agent': 'A2',    'model': 'sonnet',  'dispatch': 'ask'},
    ('research', 'complex'):    {'agent': 'A2',    'model': 'opus',    'dispatch': 'ask-opus'},
    ('research', 'critical'):   {'agent': 'A2+A5', 'model': 'opus',    'dispatch': 'ask-opus'},
    ('build',    'simple'):     {'agent': 'Sterling', 'model': 'sonnet','dispatch': 'ask'},
    ('build',    'medium'):     {'agent': 'Sterling', 'model': 'sonnet','dispatch': 'ask'},
    ('build',    'complex'):    {'agent': 'Sterling', 'model': 'opus',  'dispatch': 'ask-opus'},
    ('build',    'critical'):   {'agent': 'Sterling+A5', 'model': 'opus','dispatch': 'ask-opus'},
    ('draft',    'simple'):     {'agent': 'Dani',  'model': 'sonnet',  'dispatch': 'ask'},
    ('draft',    'medium'):     {'agent': 'Dani',  'model': 'sonnet',  'dispatch': 'ask'},
    ('draft',    'complex'):    {'agent': 'Dani',  'model': 'sonnet',  'dispatch': 'ask'},
    ('validate', 'simple'):     {'agent': 'Harlan','model': 'sonnet',  'dispatch': 'ask'},
    ('validate', 'medium'):     {'agent': 'Harlan','model': 'sonnet',  'dispatch': 'ask'},
    ('validate', 'complex'):    {'agent': 'Harlan','model': 'opus',    'dispatch': 'ask-opus'},
    ('validate', 'critical'):   {'agent': 'Harlan','model': 'opus',    'dispatch': 'ask-opus'},
    ('decide',   '*'):          {'agent': 'Commander', 'model': 'n/a','dispatch': 'telegram'},
    ('monitor',  '*'):          {'agent': 'A3',    'model': 'sonnet',  'dispatch': 'script'},
    ('maintain', 'simple'):     {'agent': 'Sterling', 'model': 'sonnet','dispatch': 'ask'},
    ('maintain', 'medium'):     {'agent': 'Sterling', 'model': 'sonnet','dispatch': 'ask'},
}
```

**Overrides (read from `overrides.json`):**
```json
{
  "furlow": {"draft": {"model": "opus"}},
  "financial": {"validate": {"model": "opus"}},
  "2026-06-08": {"all": {"agent": "Hale", "reason": "Sterling is on P0 Chromebook task"}}
}
```

**Escalation protocol:**
```python
ESCALATION = {
    1: {"on": "failure", "action": "retry_same", "max_attempts": 2},
    2: {"on": "double_failure", "action": "upgrade_model", "from": "sonnet", "to": "opus"},
    3: {"on": "opus_failure", "action": "notify_hale", "channel": "telegram"},
    4: {"on": "timeout", "action": "notify_commander", "channel": "telegram"},
}
```

### 3. `dispatcher.py` — Task Dispatcher

Based on the routing decision, spawns the task:

```python
def dispatch(route, task_desc, context=None):
    if route.dispatch == 'ask':
        # Use ask wrapper (Sonnet)
        outfile = f"/home/john/Thunderbird/output/slot_{uuid}.md"
        cmd = f"ask '{task_desc} WRITE to {outfile}'"
    elif route.dispatch == 'ask-opus':
        # Use ask-opus wrapper (Opus)
        outfile = f"/home/john/Thunderbird/output/slot_{uuid}.md"
        cmd = f"ask-opus '{task_desc} WRITE to {outfile}'"
    elif route.dispatch == 'telegram':
        # Send to Commander via Telegram
        cmd = f"telegram_send_to_commander '{task_desc}'"
    elif route.dispatch == 'script':
        # Run a local script
        cmd = task_desc  # direct execution

    pid = subprocess.Popen(cmd, shell=True).pid
    return TaskRecord(uuid, route, pid, outfile, started_at=now())
```

**`TaskRecord` schema (in-memory + JSON persistence):**
```python
{
    "id": "slot_abc123",
    "task": "Research Bergen weather July 2027",
    "classified_type": "research.cruise_intel",
    "complexity": "simple",
    "routed_to": {"agent": "A2", "model": "sonnet", "dispatch": "ask"},
    "pid": 12345,
    "output_file": "/home/john/Thunderbird/output/slot_abc123.md",
    "started_at": "2026-06-08T14:30:00",
    "status": "running",  # running | success | failed | escalated
    "attempts": 1,
    "error": null
}
```

### 4. `monitor.py` — Execution Monitor

Watches running tasks and handles outcomes:

- Polls PID liveness + output file existence every 10 seconds
- On output file complete: read, validate non-empty, mark success
- On PID dead + no output: mark failure, trigger escalation
- On timeout (default: 600s for simple, 1800s for complex): escalate
- Logs all outcomes to `slot_router.log`
- Learning feedback: record routing accuracy (did the right agent get picked?)

### 5. `slot_router.py` — Main Entry Point + MCP Tools

**CLI:**
```
python3 OpsCenter/slot_router/slot_router.py route "Research Bergen weather July 2027"
python3 OpsCenter/slot_router/slot_router.py status [task_id]
python3 OpsCenter/slot_router/slot_router.py list [--status running|success|failed]
python3 OpsCenter/slot_router/slot_router.py cancel <task_id>
python3 OpsCenter/slot_router/slot_router.py override --type research --model opus
```

**MCP Tools to Register:**
```python
Tool(
    name="slot_router_route",
    description="Route a task to the optimal agent+model. Returns task_id and dispatch plan."
)
Tool(
    name="slot_router_status",
    description="Check status of a routed task by task_id."
)
Tool(
    name="slot_router_list",
    description="List recent routed tasks with status filter."
)
```

### 6. `overrides.json` — Runtime Override Configuration

Stored at `OpsCenter/slot_router/overrides.json`:

```json
{
  "overrides": [
    {"if_type": "draft", "if_client": "furlow", "model": "opus", "reason": "Furlow emails need extra care"},
    {"if_type": "validate", "if_subtype": "financial", "model": "opus", "reason": "Harlan requires Opus for financials"}
  ],
  "temporal_overrides": [
    {"valid_from": "2026-06-08", "valid_to": "2026-06-10", "all": {"agent": "Hale"}, "reason": "Sterling on P0"}
  ]
}
```

## Integration Points

| Existing System | Integration |
|---|---|
| `ask` wrapper | Primary dispatch mechanism for Sonnet tasks |
| `ask-opus` wrapper | Primary dispatch mechanism for Opus tasks |
| Mission board | Log routed tasks as mission board items |
| `wing_relay.py` | Report routing decisions to relay |
| AGENTS.md | Session startup could call `slot_router.py list --status running` to show in-flight tasks |
| Telegram | Escalate failures, deliver Commander-bound tasks |

## Edge Cases

1. **Unknown task type:** Default to `research.simple` → A2/Sonnet
2. **Dispatcher failure (ask not available):** Retry once, then notify Hale
3. **Multiple tasks in queue:** FIFO with P0 priority queue support
4. **Task cancellation:** Kill PID, mark cancelled, clean up output file
5. **Routing to self:** Never route a slot_router maintenance task through the router (use direct execution)
6. **Override conflicts:** Default model override wins over client override (clients can opt-up, not opt-down)

## Success Criteria

1. `slot_router route "..."` classifies and dispatches a task within 3 seconds
2. Tasks are routed to the correct agent+model per the routing table
3. Failed tasks auto-escalate (sonnet→opus→Hale) within 60 seconds
4. `overrides.json` changes take effect without daemon restart
5. MCP tools `slot_router_route`, `slot_router_status`, `slot_router_list` are registered
6. Routing accuracy improves over time (tracked in learning feedback)

## Out of Scope

- GUI dashboard (future)
- Complex workflow DAG (task A → task B → task C)
- Resource-aware scheduling (CPU/memory based)
- Cross-session task persistence in SQLite (that's State Bridge's job)

---

*Spec by Hale. Build by Sonnet. Route via ask.*
