# HEADLESS CLAUDE SPAWN GUIDE — FOOLPROOF REFERENCE
**Version 2.1 | 2026-05-25 | Critical Infrastructure Document**

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

## 📦 CLAUDE AGENTS — MODERN SPAWN PATTERN (v2.1.142–v2.1.149)

**Claude Code v2.1.142–v2.1.149 introduced a superior spawning mechanism.** Prefer `claude agents` over raw `-p` subprocess for all new tasks. The agent system handles lifecycle, output capture, and background/resume natively.

### Pattern A: Scriptable Agent with `--json` (v2.1.145+)

Outputs structured JSON with status, timestamps, and result content. Best for programmatic integration.

```bash
claude agents --json -p "Your task here" --model claude-sonnet-4-6
```

**Expected output:**
```json
{"status":"done","result":"Task output here","timestamps":{"start":"...","end":"..."}}
```

Output includes GitHub repo and PR information in status line JSON input when detected.

**Use when:** You need machine-readable output, structured status reporting, tmux-resurrect, status bars, or session picker integration.

### Pattern B: Background Agent with `--bg` + `/resume` (v2.1.144+)

Spawns a detached agent that can be resumed in a later session. Best for long-running tasks (>10 min).

```bash
# Spawn in background — returns immediately with session ID
claude agents --bg -p "Long running task" --model claude-sonnet-4-6
# Output: "Agent spawned in background. Session: <session_id>"
```

**Resume the session later:**
```bash
# List all sessions (interactive + background, bg sessions marked with `bg`)
claude agents
# Or get JSON for scripting:
claude agents --json
# Resume a specific session:
claude /resume <session_id>
```

**Key behavior (v2.1.143+):** Background sessions preserve `--mcp-config`, `--settings`, `--add-dir`, `--plugin-dir`, and `--strict-mcp-config` across retire→wake cycles. The `/bg` and `←`-detach commands also preserve `--fallback-model` and `--allow-dangerously-skip-permissions`.

**Elapsed time (v2.1.144+):** Background subagent completion notifications now include elapsed duration (e.g. "Agent completed · 3h 2m 5s").

**Idle wake (v2.1.143+):** Background sessions now preserve the model and effort level you set after waking from idle.

**Critical:** The `--bg` flag replaces the old `start_new_session=True` + WRITE [PATH] dance. Output survives agent exit natively.

### Pattern C: Full Agent Dispatch with All Flags (v2.1.142+)

All `claude agents` dispatches support these flags for explicit configuration:

```bash
claude agents \
  -p "Your task" \
  --model claude-sonnet-4-6 \
  --effort high \
  --mcp-config /home/john/.claude/mcp.json \
  --settings /home/john/.claude/settings.json \
  --add-dir /home/john/Thunderbird \
  --plugin-dir /home/john/.claude/plugins \
  --permission-mode accept \
  --dangerously-skip-permissions
```

| Flag | Purpose | Required? |
|------|---------|-----------|
| `-p "..."` | The prompt/task | Always unless resuming |
| `--model` | Model override (sonnet-4-6, haiku-4-5, opus-4-7) | Recommended |
| `--effort` | Effort level (low, medium, high, xhigh) | Optional |
| `--mcp-config` | Path to MCP server config JSON | **Required — see below** |
| `--settings` | Path to Claude settings.json | Optional |
| `--add-dir` | Additional directory to add to context | Optional |
| `--plugin-dir` | Plugin directory path | Optional |
| `--permission-mode` | Permission mode (auto, accept, bypass) | Optional |
| `--dangerously-skip-permissions` | Skip all permission prompts | Optional |

**Why `--mcp-config` is required:** Without it, Claude spins up its own MCP host and may enter D-state (uninterruptible sleep) waiting for connections. Confirmed by watcher service 2026-05-17.

**Why `--dangerously-skip-permissions` persists (v2.1.143):** This flag now persists across retire→wake cycles so background agents don't stall waiting for permission approval.

