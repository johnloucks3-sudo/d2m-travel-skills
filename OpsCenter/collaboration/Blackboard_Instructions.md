# THUNDERBIRD BLACKBOARD — INSTRUCTION MANUAL
# Dreams2Memories Travel, LLC
# Version: 1.0 | Date: 2026-03-30
# Author: Claude Sonnet 4.6

---

## WHAT IS THE BLACKBOARD?

The blackboard is Thunderbird's shared operational state system.
It tells every AI (Claude, OpenCode, Hale, Deepseek, Groq) what's happening,
what's pending, and what the current budget is — automatically, on every
session, on every device, with zero Commander action.

Think of it as the mission board that never goes dark.

---

## HOW IT WORKS

`blackboard_sync.py` runs every 5 minutes via systemd timer.
It reads the master blackboard files and injects current state into:

| Entry Point | How state arrives | Commander action |
|-------------|------------------|-----------------|
| Claude Code / YOGA | CLAUDE.md auto-loads | None |
| Goose (desktop) | TOM extension injects every message | None |
| Goose (Telegram gateway) | Same TOM injection | None |
| Termius / SSH | .bashrc prints summary on login | None |
| Hale / Telegram C2 | System prompt includes state | None |
| Claude Desktop / Chromebook | Ask Hale: "blackboard state" | One Telegram message |

---

## THE MASTER FILES

All files live in: `~/Thunderbird/OpsCenter/collaboration/`

| File | Purpose | Who writes it |
|------|---------|--------------|
| `blackboard.md` | Master shared state | Commander or any agent |
| `rate_limit_status.md` | Current model budgets | Hale (auto) + Commander |
| `routing_log.md` | Every task routed | All agents (append-only) |
| `conflict_log.md` | All disputes | Any agent (append-only) |
| `deepseek_inbox.md` | Arbitration requests | Any agent |
| `deepseek_ruling.md` | Arbitration decisions | Deepseek |
| `claude_inbox.md` | Tasks for Claude | Commander or Goose |
| `opencode_inbox.md` | Tasks for Goose | Commander or Claude |
| `blackboard_summary.txt` | 10-line digest | blackboard_sync.py ONLY |

**Never edit `blackboard_summary.txt` manually** — it is overwritten every 5 minutes.

---

## UPDATING THE BLACKBOARD

### Update budget status (do this when you notice a model limit)
Edit `rate_limit_status.md`:
```
Claude Sonnet: RED — depleted, resets Tuesday 9PM
```
The sync picks it up within 5 minutes. Hale will report it on next Telegram message.

### Update active tasks
Edit `blackboard.md` — find the "Active tasks" line and update the count and description.
The sync picks it up within 5 minutes.

### Update standing directives
Edit `blackboard.md` — find the "Standing directives" section.
These persist across all sessions until you change them.

### Quick update from Telegram
Send Hale: "update blackboard — active tasks: 2, Claude status: RED"
Hale will write the update to blackboard.md directly.

---

## QUEUING TASKS

### Queue a task for Claude
Add a JSON block to `claude_inbox.md`:
```json
{
  "task_id": "20260401-0900-C",
  "submitted_by": "COMMANDER",
  "submitted_at": "2026-04-01T09:00:00MT",
  "task_type": "synthesize",
  "priority": "NORMAL",
  "token_estimate": 2000,
  "pii": false,
  "instructions": "Read opencode_output.md and synthesize into client proposal.",
  "output_destination": "/home/john/Thunderbird/OpsCenter/collaboration/claude_output.md",
  "deadline": "2026-04-01T11:00:00MT"
}
```
Then trigger Claude: **"Read your inbox and execute"**

### Queue a task for Goose
Same format, write to `opencode_inbox.md`.
Then trigger Goose: **"Read your inbox and execute"**

### PII rule
If task involves client names, booking details, or financial data:
Set `"pii": true` — this hard-blocks Deepseek and Groq from receiving the task.

---

## ARBITRATION (DEEPSEEK)

When Claude and Goose produce conflicting outputs:

1. Log the conflict in `conflict_log.md`:
```
[2026-04-01T10:00MT] | CONFLICT | task_id | Claude says X | Goose says Y
```

2. Write arbitration request to `deepseek_inbox.md`:
```
ARBITRATION REQUEST
task_id: [original task_id]
requested_by: COMMANDER
submitted_at: [timestamp]
pii: FALSE
agent_a_summary: [Claude's position — 3 sentences]
agent_b_summary: [Goose's position — 3 sentences]
question: [one clear question for Deepseek]
```

3. Trigger Deepseek: **"Read deepseek_inbox and issue ruling"**

4. Deepseek writes ruling to `deepseek_ruling.md`.
   All rulings are advisory until Commander confirms.

