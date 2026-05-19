# OpenCode → Claude Code Escalation Mechanism
**Technical Deep Dive | Version 1.0 | 2026-04-24**

---

## EXECUTIVE SUMMARY

**The Problem:** OpenCode (a subprocess running DeepSeek V3.1) needs to spawn long-running headless Claude tasks. If its native headless dispatch fails (token issues, daemon problems), the task is lost.

**The Solution:** A three-tier resilience architecture where OpenCode can escalate to Claude Code (the primary CLI) when its own mechanisms fail, ensuring mission continuity.

**The Guarantee:** Every headless Claude task either completes successfully OR the failure is logged and escalated to COS with full diagnostic information.

---

## ARCHITECTURAL CONTEXT

### How OpenCode Currently Operates

```
┌─────────────────────────────────────────────────────────────────┐
│ OpsCenter Daemon (agent_runner.py + task dispatcher)             │
│  - Monitors task queues (Telegram, API, cron)                   │
│  - Routes tasks to Hale (Claude), OpenCode (Gemini), or API        │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ↓
    ┌──────────────────────────────────────────┐
    │ Task: "Run intelligence sweep"            │
    │ Assigned: goose (OpenCode)               │
    └──────────────────────────────────────────┘
                           │
                           ↓
    ┌──────────────────────────────────────────┐
    │ OpenCode Subprocess (DeepSeek V3.1)      │
    │ - Reads task from dispatcher              │
    │ - Needs to spawn headless Claude          │
    │ - Calls Layer 2: dispatch_to_headless... │
    └──────────────────────────────────────────┘
                           │
                           ↓
          ┌────────────────────────────┐
          │ SUCCESS: Headless Claude    │
          │ running in background       │
          └────────────────────────────┘
                OR
          ┌────────────────────────────┐
          │ FAILURE: Token expired,     │
          │ supervisor down, creds      │
          │ missing, etc.               │
          └────────────────────────────┘
```

### The Problem: OpenCode Failure Modes

When Layer 1 (`spawn_headless_claude()`) fails, it returns:
```python
{
    "status": "FATAL_PREREQ",  # Token daemon, supervisor, or creds problem
    "error": "Token refresh daemon inactive",
    "can_retry": False,
    "log_file": "/path/to/log"
}
```

**At this point, what does OpenCode do?**

- **Old approach (no fallback):** OpenCode catches the error, raises RuntimeError, task dies. Failure is silent or logged only to OpenCode's stderr.
- **New approach (with fallback):** OpenCode escalates to Claude Code, which has independent OAuth, environment, and error handling.

---

## THE ESCALATION MECHANISM — Three-Tier Resilience

### Tier 1: OpenCode's Native Headless Dispatch

```python
from OpsCenter.headless_claude_fallback import dispatch_with_fallback

result = dispatch_with_fallback(
    task_description="Run ship intelligence sweep",
    output_file_path="/home/john/Thunderbird/output/ship_intel.txt",
    task_name="ship_intel_opencode"
)
```

**What happens inside `dispatch_with_fallback()`:**

#### Step 1: Try OpenCode's native dispatch
```python
result = dispatch_to_headless_claude(...)
if result["status"] == "SPAWNED":
    return result  # Success, return immediately
```

**Duration:** ~100-500ms (just subprocess.Popen() overhead)

**Success path:** Headless Claude spawned with full OAuth, token verification, log redirection. Task is running independently in background.

#### Step 2: Retry if `can_retry=True`
```python
if result.get("can_retry"):
    retries_attempted += 1
    if retries_attempted < max_retries:
        continue  # Loop back, try again
```

**Why:** Some failures are transient (token refresh daemon was slow, supervisor took a moment). Retry gives it a second chance.

**Duration:** 100-500ms per retry (capped at `max_retries`, default 1)

#### Step 3: If OpenCode still fails, escalate to Claude Code
```python
escalation_result = escalate_to_claude_code(
    task_description=task_description,
    output_file_path=output_file_path,
    task_name=task_name
)
```

**This is the critical escalation.** Let me explain what happens:

---