### Pattern D: Pinned Background Sessions (v2.1.147+)

Pinned sessions stay alive when idle and are restarted in place to apply Claude Code updates. They're shed under memory pressure only after non-pinned sessions.

```bash
# In claude agents dashboard, press Ctrl+T to pin a session
# Pinned sessions survive idle timeout and auto-update restarts
```

### Pattern E: Workflow Tool — Deterministic Multi-Agent (v2.1.147+)

**Off by default.** Set `CLAUDE_CODE_WORKFLOWS=1` to enable the Workflow tool for deterministic multi-agent orchestration.

```bash
export CLAUDE_CODE_WORKFLOWS=1
claude agents -p "Run the analysis workflow" --model claude-sonnet-4-6
```

### Session List Scoping (v2.1.141+)

Scope `claude agents` to a specific directory:
```bash
claude agents --cwd /home/john/Thunderbird
```

### `/model` Behavior Change (v2.1.144+)

`/model` now changes the model for the **current session only**. Press `d` in the model picker to set a default for new sessions.

### `/bg` Preservation (v2.1.143+)

`/bg` (in-session background) now preserves ALL of: `--mcp-config`, `--settings`, `--add-dir`, `--plugin-dir`, `--strict-mcp-config`, `--fallback-model`, and `--allow-dangerously-skip-permissions`.

### MCP Startup Overlap (v2.1.144+)

SDK/headless MCP startup now overlaps with session initialization instead of blocking before the first turn. Up to 2s faster with slow MCP servers.

### `worktree.bgIsolation: "none"` Setting (v2.1.143+)

For repos where git worktrees are impractical, set this in settings.json to let background sessions edit the working copy directly:

```json
{
  "worktree": {
    "bgIsolation": "none"
  }
}
```

### `/usage` Per-Category Breakdown (v2.1.149+)

`/usage` now shows a per-category breakdown of what's driving your limit usage — skills, subagents, plugins, and per-MCP-server cost.

### Migration Guide — Legacy `-p` → `agents`

| Legacy (`-p` subprocess) | Modern (`claude agents`) | Benefit |
|---|---|---|
| `claude -p "..."` | `claude agents -p "..."` | Structured output, no WRITE [PATH] needed |
| `start_new_session=True` | `--bg` flag | Native background, no process detachment hack |
| WRITE [PATH] in prompt | `--json` output | Output captured automatically, no file path needed |
| Manual token injection | Auto-inherited | No OAuth boilerplate |
| `proc = subprocess.Popen(...)` | Shell command | No Python wrapper needed |
| No idle persistence | Preserved model/effort | Survives sleep/wake cycles |
| Lost on parent exit | Pinned sessions survive | Survives Claude Code updates |

### Fallback: If `claude agents` is unavailable

Check installed version:
```bash
claude --version
# If < v2.1.142: fall back to legacy -p pattern below
# Update: npm update -g @anthropic-ai/claude-code
```

If update is not possible or agents fails, the legacy pattern in Section 4 still works.

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

## LEGACY SPAWN PATTERN (DEPRECATED) — COPY THIS EXACTLY ONLY IF `claude agents` IS UNAVAILABLE

> ⚠️ **STRONGLY DEPRECATED.** This section documents the legacy `-p` subprocess pattern **only for fallback** (pre-v2.1.142 or when `claude agents` is unavailable). For all new tasks, **you MUST use `claude agents` (Section 3 above).** The legacy pattern is error-prone and lacks modern features.

### ❌ THE LEGACY PATTERN (Avoid Unless Absolutely Necessary)

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

### ❌ PATTERN 1: Using Legacy `-p` When `claude agents` Is Available

```bash
# DEPRECATED — This still works but misses features
claude -p "Your task" --model claude-sonnet-4-6

# PREFERRED — Use agents pattern instead
claude agents --bg -p "Your task" --model claude-sonnet-4-6 --mcp-config /home/john/.claude/mcp.json
```

