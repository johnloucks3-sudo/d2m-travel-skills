# OpenCode Integration — Foolproof Research Task
**How to make OpenCode successfully execute the Claude integrators research task**

---

## The Problem (What Broke)
- OpenCode called `thunderbird_model_dispatcher.py` — too complex, too many failure points
- Dispatcher had syntax errors and unpredictable routing (Grok instead of Sonnet)
- File writes and email sends unreliable
- OpenCode had no clear way to know if task succeeded or failed

---

## The Solution (What Now Works)
**4 foolproof scripts in `/home/john/Thunderbird/OpsCenter/`:**

1. **`diagnose_research_system.py`** — Verify all prerequisites (run FIRST)
2. **`research_integrators_headless.py`** — Spawn headless Claude research (CORE)
3. **`send_research_email.py`** — Email results to Commander
4. **`run_research_task.sh`** — Orchestrate full workflow (use THIS)

**Plus full documentation:** `RESEARCH_TASK_README.md`

---

## For OpenCode: How to Integrate

### Step 1: Copy This Into OpenCode's Task Handler

```python
import subprocess
import time
import sys
from pathlib import Path

def task_research_claude_integrators():
    """
    OpenCode task: Research 3rd-party Claude integrators, agentic models, voice control.
    
    Returns immediately after spawning (task runs in background).
    Results saved to: /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_*.md
    Results emailed to: johnloucks3@gmail.com
    """
    
    script_dir = Path("/home/john/Thunderbird/OpsCenter")
    runner_script = script_dir / "run_research_task.sh"
    
    if not runner_script.exists():
        return {
            "status": "FATAL",
            "error": f"Runner script not found: {runner_script}",
            "instructions": "Copy research task scripts from /home/john/Thunderbird/OpsCenter/"
        }
    
    try:
        # Run the orchestrator (spawns research + sends email)
        result = subprocess.run(
            ["bash", str(runner_script)],
            capture_output=True,
            text=True,
            timeout=120,  # 2 min timeout for spawn + immediate returns
            cwd=str(script_dir)
        )
        
        if result.returncode == 0:
            return {
                "status": "SUCCESS",
                "message": "Research task spawned successfully",
                "output": result.stdout,
                "research_location": "/home/john/Thunderbird/OpsCenter/opencode_knowledge/",
                "email_destination": "johnloucks3@gmail.com"
            }
        else:
            # Check logs for debugging
            logs = list(Path("/home/john/Thunderbird/logs").glob("headless_claude_integrators_*.log"))
            latest_log = str(logs[-1]) if logs else "No logs found"
            
            return {
                "status": "PARTIAL_FAILURE",
                "message": "Research task spawn may have had issues",
                "output": result.stdout,
                "errors": result.stderr,
                "log_file": latest_log,
                "instructions": f"Check {latest_log} for details"
            }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "error": "Research task spawn timed out",
            "note": "Task may still be running in background; check logs"
        }
    
    except Exception as e:
        return {
            "status": "FATAL",
            "error": str(e),
            "instructions": "Check logs and run python3 diagnose_research_system.py"
        }
```

### Step 2: Call It From OpenCode's Main Task Router

```python
if "research integrators" in task_description.lower() or \
   "claude integrators" in task_description.lower() or \
   "agentic models" in task_description.lower():
    
    result = task_research_claude_integrators()
    return {
        "task_id": "RESEARCH_INTEGRATORS_001",
        "result": result
    }
```

### Step 3: OpenCode Executes (Example)

```bash
# OpenCode task trigger:
python3 /home/john/Thunderbird/OpsCenter/task_runner.py \
  "Research 3rd-party Claude integrators and agentic models for Thunderbird Wing"

# Output:
# {
#     "status": "SUCCESS",
#     "message": "Research task spawned successfully",
#     "research_location": "/home/john/Thunderbird/OpsCenter/opencode_knowledge/",
#     "email_destination": "johnloucks3@gmail.com"
# }
```

**That's it.** OpenCode gets immediate return. Research runs in background. Email sends when done.

---

## What Happens Inside (For Understanding)

