# Foolproof Research Task — Claude Integration Research
**Version 1.0 | 2026-04-27 | For: OpenCode, Claude Code, Manual Execution**

---

## ⚡ Quick Start (60 seconds)

### For OpenCode:
```bash
cd /home/john/Thunderbird/OpsCenter
bash run_research_task.sh
```

### For Claude Code:
```bash
cd /home/john/Thunderbird/OpsCenter
python3 research_integrators_headless.py
# Wait for spawn, then check logs/output
```

### For Manual/Testing:
```bash
python3 diagnose_research_system.py  # Check prerequisites
bash run_research_task.sh             # Run the full task
```

---

## System Design — Why This Works

### The Problem (Old Approach)
- OpenCode called `thunderbird_model_dispatcher.py` (too complex)
- Dispatcher had syntax errors and routing issues
- Unreliable file writes and email sends
- Multiple failure points, no clear recovery

### The Solution (This Approach)
- **Single-purpose scripts**: Each does ONE thing reliably
- **Foolproof pattern**: Direct subprocess spawn with explicit WRITE [PATH]
- **Clear separation**: Headless spawn → File write → Email send
- **Verification built-in**: Diagnostic script checks all prerequisites

---

## Scripts Overview

### 1. `diagnose_research_system.py` (ALWAYS RUN FIRST)
**Purpose**: Verify all prerequisites before running research.

**What it checks**:
- ✅ Claude CLI binary exists
- ✅ OAuth credentials file exists and is valid
- ✅ Token refresh daemon is running
- ✅ Output directories exist
- ✅ Gmail module is available

**Run before ANYTHING**:
```bash
python3 diagnose_research_system.py
```

**If ANY check fails**: Fix the issue and rerun diagnostics.

---

### 2. `research_integrators_headless.py` (CORE RESEARCH TASK)
**Purpose**: Spawn headless Claude to research 3rd-party Claude integrators, agentic models, and voice control.

**The Foolproof Pattern**:
1. Load OAuth token from `~/.claude/.credentials.json`
2. Build prompt with **explicit `WRITE [PATH]` instruction**
3. Spawn subprocess with `start_new_session=True` (CRITICAL for detachment)
4. Redirect stdout/stderr to log file
5. Specify model explicitly (`claude-sonnet-4-6`)
6. **Return immediately** — do NOT wait for subprocess

**Output**:
- Log: `/home/john/Thunderbird/logs/headless_claude_integrators_YYYYMMDD_HHMMSS.log`
- Result: `/home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_YYYYMMDD_HHMMSS.md`

**Run it directly**:
```bash
python3 research_integrators_headless.py
```

**Monitor progress**:
```bash
# Watch the log file
tail -f /home/john/Thunderbird/logs/headless_claude_integrators_*.log

# Check output file
tail -f /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_*.md
```

---

### 3. `send_research_email.py` (EMAIL SEND)
**Purpose**: Send completed research findings to johnloucks3@gmail.com.

**What it does**:
1. Reads research file
2. Creates Gmail draft in d2mconcierge account
3. Sends draft to Commander's email
4. Logs status

**Run it after research completes**:
```bash
python3 send_research_email.py /path/to/research_integrators_RESULT_*.md
```

---

### 4. `run_research_task.sh` (ORCHESTRATOR)
**Purpose**: Run the FULL workflow: spawn research → wait → send email.

**What it does**:
1. Calls `research_integrators_headless.py` to spawn Claude
2. Waits for output file to appear (non-blocking)
3. Calls `send_research_email.py` to send results
4. Reports completion

**Use this for normal workflow**:
```bash
bash run_research_task.sh
```

---

## The Foolproof Pattern Explained

### Why Each Element Is Critical

#### 1. Explicit `WRITE [PATH]` in Prompt
```python
prompt = f"""
TASK: Research...

===== CRITICAL INSTRUCTION =====
WRITE your COMPLETE research output to {OUTPUT_FILE}
DO NOT output to stdout.
ALL output must go to the file path above.
===== END CRITICAL INSTRUCTION =====
"""
```

**Why**: Without this, Claude writes to stdout, which is lost. Output is invisible and task fails silently.

#### 2. OAuth Token Injection
```python
env = dict(os.environ)
env["CLAUDE_CODE_OAUTH_TOKEN"] = token
```

**Why**: Claude CLI reads this env var for authentication. Without it, 401 Unauthorized.

#### 3. `start_new_session=True`
```python
proc = subprocess.Popen(
    [...],
    start_new_session=True,  # ← CRITICAL
)
```

**Why**: Without this, Claude becomes a child process. When parent exits, Claude dies. Task is lost.

#### 4. Log File Redirection
```python
proc = subprocess.Popen(
    [...],
    stdout=open(log_file, "w"),
    stderr=subprocess.STDOUT,
)
```

**Why**: Captures all Claude output for debugging. Without it, failures are invisible.

#### 5. Explicit Model Selection
```python
proc = subprocess.Popen(
    [...,
     "--model", "claude-sonnet-4-6",
     ...]
)
```

**Why**: Without this, defaults to Opus (expensive). Must specify Sonnet.

#### 6. Return Immediately (No Wait)
```python
print(f"Spawned Claude (PID {proc.pid})")
return True  # ← Do NOT call proc.wait()
```

