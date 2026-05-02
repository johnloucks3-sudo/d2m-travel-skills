# HEADLESS CLAUDE SPAWN GUIDE — FOOLPROOF REFERENCE
**Version 1.0 | 2026-04-23 | Critical Infrastructure Document**

---

## ⚠️ READ THIS FIRST — NO EXCEPTIONS

**This document is your ONLY reliable path to spawning headless Claude without wasting Commander's time.**

If you do not follow this **precisely**, Claude will:
- Fail silently (process dies, no output, no error visible)
- Exhaust credits on retries
- Miss task deadlines
- Require manual recovery by Commander or COS

**Failure costs time. Precision saves time.**

---

## WHAT IS HEADLESS CLAUDE?

Headless Claude = `claude -p "PROMPT"` running as a **background subprocess**, no Claude Desktop app needed, output written to disk.

**Why it matters:** 
- Runs without human interaction
- Continues running while you (the AI agent) exit
- Output captured to log file
- Token-aware (uses OAuth credentials automatically)

**When to use it:**
- Long-running tasks (>10 min)
- Background processing (research, analysis, file generation)
- Batch operations
- When you need to spawn Claude and then exit

---

## THE THREE MANDATORY PREREQUISITES

### ✅ PREREQUISITE 1: Token Refresh Timers MUST Be Running

**Check this FIRST. Every time. No exceptions.**

```bash
systemctl --user status claude-token-monitor.timer claude-oauth-keepalive.timer --no-pager
```

**Expected output (both timers):**
```
Active: active (waiting)
```

**If either shows `inactive` or `failed`:**
```bash
systemctl --user enable --now claude-token-monitor.timer
systemctl --user enable --now claude-oauth-keepalive.timer
```

> **⚠️ NOTE (2026-04-24):** Earlier versions of this guide referenced `claude-token-refresh.timer` and `claude-haiku-supervisor.timer`. Those timers **do not exist** on this system. The actual OAuth refresh is handled by `claude-token-monitor.timer` + `claude-oauth-keepalive.timer` (both user-level). Do not attempt to check or restart the old names.

**Why this matters:** Token keepalive fires every ~30 minutes. Without it, your token will expire within hours and Claude will fail silently.

---

### ✅ PREREQUISITE 2: OAuth Credentials File MUST Exist

**Check this SECOND.**

```bash
ls -la ~/.claude/.credentials.json
```

**Expected:** File exists, readable, contains `claudeAiOauth` with `accessToken` and `expiresAt` fields.

**If file missing or corrupted:**
- Have Commander re-authenticate via Claude Desktop app
- File will be created/refreshed automatically
- Do NOT proceed until file exists

**Why this matters:** Headless Claude reads this file for OAuth token. No file = no auth = instant failure.

---

### ✅ PREREQUISITE 3: Thunderbird Watchdog MUST Be Running

**Check this THIRD.**

```bash
systemctl --user status thunderbird-watchdog.timer --no-pager
```

**Expected output:**
```
Active: active (waiting)
```

**If inactive:**
```bash
systemctl --user enable --now thunderbird-watchdog.timer
```

> **⚠️ NOTE (2026-04-24):** Earlier versions of this guide referenced `claude-haiku-supervisor.timer`. That timer **does not exist** on this system. Failure monitoring is handled by `thunderbird-watchdog.timer` (user-level). Do not attempt to check or restart the old name.

**Why this matters:** Watchdog detects spawn failures and alerts COS. Without it, failures go unnoticed and tasks are silently lost.

---

## THE EXACT SPAWN PATTERN — COPY THIS EXACTLY

### ✅ THE CORRECT PATTERN (Copy This Exactly)