```
OpenCode calls bash run_research_task.sh
                    ↓
        ╔═══════════════════════════════════╗
        ║ Step 1: Spawn headless Claude    ║
        ║ - Load OAuth token               ║
        ║ - Build prompt (WRITE [PATH])    ║
        ║ - subprocess.Popen() detached    ║
        ║ - Return immediately             ║
        ╚═══════════════════════════════════╝
                    ↓
        (Claude runs in background for 5-15 min)
                    ↓
        ╔═══════════════════════════════════╗
        ║ Step 2: Send email                ║
        ║ - Read research_integrators_RESULT_*.md
        ║ - gmail_send_from_wing() to Commander
        ║ - Email sent to johnloucks3@gmail.com
        ╚═══════════════════════════════════╝
                    ↓
                Returns
            (OpenCode continues)
```

---

## Testing Before OpenCode Uses It

### Test 1: Run Diagnostics
```bash
cd /home/john/Thunderbird/OpsCenter
python3 diagnose_research_system.py
# Should show: ✅ ALL CHECKS PASSED
```

### Test 2: Dry Run the Spawn
```bash
cd /home/john/Thunderbird/OpsCenter
python3 research_integrators_headless.py
# Should show: ✅ Spawned Claude (PID XXXXX)
```

### Test 3: Monitor the Research
```bash
# In another terminal:
tail -f /home/john/Thunderbird/logs/headless_claude_integrators_*.log

# In another terminal:
watch -n 5 "ls -lah /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_*.md"
```

### Test 4: Full Workflow
```bash
cd /home/john/Thunderbird/OpsCenter
bash run_research_task.sh
# Should complete with: ✅ RESEARCH TASK COMPLETE
```

### Test 5: Check Email
- Log into d2mconcierge@gmail.com
- Check Sent folder for email to johnloucks3@gmail.com
- Or check johnloucks3@gmail.com inbox for research email

---

## Error Handling for OpenCode

### If Research Won't Spawn
```bash
python3 diagnose_research_system.py
# Fix any "❌ FAIL" issues
# Most common: Token daemon inactive (enable with systemctl)
```

### If Output File Doesn't Appear
```bash
tail -50 /home/john/Thunderbird/logs/headless_claude_integrators_*.log
# Check if prompt includes "WRITE [PATH]" instruction (should be in logs)
# Wait longer — Claude may still be processing
```

### If Email Doesn't Send
```bash
# Check draft was created in d2mconcierge Gmail
# Run: python3 send_research_email.py /path/to/research_*.md
# manually
```

---

## Key Points for OpenCode

✅ **Do these**:
- Run diagnostics first (catches 95% of issues)
- Call `bash run_research_task.sh` (handles full workflow)
- Monitor logs for debugging
- Return immediately (don't wait for research completion)

❌ **Don't do these**:
- Don't call dispatcher.py directly (too complex, too many failure points)
- Don't remove WRITE [PATH] from prompt (output is lost)
- Don't wait for subprocess to finish
- Don't skip OAuth verification

---

## Files to Copy to OpenCode

If running on a different machine, copy these to the same directory:

```bash
cp /home/john/Thunderbird/OpsCenter/research_integrators_headless.py /path/to/opencode/
cp /home/john/Thunderbird/OpsCenter/send_research_email.py /path/to/opencode/
cp /home/john/Thunderbird/OpsCenter/run_research_task.sh /path/to/opencode/
cp /home/john/Thunderbird/OpsCenter/diagnose_research_system.py /path/to/opencode/
cp /home/john/Thunderbird/OpsCenter/RESEARCH_TASK_README.md /path/to/opencode/
```

All 5 files required for full integration.

---

## Success Criteria

Task is complete when:
1. ✅ `research_integrators_RESULT_*.md` appears in `opencode_knowledge/`
2. ✅ File contains 3 sections: Integrators, Agentic Models, Voice Control
3. ✅ Email sent to johnloucks3@gmail.com with research content
4. ✅ Email visible in d2mconcierge Sent folder

---

## Monitoring Dashboard Command

Run this to see full task status:

```bash
#!/bin/bash
echo "=== RESEARCH TASK STATUS ==="
echo ""
echo "[OUTPUT] Files in opencode_knowledge/"
ls -lah /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT_*.md 2>/dev/null || echo "No output files yet"
echo ""
echo "[LOGS] Latest research log tail"
tail -10 /home/john/Thunderbird/logs/headless_claude_integrators_*.log 2>/dev/null | tail -10 || echo "No logs yet"
echo ""
echo "[EMAIL] Check d2mconcierge Gmail Sent folder for johnloucks3@gmail.com emails"
```

Save as `monitor_research.sh` and run: `bash monitor_research.sh`

---

*This system is designed to work reliably. If it fails, diagnostics and logs will tell you exactly why.*