**Why it's suboptimal:** Legacy `-p` requires OAuth injection, `start_new_session=True`, and explicit `WRITE [PATH]` in prompts. The `agents` pattern handles all of this automatically and adds resume capability.

**FIX:** Use `claude agents --bg` for all new spawns (v2.1.142+).

---

### ❌ PATTERN 2: No `--mcp-config` with `claude agents`

```bash
# WRONG — May cause D-state (uninterruptible sleep)
claude agents -p "Your task"

# CORRECT — Explicit MCP config
claude agents -p "Your task" --mcp-config /home/john/.claude/mcp.json
```

**Why it fails:** Without `--mcp-config`, Claude spins up its own MCP host and may enter D-state waiting for connections. Confirmed by watcher service 2026-05-17.

**FIX:** Always pass `--mcp-config /home/john/.claude/mcp.json` with `claude agents`.

---

### ❌ PATTERN 3: Legacy — No `start_new_session=True`

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

**FIX (legacy):** Add `start_new_session=True` to Popen() call.
**FIX (modern):** Use `claude agents --bg` instead — no `start_new_session` needed.

---

### ❌ PATTERN 4: Legacy — Relying on stdout/stderr without explicit WRITE to file

```python
# WRONG — Output will be lost
prompt = "Analyze this data and tell me what you find"
proc = subprocess.Popen([CLAUDE_BIN, "-p", prompt], ...)
```

**Why it fails:** Claude writes to stdout. But your process can't read it (it exits before Claude finishes). Output is lost.

**FIX (legacy):** Prompt MUST include explicit `WRITE [PATH]` instruction.
**FIX (modern):** Use `claude agents --json` — output captured automatically.

---

### ❌ PATTERN 5: Legacy — No log redirection

```python
# WRONG — You can't monitor what happened
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    env=env,
    start_new_session=True,
    # Missing: stdout/stderr redirection
)
```

**Why it fails:** If Claude fails, you have no log to debug.

**FIX (legacy):** Always redirect to a log file.
**FIX (modern):** `claude agents --bg` writes logs automatically.

---

### ❌ PATTERN 6: No explicit model selection

```python
# WRONG — Uses default model (may be Opus, expensive)
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    # Missing: --model argument
    ...
)
```

**Why it fails:** You waste credits on Opus when Haiku would work. Task becomes expensive.

**FIX:** Always specify model:
```bash
--model claude-sonnet-4-6    # General work (MAX plan)
--model claude-haiku-4-5     # Quick/bulk tasks (MAX plan)
--model claude-opus-4-7      # Heavy reasoning (MAX plan)
```

---

### ❌ PATTERN 7: Legacy — OAuth token not injected

```python
# WRONG — Token not in environment
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p", prompt],
    env={},  # Empty environment = no token
    ...
)
```

**Why it fails:** Claude tries to auth, finds no token, fails immediately.

**FIX (legacy):** Load token from credentials file and inject into env.
**FIX (modern):** Use `claude agents --bg` — token auto-inherited.

---

### ❌ PATTERN 8: Using `--bg` on Claude Code < v2.1.142

```bash
# WRONG — Flag doesn't exist in older versions
claude agents --bg -p "Your task"

# CHECK FIRST:
claude --version
```

**Why it fails:** The `--bg` flag was introduced in v2.1.142, and `agents --json` in v2.1.145. Older versions silently ignore unrecognized flags.

**FIX:** Check version and update if needed: `npm update -g @anthropic-ai/claude-code`

---

## VERIFICATION CHECKLIST — DO THIS BEFORE SPAWNING