### Tier 2: Escalation to Claude Code

When OpenCode's headless dispatch fails persistently, it spawns Claude Code directly:

```python
def escalate_to_claude_code(...) -> dict:
    # Spawn Claude Code CLI directly
    proc = subprocess.Popen(
        [
            "/home/john/.local/bin/claude",    # Claude Code binary
            "-p", prompt,                      # The task prompt
            "--model", "claude-haiku-4-5..."
        ],
        stdout=log_file,                       # Capture to log
        stderr=subprocess.STDOUT,
        # ← NO start_new_session=True here!
        # Claude Code is the PRIMARY process
    )
    
    return {
        "status": "ESCALATED_TO_CLAUDE_CODE",
        "pid": proc.pid,
        "log_file": str(log_file),
        "output_file": output_file_path
    }
```

**Why NOT `start_new_session=True` on Claude Code escalation?**

This is crucial. Here's the reasoning:

1. **OpenCode is already a subprocess.** It was spawned by OpsCenter daemon/task runner
2. **OpenCode can exit after spawning Claude Code.** It doesn't need to monitor the process
3. **Claude Code IS the primary handler.** It manages its own session, OAuth, subprocess lifecycle
4. **If we use `start_new_session=True` for Claude Code:**
   - Process becomes a grandchild (OpenCode → Claude Code)
   - If OpsCenter daemon dies, both orphan
   - Adds unnecessary process hierarchy complexity

5. **Without `start_new_session=True`:**
   - Claude Code runs as a child of OpenCode
   - If OpenCode exits normally after spawning Claude Code, Claude continues running
   - System automatically reaps the process when it's done
   - Simple, clean hierarchy

**Key insight:** OpenCode's job is to DISPATCH the work to Claude Code. OpenCode can then exit. Claude Code handles the actual task execution with its own full OAuth stack.

---

### Tier 3: Error Return (Both Tiers Failed)

If Claude Code escalation also fails:

```python
return {
    "status": "FAILED",
    "error": "OpenCode dispatch failed (1 retry), Claude Code escalation also failed: [error details]",
    "log_file": str(escalation_log_file),
    "retries_attempted": 1,
    "escalated": True
}
```

**At this point:**
- Task is marked FAILED in audit log
- Full error trail is logged for COS review
- Supervisor detects the failure and alerts COS
- Commander can investigate the logs

---

## WHY THIS ARCHITECTURE WORKS

### Problem 1: Token Issues
**Symptom:** Token refresh daemon down or token expired  
**Tier 1 handling:** Verification check fails, `can_retry=False`, escalates immediately  
**Tier 2 handling:** Claude Code spawns its own process, reads fresh credentials, has independent OAuth stack  
**Result:** Even if system-wide token daemon is down, Claude Code can still auth using its own credential reading

### Problem 2: Supervisor Daemon Down
**Symptom:** Haiku supervisor not running  
**Tier 1 handling:** Verification fails, escalates  
**Tier 2 handling:** Claude Code doesn't depend on supervisor verification (it has its own error handling)  
**Result:** Task completes even if supervisor is temporarily down

### Problem 3: Credentials File Corrupted
**Symptom:** `~/.claude/.credentials.json` missing or invalid JSON  
**Tier 1 handling:** Verification fails with clear error, escalates  
**Tier 2 handling:** Claude Code re-reads same credentials file, but if it's truly missing, logs error with SAME clarity  
**Result:** Clear diagnostic trail for COS

### Problem 4: OpenCode Process Dies Mid-Spawn
**Symptom:** OpenCode crashes after spawning Claude Code  
**Tier 1:** N/A (already failed, escalating)  
**Tier 2:** Claude Code is now running. OpenCode's death doesn't affect it  
**Result:** Task continues uninterrupted

---

## PROCESS LIFECYCLE DIAGRAMS

### Success Path (Tier 1)

