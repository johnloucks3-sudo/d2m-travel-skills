# OPENCODE HEADLESS CLAUDE — SIMPLE VERSION
## How to Make Claude Run in the Background (For Real Dummies)

**Last Updated:** 2026-04-26  
**Status:** VERIFIED WORKING

---

## WHAT THIS DOES

You want Claude to:
1. Do work in the background
2. Write output to a file
3. Let your OpenCode task finish while Claude keeps running

This is called "headless." This document tells you exactly how.

---

## THE RULE

**Use this function. Don't write subprocess code yourself.**

```python
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

result = spawn_headless_claude(
    prompt="Your task here",
    output_file="/home/john/Thunderbird/output/my_output.txt",
    task_name="descriptive_name",
    model="claude-haiku-4-5-20251001"
)

print(f"Claude is running as PID {result['pid']}")
print(f"Output will appear at: {result['output_file']}")
```

That's it. Do NOT write subprocess.Popen yourself. Do NOT use -p flag. Do NOT ignore this.

---

## WHAT HAPPENS INTERNALLY (So You Understand Why)

```
OpenCode                          Claude Desktop                System
   │                                  │                            │
   │ spawn_headless_claude()          │                            │
   │    ↓                             │                            │
   │ ✓ Check token refresh daemon ←──┬──────────────────────────┐ │ (systemd)
   │ ✓ Check supervisor daemon    ←──┤  Is it running?          │ │
   │ ✓ Check credentials file     ←──┤  ~/.claude/.credentials  │ │
   │    ↓                             │                        ←─┘
   │ Load OAuth token from credentials.json
   │    ↓
   │ Strip ANTHROPIC_API_KEY (forces OAuth use)
   │    ↓
   │ Start Claude subprocess with:
   │   - stdin = receive prompt from us
   │   - stdout/stderr = capture to file
   │   - start_new_session=True (detached)
   │    ↓
   │ Send prompt via stdin
   │    ↓
   │ Claude authenticates with OAuth token (from credentials)
   │    ↓
   │ Claude outputs to file
   │    ↓
   │ Return PID + output file path to OpenCode
   │ (OpenCode can now exit)
   │    ↓
   │ Claude continues running independently
```

**Why OAuth works:**
- The `-p/--print` flag disables OAuth (forces API key auth)
- We DON'T use `-p` — we use stdin/stdout PIPE instead
- This allows OAuth credentials from `~/.claude/.credentials.json` to be used
- Result: `CLAUDE_CODE_OAUTH_TOKEN` environment variable is read automatically

---

## COPY-PASTE RECIPE

Use this exact pattern every time:

```python
#!/usr/bin/env python3
"""
OpenCode task: Generate something using Claude
"""

from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
import json

# 1. Define what you want Claude to do
prompt = f"""
You are an AI assistant for Dreams2Memories Travel, LLC.

TASK: Analyze the cruise market for Regent Seven Seas.
REQUIREMENTS:
- Look for 3 key trends
- Focus on 2026 bookings
- Identify one competitor move worth noting

OUTPUT: Write a 500-word market analysis.
"""

# 2. Spawn Claude in background
result = spawn_headless_claude(
    prompt=prompt,
    output_file="/home/john/Thunderbird/output/regent_market_analysis.txt",
    task_name="regent_market_analysis",
    model="claude-haiku-4-5-20251001"
)

# 3. Check if spawn succeeded
if result["status"] != "SPAWNED":
    print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
    print(f"Logs: {result.get('log_file')}")
    exit(1)

# 4. Report success (Claude is running)
print(f"✅ Task spawned successfully")
print(f"   PID: {result['pid']}")
print(f"   Output: {result['output_file']}")
print(f"   Logs: {result['log_file']}")

# 5. That's it — you can exit now
# Claude will keep running in the background
```

---

## COMMON MISTAKES (DON'T DO THESE)

### ❌ MISTAKE 1: Using subprocess.Popen yourself
```python
# WRONG — Don't do this
import subprocess
proc = subprocess.Popen(["claude", "-p", prompt])
```

**Why:** You'll get OAuth auth failures. Always use `spawn_headless_claude()`.

---

### ❌ MISTAKE 2: Using -p flag anywhere
```python
# WRONG — -p disables OAuth
["/home/john/.local/bin/claude", "-p", prompt]
```

**Why:** `-p/--print` flag disables OAuth. The wrapper handles this for you.

---

### ❌ MISTAKE 3: Trying to read output immediately
```python
# WRONG — Output file doesn't exist yet
result = spawn_headless_claude(...)
with open(result["output_file"]) as f:
    data = f.read()  # ← FAILS, file still being written
```

**Why:** Claude is still running. File doesn't exist yet. Poll it or set up a watcher.

---

### ❌ MISTAKE 4: Forgetting to set ANTHROPIC_API_KEY
The wrapper handles this automatically. You don't need to do anything.

---

## WHAT TO CHECK IF IT FAILS

**Step 1: Read the log file**
```bash
tail -50 /home/john/Thunderbird/logs/claude_*.log
```

**Step 2: Check prerequisites**
```bash
systemctl is-active claude-token-refresh.timer
systemctl is-active claude-haiku-supervisor.timer
ls -la ~/.claude/.credentials.json
```

**Step 3: If still broken, share the log with COS**

---

## THE RETURN VALUE (What You Get Back)

```python
{
    "status": "SPAWNED",           # ← SUCCESS: Claude is running
    "pid": 2039799,                # Process ID (for monitoring)
    "log_file": "/path/to/...",   # Where we wrote logs
    "output_file": "/path/to/...", # Where Claude writes output
    "model": "claude-haiku-...",   # Model used
    "task_name": "task_name",      # Your task name
    "can_retry": false             # If True, you can retry after delay
}
```

If status is NOT "SPAWNED", check the `error` field and the `log_file`.

---

## MODELS TO USE

- `claude-haiku-4-5-20251001` — Fast, cheap (default, use this)
- `claude-sonnet-4-6-20250514` — Smarter, slower
- `claude-opus-4-7-20250121` — Smartest, slowest

Haiku is fine for most tasks. Sonnet if you need better reasoning.

---

## THAT'S IT

```python
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

result = spawn_headless_claude(
    prompt="your task",
    output_file="/home/john/Thunderbird/output/something.txt",
    task_name="descriptive_name"
)

if result["status"] == "SPAWNED":
    print(f"✅ Running as PID {result['pid']}")
else:
    print(f"❌ Failed: {result.get('error')}")
```

Copy this pattern. Use it everywhere. Stop writing custom subprocess code.

---

*Simple version written for OpenCode/OpenRouter teams. Verify working 2026-04-26.*