```python
import subprocess
from pathlib import Path
from datetime import datetime

# 1. Set up paths
log_dir = Path("/home/john/Thunderbird/logs")
log_dir.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = log_dir / f"headless_claude_{ts}.log"

# 2. Build your prompt (MUST include explicit WRITE [PATH] instruction)
prompt = f"""
You are performing a task for Commander John Loucks.

TASK: [Your specific task description here]

INSTRUCTIONS:
1. Perform the task completely
2. WRITE your complete output to {output_file_path} with this exact content:
   [Your expected output format/content]

Output nothing to stdout. All output goes to {output_file_path}.
"""

# 3. Load OAuth environment
import json
creds_path = Path.home() / ".claude" / ".credentials.json"
env = dict(os.environ)
if creds_path.exists():
    creds = json.loads(creds_path.read_text())
    token = creds.get("claudeAiOauth", {}).get("accessToken")
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

# 4. Spawn the subprocess (start_new_session=True is CRITICAL)
proc = subprocess.Popen(
    [
        "/home/john/.local/bin/claude",
        "-p", prompt,
        "--model", "claude-haiku-4-5-20251001",
        "--output-format", "text"
    ],
    stdout=open(log_path, "w"),
    stderr=subprocess.STDOUT,
    env=env,
    start_new_session=True,  # ← DO NOT REMOVE THIS
)

# 5. Log the spawn event so supervisor can detect it
import logging
logging.info(f"Spawned headless Claude (PID {proc.pid}) → {log_path}")
logging.info(f"Output will be written to {output_file_path}")
```

---

## ❌ COMMON FAILURE PATTERNS — DO NOT DO THESE

### ❌ PATTERN 1: No start_new_session=True
```python
# WRONG — This will fail
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    stdout=open(log, "w"),
    stderr=subprocess.STDOUT,
    env=env,
    # Missing: start_new_session=True
)
```

**Why it fails:** Without `start_new_session=True`, Claude process becomes a child of your process. When you exit, Claude dies with you. Task is lost.

**FIX:** Add `start_new_session=True` to Popen() call.

---

### ❌ PATTERN 2: Relying on stdout/stderr without explicit WRITE to file

```python
# WRONG — Output will be lost
prompt = "Analyze this data and tell me what you find"
proc = subprocess.Popen([CLAUDE_BIN, "-p", prompt], ...)
# Waiting for output... but where does it go?
```

**Why it fails:** Claude writes to stdout. But your process can't read it (it exits before Claude finishes). Output is lost. Task fails silently.

**FIX:** Your prompt MUST include explicit `WRITE [PATH]` instruction. Example:
```python
prompt = f"""
Analyze this data.
WRITE your complete analysis to /home/john/Thunderbird/output/analysis_{ts}.txt
"""
```

---

### ❌ PATTERN 3: No log redirection

```python
# WRONG — You can't monitor what happened
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    env=env,
    start_new_session=True,
    # Missing: stdout/stderr redirection
)
```

**Why it fails:** If Claude fails, you have no log to debug. You don't know if it was token issue, prompt issue, or crash. Impossible to fix.

**FIX:** Always redirect to a log file:
```python
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    stdout=open(log_path, "w"),
    stderr=subprocess.STDOUT,
    env=env,
    start_new_session=True,
)
```

---

### ❌ PATTERN 4: No explicit model selection

```python
# WRONG — Uses default model (may be Opus, expensive)
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    # Missing: --model argument
    ...
)
```

**Why it fails:** You waste credits on Opus when Haiku would work. Task becomes expensive. Commander notices.

**FIX:** Always specify model:
```python
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt, "--model", "claude-haiku-4-5-20251001"],
    ...
)
```

---

### ❌ PATTERN 5: OAuth token not injected

```python
# WRONG — Token not in environment
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    env={},  # Empty environment = no token
    ...
)
```

**Why it fails:** Claude tries to auth, finds no token, fails immediately.

**FIX:** Load token from credentials file and inject into env:
```python
import json, os
creds_path = Path.home() / ".claude" / ".credentials.json"
env = dict(os.environ)  # Start with current environment
if creds_path.exists():
    creds = json.loads(creds_path.read_text())
    token = creds.get("claudeAiOauth", {}).get("accessToken")
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

proc = subprocess.Popen([...], env=env, ...)
```

---

## VERIFICATION CHECKLIST — DO THIS BEFORE SPAWNING

