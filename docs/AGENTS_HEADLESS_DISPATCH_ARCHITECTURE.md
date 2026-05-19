# Agent Headless Claude Dispatch Architecture
**Version 1.0 | 2026-04-24 | Definitive Guidance for All Agents**

---

## ⚠️ CRITICAL — READ THIS FIRST

This document is the **README for how agents (OpenCode, OpenCode, Claude Code) spawn headless Claude**.

**Definitive Reference:** `@docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md`  
**Do NOT deviate.** Violations → supervisor detection → COS escalation.

---

## What is Headless Claude?

Headless Claude = `claude -p "PROMPT"` running as a **background subprocess** without Claude Desktop, output written to disk.

**When to use it:**
- Long-running tasks (>10 min)
- Background processing (research, analysis, file generation)
- Batch operations
- When spawning Claude and then exiting the parent process

**When NOT to use it:**
- Real-time interaction needed
- Prompt requires user input
- Output must be captured in-process

---

## Three-Layer Architecture

### Layer 1: Foolproof Spawn Wrapper
**File:** `core/ai_infra/thunderbird_headless_spawn.py`

This is the **ONLY safe implementation**. It enforces:
- Token refresh daemon verification (prevents "token expired" failures)
- OAuth credentials file check (prevents auth failures)
- Haiku supervisor daemon check (enables failure detection)
- OAuth token injection from credentials file
- `start_new_session=True` process detachment (prevents orphaning)
- Log file redirection (enables debugging)
- Explicit model selection (prevents expensive model surprises)

**Never call subprocess.Popen directly.**

```python
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

result = spawn_headless_claude(
    prompt="Your prompt with WRITE [PATH] instruction...",
    output_file="/home/john/Thunderbird/output/result.txt",
    model="claude-haiku-4-5-20251001",
    task_name="my_task"
)

if result["status"] == "SPAWNED":
    print(f"Task running as PID {result['pid']}")
else:
    print(f"Spawn failed: {result.get('error')}")
```

---

### Layer 2: Agent Dispatch Wrapper
**OpenCode:** `OpsCenter/opencode_headless_claude_dispatch.py`

OpenCode MUST use this wrapper for all headless Claude tasks. It:
- Enforces mandatory prompt format with `WRITE [PATH]` instruction
- Routes to Layer 1 (foolproof wrapper)
- Handles OpenCode-specific error reporting

```python
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

result = dispatch_to_headless_claude(
    task_description="Analyze cruise line competitors",
    output_file_path="/home/john/Thunderbird/output/cruise_analysis.txt",
    task_name="cruise_competitive_analysis"
)
```

**DO NOT call subprocess.Popen directly in OpenCode code.**

---

### Layer 2B: Fallback to Claude Code
**File:** `OpsCenter/headless_claude_fallback.py`

If OpenCode's dispatch fails, automatic fallback to Claude Code ensures mission continuity.

**High-level API (recommended):**
```python
from OpsCenter.headless_claude_fallback import dispatch_with_fallback

result = dispatch_with_fallback(
    task_description="Analyze cruise line competitors",
    output_file_path="/home/john/Thunderbird/output/cruise_analysis.txt",
    task_name="cruise_competitive_analysis",
    max_retries=1  # Try OpenCode once, then escalate to Claude Code
)

if result["escalated"]:
    print(f"Task escalated to Claude Code (OpenCode failed {result['retries_attempted']} times)")
```

**What happens if OpenCode fails:**
1. Layer 1 verification fails (token daemon, supervisor, or credentials)
2. Layer 2 catches the failure
3. Automatically escalates to `dispatch_with_fallback()` which:
   - Retries OpenCode dispatch up to `max_retries` times
   - If still failing, escalates to Claude Code directly
   - Claude Code handles full OAuth, environment, and error handling
   - Returns result with `escalated=True` flag

**Result structure includes escalation info:**
```python
{
    "status": "SPAWNED" | "ESCALATED_TO_CLAUDE_CODE" | "FAILED",
    "pid": int,
    "log_file": str,
    "output_file": str,
    "escalated": bool,
    "retries_attempted": int,
    "error": str (if failed)
}
```

---

### Layer 3: Standing Order
**File:** `CLAUDE.md` (section: HARD RULE — HEADLESS CLAUDE DISPATCH)

All agents are bound by Standing Order 24 APR 2026:
- Mandatory use of Layer 1 or Layer 2 wrappers
- No direct subprocess.Popen calls
- Violations → supervisor detection → COS escalation

---

## Mandatory Patterns (Cannot Be Omitted)

### Pattern 1: Token Refresh Timers RUNNING
```bash
systemctl --user status claude-token-monitor.timer claude-oauth-keepalive.timer --no-pager
# Expected: Active: active (waiting) for both
```
**Why:** Token expires within hours. Keepalive fires every ~30 min. Without it, Claude fails ~4 hours in.

> **Correction (2026-05-18 — A12 ELON / SO-VCS-INFRA-20260518):** `claude-token-refresh.timer` does **not** exist on this system. Use the two user-level timers shown above.