```
OpsCenter daemon
    ↓ (spawns)
OpenCode subprocess (DeepSeek V3.1)
    ↓ (calls dispatch_with_fallback)
    ├─ Tier 1: dispatch_to_headless_claude()
    │  ├─ Layer 1: spawn_headless_claude()
    │  │  ├─ Verify token daemon ✓
    │  │  ├─ Verify supervisor ✓
    │  │  ├─ Verify credentials ✓
    │  │  └─ Spawn headless Claude → PID 12345 ✓
    │  └─ RETURN: status=SPAWNED, pid=12345
    └─ RETURN to caller: status=SPAWNED
OpenCode continues/exits
    ↓
Headless Claude PID 12345 runs independently
    ↓
Writes output to /home/john/Thunderbird/output/...
    ↓
Task complete ✓
```

### Escalation Path (Tier 1 fails, Tier 2 succeeds)

```
OpsCenter daemon
    ↓
OpenCode subprocess
    ↓
dispatch_with_fallback()
    ├─ Tier 1: dispatch_to_headless_claude()
    │  └─ FAILS: "token_refresh daemon inactive"
    │     (can_retry=False)
    ├─ Retry: NO (can_retry=False, skip loop)
    └─ Tier 2: escalate_to_claude_code()
       ├─ Spawn Claude Code → PID 12346
       │  [/home/john/.local/bin/claude -p "..." --model haiku]
       └─ RETURN: status=ESCALATED_TO_CLAUDE_CODE, pid=12346
       
OpenCode returns result to dispatcher
OpenCode may exit normally
    ↓
Claude Code PID 12346 runs independently
    ├─ Reads ~/.claude/.credentials.json
    ├─ Authenticates with own OAuth
    ├─ Spawns subprocess (start_new_session=True)
    │  └─ Headless Claude PID 12347 (grandchild of OpenCode)
    └─ Manages task completion
        ↓
Claude Code receives output, exits cleanly
Headless Claude PID 12347 continues until done
    ↓
Output written to file
Task complete ✓
```

### Total Failure Path (Both Tiers fail)

```
OpenCode subprocess
    ↓
dispatch_with_fallback()
    ├─ Tier 1: FAILS
    ├─ Retry: FAILS again
    └─ Tier 2: escalate_to_claude_code()
       └─ FAILS: "Claude Code binary not found" or "subprocess.Popen() exception"
       
       RETURN: status=FAILED, error="[full error trail]"
       
OpenCode returns error result to dispatcher
    ↓
Dispatcher logs failure to audit trail
    ↓
Supervisor detects logged failure
    ↓
COS alerted with:
  - Task name
  - Failure reason
  - Log file path
  - Retries attempted
  - Whether escalation was attempted
```

---

## KEY DESIGN DECISIONS

### Decision 1: Why NOT Use Mission Board for Escalation?

**Alternative approach:** When OpenCode fails, write to mission board queue, wait for Claude Code to pick it up

**Why we didn't:**
- Adds queue latency (10-30 seconds vs. immediate spawn)
- Adds complexity (queue entries, polling, race conditions)
- Makes it harder to track original failure context
- Loses the immediate PID linking

**Why we do it:** Direct subprocess spawn → immediate execution, clear causality chain.

---

### Decision 2: Why NOT Retry via Message to Commander?

**Alternative:** When OpenCode fails, send Telegram to Commander asking them to approve retry via Claude Code

**Why we didn't:**
- Blocks on human response (30 minutes to hours vs. milliseconds)
- Loses mission continuity for automated tasks
- Wastes Commander's attention on recoverable failures
- Command pattern for escalation should be automatic

**Why we do it:** Automatic escalation preserves continuity, Commander is only alerted if BOTH tiers fail.

---

### Decision 3: Why No `start_new_session=True` for Claude Code?

(Addressed above, but critical decision)

Alternative: Use `start_new_session=True` to isolate Claude Code

Why we didn't:
- Creates unnecessary process isolation when OpenCode is temporary
- Claude Code is the PRIMARY handler, not a background worker
- Simpler to let Claude Code live as OpenCode's child, exit normally when done
- One less subprocess config to manage

Why we do it: Clean process hierarchy (OpenCode → Claude Code), simple lifecycle management.

---

## MONITORING & OBSERVABILITY