| Check | Command | Expected Result | What to Do If Fails |
|-------|---------|-----------------|-------------------|
| Token monitor timer running | `systemctl --user status claude-token-monitor.timer --no-pager` | `Active: active (waiting)` | `systemctl --user enable --now claude-token-monitor.timer` |
| OAuth keepalive timer running | `systemctl --user status claude-oauth-keepalive.timer --no-pager` | `Active: active (waiting)` | `systemctl --user enable --now claude-oauth-keepalive.timer` |
| OAuth credentials exist | `ls -la ~/.claude/.credentials.json` | File exists, readable | Have Commander re-authenticate in Claude Desktop |
| Watchdog running | `systemctl --user status thunderbird-watchdog.timer --no-pager` | `Active: active (waiting)` | `systemctl --user enable --now thunderbird-watchdog.timer` |
| /logs directory exists | `ls -ld /home/john/Thunderbird/logs` | Directory exists | `mkdir -p /home/john/Thunderbird/logs` |
| Output directory exists | `ls -ld /home/john/Thunderbird/output` | Directory exists | `mkdir -p /home/john/Thunderbird/output` |

**Do NOT proceed to spawn unless ALL checks pass. Proceeding with failed checks = wasted time.**

---

## EXACT COMPLETE EXAMPLE — USE THIS TEMPLATE

```python
#!/usr/bin/env python3
"""
Headless Claude spawn example — COPY THIS EXACTLY
"""
import os
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger("headless_spawn")

# Paths
LOG_DIR = Path("/home/john/Thunderbird/logs")
OUTPUT_DIR = Path("/home/john/Thunderbird/output")
CLAUDE_BIN = "/home/john/.local/bin/claude"

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Timestamp for unique filenames
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"claude_spawn_{ts}.log"
output_file = OUTPUT_DIR / f"claude_output_{ts}.txt"

# Load OAuth token
creds_path = Path.home() / ".claude" / ".credentials.json"
env = dict(os.environ)

if not creds_path.exists():
    logger.error(f"FATAL: Credentials file missing at {creds_path}")
    logger.error("Have Commander re-authenticate via Claude Desktop app")
    exit(1)

try:
    creds = json.loads(creds_path.read_text())
    token = creds.get("claudeAiOauth", {}).get("accessToken")
    if not token:
        logger.error("FATAL: No accessToken in credentials file")
        exit(1)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    logger.info("✅ OAuth token loaded successfully")
except Exception as e:
    logger.error(f"FATAL: Could not load credentials: {e}")
    exit(1)

# Build prompt (MUST include explicit WRITE instruction)
prompt = f"""
You are analyzing customer data for Dreams2Memories Travel, LLC.

TASK: Summarize the top 3 trends in customer preferences from the provided dataset.

INSTRUCTIONS:
1. Read the dataset carefully
2. Identify the top 3 trends
3. WRITE your complete analysis to {output_file} in this format:

TREND 1: [Name]
[Description and supporting evidence]

TREND 2: [Name]
[Description and supporting evidence]

TREND 3: [Name]
[Description and supporting evidence]

Do NOT output anything to stdout. All output goes to {output_file}.
"""

# Spawn the subprocess
logger.info(f"Spawning headless Claude → {log_file}")
try:
    proc = subprocess.Popen(
        [
            CLAUDE_BIN,
            "-p", prompt,
            "--model", "claude-haiku-4-5-20251001",
            "--output-format", "text"
        ],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,  # ← CRITICAL: Detaches process
    )
    logger.info(f"✅ Claude spawned successfully (PID {proc.pid})")
    logger.info(f"Output will be written to: {output_file}")
    logger.info(f"Logs available at: {log_file}")
except Exception as e:
    logger.error(f"FATAL: Failed to spawn Claude: {e}")
    exit(1)

# Do NOT wait for process. Exit normally.
logger.info("✅ Spawn successful. Process running in background.")
logger.info(f"COS/Supervisor will monitor at {log_file}")
logger.info("You may exit now.")
```

---

## IF SPAWNING FAILS — DIAGNOSIS FLOWCHART

