# OpenCode Headless Claude — Quick Start
**For OpenCode developers | v1.0 | 2026-04-24**

---

## TL;DR — Just Copy This

```python
from OpsCenter.headless_claude_fallback import dispatch_with_fallback

result = dispatch_with_fallback(
    task_description="Analyze Q2 cruise trends",
    output_file_path="/home/john/Thunderbird/output/q2_trends.txt",
    task_name="q2_cruise_analysis"
)

# That's it. Auto-escalates to Claude Code if needed.

if result["status"] in ["SPAWNED", "ESCALATED_TO_CLAUDE_CODE"]:
    print(f"Task running (escalated: {result['escalated']})")
else:
    print(f"Failed: {result['error']}")
```

---

## What Just Happened?

1. **Tried:** Spawn headless Claude via OpenCode's native method
2. **Failed?** Retried once
3. **Still failed?** Escalated to Claude Code (the primary CLI)
4. **Failed again?** Returned error with full diagnostic trail

**Result:** Task is running, OR you have full error info for COS.

---

## Three-Level Architecture

| Level | What | Use Case | Fallback |
|-------|------|----------|----------|
| **Tier 1** | Native OpenCode dispatch (`spawn_headless_claude`) | Fast path, simple task spawn | Retry once |
| **Tier 2** | Escalation to Claude Code CLI | Token issues, daemon problems | Error logging |
| **Tier 3** | Failure logging + COS alert | Both tiers failed completely | Manual recovery |

---

## Important Notes

### ✅ DO

- ✅ Use `dispatch_with_fallback()` for all headless spawns
- ✅ Provide descriptive `task_name` for logging
- ✅ Check `result["status"]` before proceeding
- ✅ Log the result for audit trail
- ✅ Let OpenCode exit after spawning (don't wait for task)

### ❌ DON'T

- ❌ Call `subprocess.Popen()` directly
- ❌ Call `spawn_headless_claude()` directly (use fallback wrapper)
- ❌ Try to read output from subprocess — Claude writes to file
- ❌ Wait for process with `.wait()` — task runs in background
- ❌ Assume success without checking `result["status"]`

---

## Return Value

```python
result = {
    "status": "SPAWNED" | "ESCALATED_TO_CLAUDE_CODE" | "FAILED",
    "escalated": True/False,                    # Was Tier 2 used?
    "retries_attempted": 0-1,                   # How many retries?
    "pid": 12345,                               # Process ID (if running)
    "log_file": "/path/to/log",                 # Where to find logs
    "output_file": "/path/to/output.txt",       # Where task writes result
    "error": "human readable error" (if FAILED)
}
```

---

## Status Values

| Status | Meaning | What To Do |
|--------|---------|-----------|
| `SPAWNED` | Task is running (Tier 1 succeeded) | Log result, move on |
| `ESCALATED_TO_CLAUDE_CODE` | Task is running (Tier 2, escalated) | Log result, move on |
| `FAILED` | Both tiers failed | Log error, alert COS with log_file path |

---

## Common Questions

### Q: What if the task takes >10 minutes?
**A:** Perfect use case for headless spawn. Task runs in background while OpenCode exits. Check output file later.

### Q: How do I know when the task is done?
**A:** Poll the output file:
```python
output_path = result["output_file"]
if Path(output_path).exists():
    print("Task complete, reading output...")
    output = Path(output_path).read_text()
```

Or check supervisor logs:
```bash
tail -f /home/john/Thunderbird/logs/haiku_supervisor.log | grep task_name
```

### Q: What if OpenCode crashes mid-spawn?
**A:** Claude Code is now running independently. OpenCode's death doesn't affect it.

### Q: Can I customize max_retries?
**A:** Yes:
```python
result = dispatch_with_fallback(
    task_description="...",
    output_file_path="...",
    task_name="...",
    max_retries=3  # Try 3 times before escalating
)
```

---

## Debugging Failed Tasks

**Step 1:** Check the returned log file
```bash
tail -50 /home/john/Thunderbird/logs/claude_*_escalation_*.log
```

**Step 2:** Look for Tier 1 error
```
[FAILED] spawn_headless_claude: token_refresh_daemon inactive
```

**Step 3:** Look for Tier 2 outcome
```
[INFO] escalate_to_claude_code: Spawned Claude Code (PID 12346)
```

**Step 4:** If FAILED, report to COS with the log file path

---

## Full Example

```python
#!/usr/bin/env python3
from OpsCenter.headless_claude_fallback import dispatch_with_fallback
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define task
task_description = """
Analyze cruise line competitors for Q2 2026.
Report on: pricing trends, new itineraries, marketing strategies.
"""

output_file = Path("/home/john/Thunderbird/output/q2_competitive_analysis.txt")

# Dispatch with automatic escalation
result = dispatch_with_fallback(
    task_description=task_description,
    output_file_path=str(output_file),
    task_name="q2_competitive_analysis"
)

# Log result
logger.info(f"Headless Claude dispatch: {json.dumps(result, indent=2)}")

# Check status
if result["status"] in ["SPAWNED", "ESCALATED_TO_CLAUDE_CODE"]:
    logger.info(f"✅ Task running (PID {result['pid']})")
    logger.info(f"   Output: {result['output_file']}")
    logger.info(f"   Logs: {result['log_file']}")
else:
    logger.error(f"❌ Task dispatch failed: {result['error']}")
    logger.error(f"   Check logs: {result['log_file']}")
```

---

## Architecture References

**Want to understand the internals?** Read these in order:

1. **This file** — Quick start
2. `@docs/AGENTS_HEADLESS_DISPATCH_ARCHITECTURE.md` — Architecture overview
3. `@docs/OPENCODE_ESCALATION_MECHANISM.md` — Deep technical dive (Sonnet-level analysis)
4. `@docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` — The definitive spawn reference

---

## Key Principle

> **Escalation is automatic. You just dispatch. The system handles resilience.**

Call `dispatch_with_fallback()`. The rest happens automatically: verification, retry, escalation, logging, and error reporting.

---

*Updated 2026-04-24 | Hale, COS*