**Why**: Parent process exits. Claude continues independently. Task doesn't block.

---

## Common Scenarios

### Scenario 1: Running from OpenCode
```bash
# OpenCode calls this:
cd /home/john/Thunderbird/OpsCenter && bash run_research_task.sh
```

**Result**:
- Claude spawns in background
- Research runs for 5-15 minutes
- Output saved to opencode_knowledge folder
- Email sent to Commander
- OpenCode moves on (no blocking)

---

### Scenario 2: Manual Testing
```bash
# Check system first
python3 diagnose_research_system.py

# If all green, run research
python3 research_integrators_headless.py

# Monitor in another terminal
tail -f /home/john/Thunderbird/logs/headless_claude_integrators_*.log

# Once research completes (15+ min), send email
python3 send_research_email.py /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_*.md
```

---

### Scenario 3: Debugging Failures

**Claude won't spawn**:
```bash
python3 diagnose_research_system.py  # Identify the blocker
# Most common: OAuth credentials missing or token daemon inactive
```

**Claude spawned but no output**:
```bash
tail -f /home/john/Thunderbird/logs/headless_claude_integrators_*.log
# Check if prompt has WRITE [PATH] instruction (should be in log)
# Check if output file is being created
```

**Output file exists but empty**:
```bash
# Claude may still be writing. Wait longer.
# Or check log file for errors.
ls -lah /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_*.md
tail -f /home/john/Thunderbird/logs/headless_claude_integrators_*.log
```

**Email send failed**:
```bash
# Check d2mconcierge Gmail account for draft
# Or run diagnose_research_system.py to check Gmail config
```

---

## Monitoring & Logging

### Live Monitoring
```bash
# Terminal 1: Watch logs
tail -f /home/john/Thunderbird/logs/headless_claude_integrators_*.log

# Terminal 2: Watch output growth
watch -n 5 "ls -lah /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_*.md"

# Terminal 3: Check process
ps aux | grep claude | grep -v grep
```

### Log Locations
- **Research Logs**: `/home/john/Thunderbird/logs/headless_claude_integrators_YYYYMMDD_HHMMSS.log`
- **Output Markdown**: `/home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_YYYYMMDD_HHMMSS.md`
- **Email Logs**: Check Gmail d2mconcierge account (Sent folder)

---

## Execution Timeline

### Expected Duration
1. **Spawn**: <1 second
2. **Research**: 5-15 minutes (depending on Claude load)
3. **Email**: <5 seconds (once research completes)

### Total Time: ~10-20 minutes (end-to-end)

---

## Integration for OpenCode

### In OpenCode's Task Handler:
```python
import subprocess

def task_research_integrators():
    """OpenCode task: Research Claude integrators."""
    result = subprocess.run(
        ["bash", "/home/john/Thunderbird/OpsCenter/run_research_task.sh"],
        capture_output=True,
        text=True,
        timeout=120  # 2 min timeout for spawn + email send
    )
    
    if result.returncode == 0:
        print("✅ Research task complete")
        print(result.stdout)
    else:
        print(f"⚠️ Research spawn/send had issues (check logs)")
        print(result.stdout)
        print(result.stderr)
```

### What OpenCode Gets Back
- Immediate return (research runs in background)
- Status printed to stdout
- Full logs in `/home/john/Thunderbird/logs/` if debugging needed

---

## Failure Recovery

### If Task Fails Silently
1. Run diagnostics: `python3 diagnose_research_system.py`
2. Fix any issues (usually OAuth or daemon related)
3. Rerun: `python3 research_integrators_headless.py`

### If Output File Doesn't Appear
1. Check log file for errors: `tail -50 /home/john/Thunderbird/logs/headless_claude_integrators_*.log`
2. Check if prompt has WRITE [PATH] instruction (should be in logs)
3. Wait longer — Claude may still be processing

### If Email Send Fails
1. Check d2mconcierge Gmail for draft (check Drafts folder)
2. Run diagnostics: `python3 diagnose_research_system.py`
3. Manually send draft if it exists in Gmail

---

## Important Notes

⚠️ **Do NOT do these**:
- ❌ Don't call `proc.wait()` — Claude continues independently
- ❌ Don't remove the `WRITE [PATH]` from the prompt
- ❌ Don't use default model — always specify `claude-sonnet-4-6`
- ❌ Don't skip `start_new_session=True` — task will die when parent exits
- ❌ Don't pipe stdout directly — use log file redirection

✅ **Always do these**:
- ✅ Run diagnostics first: `python3 diagnose_research_system.py`
- ✅ Monitor logs: `tail -f /home/john/Thunderbird/logs/headless_claude_integrators_*.log`
- ✅ Check output file exists (non-empty)
- ✅ Let Claude run in background (no blocking)

---

## Support / Issues

**If task fails**: Check `/home/john/Thunderbird/logs/headless_claude_integrators_*.log` first.

**If OAuth issues**: Run `systemctl --user status claude-token-monitor.timer --no-pager` and enable if inactive.

**If email doesn't send**: Check d2mconcierge Gmail Drafts folder for the draft (may need manual send).

---

*This system is designed to be foolproof. If it fails, the logs will tell you exactly why.*