### Pattern 2: OAuth Credentials File EXISTS
```bash
ls -la ~/.claude/.credentials.json
# Expected: file exists, contains claudeAiOauth.accessToken
```
**Why:** Headless Claude reads this file for auth. No file = instant 401 Unauthorized.

### Pattern 3: Watchdog RUNNING
```bash
systemctl --user status thunderbird-watchdog.timer --no-pager
# Expected: Active: active (waiting)
```
**Why:** Watchdog detects spawn failures and alerts COS. Without it, failures go unnoticed.

> **Correction (2026-05-18 — A12 ELON / SO-VCS-INFRA-20260518):** `claude-haiku-supervisor.timer` does **not** exist on this system. Failure monitoring is `thunderbird-watchdog.timer`.

### Pattern 4: Explicit WRITE [PATH] in Prompt
```python
prompt = f"""
TASK: Your task description

WRITE your complete output to {output_file}
Do NOT output to stdout.
"""
```
**Why:** Headless Claude writes to the specified file. Without explicit WRITE, output is lost and task fails silently.

### Pattern 5: start_new_session=True in Popen()
```python
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    stdout=log_file,
    stderr=subprocess.STDOUT,
    env=env,
    start_new_session=True  # ← MANDATORY
)
```
**Why:** Without this, Claude becomes a child process. When parent exits, Claude dies. Task is lost.

### Pattern 6: Explicit Model Selection
```python
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt, "--model", "claude-haiku-4-5-20251001"],
    ...
)
```
**Why:** Without this, defaults to expensive Opus. Wastes Commander's credits.

---

## Common Failure Patterns (DO NOT DO THESE)

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| No `start_new_session=True` | Process dies when parent exits | Add to Popen() |
| No explicit WRITE to file | Output is lost | Include `WRITE [PATH]` in prompt |
| No log redirection | Can't debug failures | Redirect stdout/stderr to log file |
| Empty environment dict | No token in env for Claude | Start with `dict(os.environ)` |
| No token refresh timers | Token expires after ~4 hours | `systemctl --user enable --now claude-token-monitor.timer claude-oauth-keepalive.timer` |
| Direct subprocess.Popen call | Bypasses safety checks | Use Layer 1 or Layer 2 wrapper |

---

## Correct Example — Copy This Pattern

```python
#!/usr/bin/env python3
"""
Headless Claude spawn — CORRECT PATTERN
"""
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude
import json

# Dispatch to headless Claude
result = dispatch_to_headless_claude(
    task_description="Summarize Q2 cruise demand trends by destination",
    output_file_path="/home/john/Thunderbird/output/q2_cruise_trends.txt",
    task_name="q2_cruise_analysis"
)

# Check result
if result["status"] == "SPAWNED":
    print(f"✅ Task spawned (PID {result['pid']})")
    print(f"Output: {result['output_file']}")
    print(f"Logs: {result['log_file']}")
else:
    print(f"❌ Spawn failed: {result.get('error')}")
    exit(1)
```

---

## If Spawning Fails — Diagnosis

**Step 1: Check the log file**
```bash
tail -50 /home/john/Thunderbird/logs/claude_*.log
```

**Step 2: Verify prerequisites**
```bash
systemctl --user status claude-token-monitor.timer claude-oauth-keepalive.timer --no-pager
systemctl --user status thunderbird-watchdog.timer --no-pager
ls -la ~/.claude/.credentials.json
```

**Step 3: Match error to root cause**

| Error | Root Cause | Fix |
|---|---|---|
| `401 Unauthorized` | OAuth token missing or expired | Check credentials file; wait for token refresh daemon |
| `[Errno 2] No such file or directory` | Claude binary not found | Check `/home/john/.local/bin/claude` exists |
| `timeout` | Process took >10 min | Expected for large tasks; check log file |
| `Process exited with code 1` | Generic error | Read full log output; escalate to COS |

**Step 4: Report to COS if unresolved**
```
Message: "Headless Claude spawn failed for task [NAME]
Check log: [PATH]
Prerequisites: [token_refresh/supervisor/credentials status]"
```

---

## Supervisor Detection

The Haiku Supervisor daemon monitors all headless Claude spawns:

```bash
# View supervisor logs
tail -50 /home/john/Thunderbird/logs/haiku_supervisor.log | grep "Spawning Claude"

# Check for failures
tail -50 /home/john/Thunderbird/logs/haiku_supervisor.log | grep -E "FAILED|ERROR"
```

Violations (direct subprocess.Popen calls detected) → logged → escalated to COS.

---

## TLDR — For Agents

**OpenCode spawning headless Claude?**
```python
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

result = dispatch_to_headless_claude(
    task_description="...",
    output_file_path="/home/john/Thunderbird/output/...",
    task_name="..."
)
```

**That's it.** Don't deviate. Don't use subprocess.Popen directly.

---

## References

- **Definitive Spawn Guide:** `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` ← **READ THIS FIRST**
- **Standing Order:** `CLAUDE.md` section "HARD RULE — HEADLESS CLAUDE DISPATCH"
- **Layer 1 Code:** `core/ai_infra/thunderbird_headless_spawn.py`
- **Layer 2 Code (OpenCode):** `OpsCenter/opencode_headless_claude_dispatch.py`

---

*Updated 2026-04-24 | Hale, COS*