**Deepseek never receives PII. Hard fence. No exceptions.**

---

## MODEL ROUTING QUICK REFERENCE

| Task | Route to | Reason |
|------|---------|--------|
| Classify, summarize < 500 tokens | Groq | Fastest, cheapest |
| Web research, real-time data | Goose | Multi-modal, broad tools |
| Structured data, code analysis | Deepseek | Precision extraction |
| Long-context, client writing | Claude | 200K context, D2M voice |
| Any conflict | Deepseek | Arbitrator authority |
| PII tasks | Claude or Goose ONLY | Hard fence |

### Claude budget guard (0600-1800 MT)
During Commander's operational hours, Claude routes to Goose-first automatically.
Override: type **/use claude** to force Claude regardless of budget.

---

## CHECKING SYSTEM STATUS

### From Termius/SSH
Login — blackboard summary prints automatically before prompt.

### From Telegram
Send Hale: **"blackboard state"** — she responds with current summary.
Send Hale: **"system status"** — she runs full health check.

### From YOGA directly
```bash
cat ~/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt
systemctl --user status thunderbird-blackboard-sync.timer
```

### From Claude Code
CLAUDE.md auto-loads with current state — just start a session.

---

## JAPAN / TRAVEL OPERATIONS

While away April 10 — May 11, 2026:

**Check YOGA is alive:** Hale sends daily heartbeat at 0800 MT.
If no heartbeat → something is wrong.

**Check blackboard from anywhere:**
  - Termius SSH → auto-prints on login
  - Telegram → ask Hale "blackboard state"
  - Goose → state is in every message automatically

**If a service crashes:** Watchdog auto-restarts and alerts via Telegram.
**If Claude is rate-limited:** Goose handles everything automatically.
**If you need Claude urgently:** /use claude override, or wait for reset.

---

## TROUBLESHOOTING

### Blackboard summary looks stale
```bash
systemctl --user status thunderbird-blackboard-sync.timer
systemctl --user start thunderbird-blackboard-sync.service
```

### Goose isn't seeing blackboard state
Check TOM extension in `~/.config/goose/config.yaml`:
```yaml
tom:
  envs:
    GOOSE_MOIM_MESSAGE_FILE: /home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt
```
Restart Goose after any config.yaml changes.

### SSH login not showing blackboard
Check `.bashrc` contains:
```bash
cat /home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt 2>/dev/null && echo ""
```

### Hale not reporting blackboard state
Check task_processor.py contains `_get_blackboard_context()` function.
Restart thunderbird-overwatch: `systemctl --user restart thunderbird-overwatch`

### Sync failing silently
```bash
journalctl --user -u thunderbird-blackboard-sync.service -n 20
```

---

## FILES CREATED BY THIS SYSTEM

```
~/Thunderbird/OpsCenter/
  blackboard_sync.py                    ← sync engine (runs every 5 min)

~/.config/systemd/user/
  thunderbird-blackboard-sync.service   ← systemd service
  thunderbird-blackboard-sync.timer     ← systemd timer

~/Thunderbird/OpsCenter/collaboration/
  blackboard.md                         ← master state (edit this)
  blackboard_summary.txt                ← auto-generated (never edit)
  rate_limit_status.md                  ← budget tracking
  routing_log.md                        ← audit trail
  conflict_log.md                       ← dispute log
  deepseek_inbox.md                     ← arbitration requests
  deepseek_ruling.md                    ← arbitration decisions
  claude_inbox.md                       ← Claude task queue
  opencode_inbox.md                        ← Goose task queue
  Blackboard_Instructions.md            ← this file
```

---

## QUICK COMMAND REFERENCE

| Action | Command |
|--------|---------|
| Run sync manually | `cd ~/Thunderbird && source .venv/bin/activate && python3 OpsCenter/blackboard_sync.py` |
| Check timer status | `systemctl --user status thunderbird-blackboard-sync.timer` |
| View current summary | `cat ~/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt` |
| Restart sync timer | `systemctl --user restart thunderbird-blackboard-sync.timer` |
| View sync logs | `journalctl --user -u thunderbird-blackboard-sync.service -n 20` |
| Trigger Claude | Say: **"Read your inbox and execute"** |
| Trigger Goose | Say: **"Read your inbox and execute"** |
| Trigger Deepseek | Say: **"Read deepseek_inbox and issue ruling"** |
| Override budget guard | Type: **/use claude** |
| Get state from anywhere | Telegram to Hale: **"blackboard state"** |

---
*Thunderbird Blackboard v1.0 — Dreams2Memories Travel, LLC*
*Built: 2026-03-30 | Research to production: < 12 hours*
