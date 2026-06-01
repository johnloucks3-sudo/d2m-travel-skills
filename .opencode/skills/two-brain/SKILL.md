---
name: two-brain
description: "Run auto sessions with two models — OpenCode (tools/ops) + Claude Sonnet (reasoning/voice). Includes METRONOME clock daemon that never sleeps, auto-progresses stalled tasks, escalates on idle. Triggers on: two-brain, partner mode, pair program, dual model, split brain, auto session, sonnet partner, multi-model, two windows, two models, parallel session, metronome, clock agent, non-sleeper, cadence, pacemaker, heartbeat, session timer, auto-progress, stalled task, dual engine, wind condor."
---

# Two-Brain Session Protocol + METRONOME

You run TWO agents in parallel:

1. **OpenCode** (current session) — tools, file ops, MCP, code execution, ops
2. **Claude Sonnet** (headless via `dispatch_claude.py`) — reasoning, judgment, client voice, strategy

A **METRONOME** daemon ticks every 5 minutes, tracks cadence, and auto-escalates stalled work.

## When to Activate

Activate this skill when the user invokes any keyword above, or when:
- The task requires both tool execution AND reasoning/judgment
- A task is complex enough that a second model's opinion adds value
- The user wants "auto-pilot" mode with cadence tracking
- Work has been stalled and needs escalation

## Workflow

### Phase 1: Classify the Task

```
Is it a code/tools/ops task?
  → OpenCode handles directly

Is it a reasoning/voice/strategy/judgment call?
  → Dispatch to Claude Sonnet via dispatch_claude.py

Is it both?
  → OpenCode handles tools, dispatches Sonnet for judgment.
    METRONOME tracks both threads.
```

### Phase 2: Dispatch Sonnet (when needed)

```bash
ask 'YOUR TASK — include all context needed'
```

Or background (fire-and-forget, METRONOME monitors):
```bash
python3 /home/john/Thunderbird/OpsCenter/dispatch_claude.py \
  --task "two-brain-$(date +%s)" \
  --output "/home/john/Thunderbird/output/two_brain_$(date +%s).md" \
  --prompt "YOUR TASK — WRITE to /home/john/Thunderbird/output/two_brain_$(date +%s).md" \
  --model sonnet
```

Then watch:
```bash
python3 /home/john/Thunderbird/OpsCenter/watch_task.py \
  "/home/john/Thunderbird/output/two_brain_$(date +%s).md" \
  $(cat /tmp/last_pid) \
  --timeout 600
```

### Phase 3: Integrate Results

- Sonnet output lands in `output/two_brain_*.md`
- Read it, integrate into current context
- If METRONOME is running, it auto-detects completion from the output file

### Phase 4: Close the Loop

- Write checkpoint via `session_checkpoint.py`
- Write tick to metronome_ticks.jsonl via the daemon
- Mark task COMPLETE in inbox or outbox

## METRONOME — The Clock

A systemd timer runs `OpsCenter/metronome.py` every 5 minutes.

### What It Checks

| Check | Threshold | Action |
|-------|-----------|--------|
| Last checkpoint age | > 5 min idle | YELLOW — write nudge |
| Last dispatch stale | > 10 min idle | ORANGE — auto-restart Sonnet dispatch |
| Both brains idle | > 15 min | RED — Telegram alert Commander |
| Deep idle | > 30 min | CRITICAL — auto-close stale task, surface blocking issue |

### METRONOME Ticks

Every tick writes to `OpsCenter/metronome_ticks.jsonl`:
```json
{"ts": "2026-05-22T21:00:00Z", "tick": 1234, "cadence_s": 300, "state": "GREEN", "last_checkpoint_age_s": 120, "last_dispatch_age_s": null}
```

### METRONOME Systemd

```bash
# Install
sudo cp deploy/systemd/metronome.service /etc/systemd/system/
sudo cp deploy/systemd/metronome.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now metronome.timer

# Status
systemctl status metronome.timer
journalctl -u metronome.service --since "10 min ago"

# View ticks
tail -5 /home/john/Thunderbird/OpsCenter/metronome_ticks.jsonl | python3 -m json.tool
```

## Two-Brain Agent Config

Registered in opencode.json as `two-brain` agent using Claude Sonnet via dispatch infrastructure. The `sonnet-partner` agent is a subagent that wraps `dispatch_claude.py --model sonnet` for inline use.

## Compatible Commands

| Command | Effect |
|---------|--------|
| `/two-brain classify <task>` | Classifies a task for OpenCode vs Sonnet |
| `/two-brain dispatch <task>` | Dispatches task to Sonnet with watch |
| `/two-brain status` | Shows METRONOME state + latest tick |
| `/two-brain tick` | Force a METRONOME tick now |
| `/two-brain full <task>` | Full two-brain: classify → dispatch → integrate |

## Important Rules

1. **Sonnet is the thinking partner, not the executor.** It writes output files, not code changes. OpenCode integrates.
2. **METRONOME never sleeps.** If you stop hearing ticks, check the systemd timer.
3. **Always close the loop.** Mark tasks COMPLETE when Sonnet results are integrated.
4. **If Sonnet dispatch fails, fall back to OpenCode.** Never block on a dead partner.
5. **Log every dispatch** — write source, model, task, and result path to checkpoints.