| Check | Command | Expected Result | What to Do If Fails |
|-------|---------|-----------------|-------------------|
| Claude Code version ≥ 2.1.142 | `claude --version` | `2.1.142` or higher | `npm update -g @anthropic-ai/claude-code` |
| Token monitor timer running | `systemctl --user status claude-token-monitor.timer --no-pager` | `Active: active (waiting)` | `systemctl --user enable --now claude-token-monitor.timer` |
| OAuth keepalive timer running | `systemctl --user status claude-oauth-keepalive.timer --no-pager` | `Active: active (waiting)` | `systemctl --user enable --now claude-oauth-keepalive.timer` |
| OAuth credentials exist | `ls -la ~/.claude/.credentials.json` | File exists, readable | Have Commander re-authenticate in Claude Desktop |
| Watchdog running | `systemctl --user status thunderbird-watchdog.timer --no-pager` | `Active: active (waiting)` | `systemctl --user enable --now thunderbird-watchdog.timer` |
| MCP config exists | `ls -la ~/.claude/mcp.json` | File exists, readable | `echo '{}' > ~/.claude/mcp.json` |
| /logs directory exists | `ls -ld /home/john/Thunderbird/logs` | Directory exists | `mkdir -p /home/john/Thunderbird/logs` |
| Output directory exists | `ls -ld /home/john/Thunderbird/output` | Directory exists | `mkdir -p /home/john/Thunderbird/output` |

**Do NOT proceed to spawn unless ALL checks pass. Proceeding with failed checks = wasted time.**

---

## EXACT COMPLETE EXAMPLES

### ✅ PREFERRED: Modern `claude agents --bg` Pattern (v2.1.142+)

```python
#!/usr/bin/env python3
"""
Headless Claude spawn — MODERN agents pattern (preferred for v2.1.142+)
"""
import subprocess
import sys
from pathlib import Path

CLAUDE_BIN = "/home/john/.local/bin/claude"
LOG_DIR = Path("/home/john/Thunderbird/logs")
LOG_DIR.mkdir(exist_ok=True)

prompt = """
Analyze customer data for Dreams2Memories Travel, LLC.

TASK: Summarize the top 3 trends in customer preferences.
Write your complete analysis as structured markdown.
"""

log_file = LOG_DIR / f"claude_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Modern agents pattern — no OAuth injection needed, no start_new_session, no WRITE [PATH]
proc = subprocess.Popen(
    [
        CLAUDE_BIN, "agents", "--bg",
        "-p", prompt,
        "--model", "claude-sonnet-4-6",
        "--mcp-config", "/home/john/.claude/mcp.json",
        "--effort", "high",
    ],
    stdout=open(log_file, "w"),
    stderr=subprocess.STDOUT,
)
print(f"Agent spawned (PID {proc.pid}). Resume with: claude agents")
print(f"Log: {log_file}")
```

**What changed from legacy pattern:**
- No `start_new_session=True` needed — `--bg` handles detachment
- No OAuth token injection needed — auto-inherited
- No `WRITE [PATH]` in prompt needed — output survives agent exit
- No `env=` manipulation needed
- Resume capability via `claude /resume <session_id>` or `claude agents` dashboard

### ✅ FALLBACK: Legacy `-p` Subprocess Pattern (Pre-v2.1.142)

> **Use only if `claude agents` is unavailable (check: `claude --version`).**
> Otherwise, prefer the modern pattern above.

```python
#!/usr/bin/env python3
"""
Headless Claude spawn — LEGACY subprocess pattern (fallback only)
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

# Build prompt (MUST include explicit WRITE instruction — critical for legacy pattern)
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
- [ ] I am using `claude agents` for new spawns (prefer `--bg` or `--json`)
- [ ] I am explicitly specifying `--mcp-config /home/john/.claude/mcp.json`
- [ ] I am explicitly specifying `--model` (e.g., `claude-sonnet-4-6`, `claude-haiku-4-5`)
- [ ] I am NOT using the legacy `-p` subprocess pattern unless absolutely necessary
- [ ] I understand that `claude agents --bg` detaches the process and manages output/logs automatically
- [ ] I understand that `claude agents --json` provides structured, machine-readable output

**If any checkbox is unchecked, DO NOT SPAWN. Go back and fix it first.**

---

*This guide is the single source of truth for headless Claude spawning. Print it. Memorize it. Follow it precisely. Precision saves time. Imprecision wastes the Commander's time immensely.*

**Last updated: 2026-04-23 by COS**