### Logging

Every escalation is logged:

```
# In /home/john/Thunderbird/logs/claude_opencode_escalation_*.log

[2026-04-24 14:32:15] Tier 1 dispatch FAILED: "token_refresh_daemon inactive"
[2026-04-24 14:32:15] Retrying (1/1 max_retries)...
[2026-04-24 14:32:15] Tier 1 retry still FAILED: "token_refresh_daemon inactive"
[2026-04-24 14:32:15] Escalating to Claude Code...
[2026-04-24 14:32:15] ✅ Spawned Claude Code (PID 12346) as escalation
```

### Supervisor Detection

Haiku Supervisor monitors all spawns (OpenCode tier 1 AND Claude Code tier 2):

```bash
tail -50 /home/john/Thunderbird/logs/haiku_supervisor.log | grep "escalat"
# Output: Shows which tasks escalated, when, and outcome
```

### Result Metadata

Result dict includes escalation flag:

```python
result = dispatch_with_fallback(...)
print(result)
# {
#     "status": "SPAWNED" | "ESCALATED_TO_CLAUDE_CODE" | "FAILED",
#     "escalated": True/False,
#     "retries_attempted": 1,
#     "pid": 12346,
#     "log_file": "/path/to/log"
# }
```

Caller can log this metadata back to task tracking system for full audit trail.

---

## ERROR SCENARIOS & RECOVERY

| Scenario | Tier 1 Result | Escalation Attempt | Outcome | Recovery |
|---|---|---|---|---|
| Token daemon down | FATAL_PREREQ | ✅ Yes | Success (Claude Code reads creds) | Automatic |
| Credentials file missing | FATAL_CREDS | ✅ Yes | Fail (Claude Code also fails) | Manual: re-auth in Claude Desktop |
| Claude binary not found | FATAL_BIN (Tier 1), ESCALATION_FAILED (Tier 2) | ✅ Yes | Fail (both) | Manual: reinstall Claude Code CLI |
| Supervisor daemon down | FATAL_PREREQ | ✅ Yes | Success (Claude Code ignores supervisor) | Automatic |
| OpenCode runs out of memory | SPAWN_FAILED | ✅ Yes (if process still alive) | Depends on Claude Code | Manual: restart OpsCenter |
| Both daemons and CLI offline | Both fail | ✅ Yes | FAILED status logged | Manual: contact systems team |

---

## IMPLEMENTATION CHECKLIST FOR OPENCODE

OpenCode should use the high-level API:

```python
# ✓ Import the fallback module
from OpsCenter.headless_claude_fallback import dispatch_with_fallback

# ✓ Call the high-level function (not dispatch_to_headless_claude directly)
result = dispatch_with_fallback(
    task_description="Your task",
    output_file_path="/home/john/Thunderbird/output/...",
    task_name="descriptive_name",
    max_retries=1  # Default: try once, then escalate
)

# ✓ Check the result
if result["status"] in ["SPAWNED", "ESCALATED_TO_CLAUDE_CODE"]:
    # Task is running, log metadata
    logging.info(f"Task dispatched (escalated={result['escalated']}, PID={result['pid']})")
else:
    # Task failed, log error and alert COS
    logging.error(f"Task dispatch FAILED: {result['error']}")
    # Send to COS: "Headless Claude dispatch failed after escalation. Check logs: {result['log_file']}"
```

**That's it.** The escalation logic is entirely automatic.

---

## CONCLUSION

The escalation mechanism guarantees:

✅ **Resilience:** 3-tier retry logic (native dispatch → retry → Claude Code escalation)  
✅ **Transparency:** Every attempt is logged; escalations are visible  
✅ **Continuity:** Tasks don't die; they escalate and complete  
✅ **Simplicity:** OpenCode calls one function; escalation is automatic  
✅ **Debuggability:** Full error trail with log files and metadata  

**Result:** OpenCode can reliably spawn long-running headless Claude tasks, with automatic fallback to Claude Code when its own mechanisms fail.

---

*Updated 2026-04-24 | Hale, COS | Deep technical review by Sonnet*