**Step 1: Check the log file**
```bash
tail -50 /home/john/Thunderbird/logs/claude_spawn_TIMESTAMP.log
```

**Look for:**

| Error Message | Root Cause | Fix |
|---|---|---|
| `[Errno 2] No such file or directory` | Claude binary not found | Check `/home/john/.local/bin/claude` exists |
| `401 Unauthorized` | OAuth token missing or expired | Check credentials file exists; wait for token refresh daemon |
| `402 Payment Required` | Account out of credits | Contact Commander for credit top-up |
| `timeout` | Claude took >10 min | Expected for large tasks; monitor log file |
| Process exited with code 1 | Generic error | Read full log output; escalate to COS |

**Step 2: Verify prerequisites again**
```bash
systemctl --user status claude-token-monitor.timer --no-pager
systemctl --user status claude-oauth-keepalive.timer --no-pager
systemctl --user status thunderbird-watchdog.timer --no-pager
ls -la ~/.claude/.credentials.json
```

**Step 3: If still failing, escalate to COS**
```
Message to COS: "Headless Claude spawn failed. Check log file at [PATH]. 
Verification: 
- Token refresh: [status]
- Supervisor: [status]
- Credentials: [status]"
```

---

## MONITORING AND VERIFICATION

**After spawning, do this:**

1. **Check that process detached:**
   ```bash
   ps aux | grep claude_spawn
   ```
   Should show process running independently (PPID = 1 for detached process)

2. **Monitor the log file:**
   ```bash
   tail -f /home/john/Thunderbird/logs/claude_spawn_TIMESTAMP.log
   ```

3. **Verify output file is being written:**
   ```bash
   watch -n 2 "ls -lah /home/john/Thunderbird/output/claude_output_*.txt"
   ```

4. **Supervisor will detect the spawn:**
   ```bash
   tail -50 /home/john/Thunderbird/logs/haiku_supervisor.log | grep "Spawning Claude"
   ```

---

## ⚠️ STRONG WARNINGS

### Warning 1: Never ignore token refresh daemon status
**If token refresh is inactive, you have ~4 hours before token expires and headless Claude starts failing.** Check it before every spawn.

### Warning 2: Never skip the explicit WRITE [PATH] instruction
**If your prompt doesn't include `WRITE [PATH]`, output is lost and task fails silently.** Every prompt must end with a WRITE instruction.

### Warning 3: Never wait for the subprocess to finish
**Headless Claude runs in background. Don't call `.wait()` or try to read output from subprocess. Let it run independently. Read output from the file it writes to.**

### Warning 4: Never use empty environment
**Always start with `dict(os.environ)` so CLAUDE_CODE_OAUTH_TOKEN is added to an existing environment, not an empty one.**

### Warning 5: Never spawn Claude more than once per 30 seconds
**If you spawn multiple Claude processes rapidly, they may compete for the same token or resource. Space out spawns by at least 30 seconds.**

---

## FINAL CHECKLIST BEFORE SPAWNING

- [ ] Token refresh daemon is `Active: active (waiting)`
- [ ] Haiku supervisor daemon is `Active: active (waiting)`
- [ ] OAuth credentials file exists at `~/.claude/.credentials.json`
- [ ] `/home/john/Thunderbird/logs/` directory exists
- [ ] `/home/john/Thunderbird/output/` directory exists
- [ ] My prompt includes explicit `WRITE [PATH]` instruction
- [ ] I am using `start_new_session=True` in Popen()
- [ ] I am redirecting stdout/stderr to a log file
- [ ] I have injected `CLAUDE_CODE_OAUTH_TOKEN` into the environment
- [ ] I am using `--model claude-haiku-4-5-20251001` (or explicitly chosen model)
- [ ] I am NOT waiting for the process to finish
- [ ] I understand this will write to disk, not return to my code

**If any checkbox is unchecked, DO NOT SPAWN. Go back and fix it first.**

---

*This guide is the single source of truth for headless Claude spawning. Print it. Memorize it. Follow it precisely. Precision saves time. Imprecision wastes the Commander's time immensely.*

**Last updated: 2026-04-23 by COS**
