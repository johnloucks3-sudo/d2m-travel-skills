# OPENCODE COPY-PASTE — HEADLESS CLAUDE IN 30 SECONDS

**Status:** ✅ VERIFIED 2026-04-26

---

## ONE TIME: Import This

```python
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude
```

---

## EVERY TIME: Use This Pattern

```python
# What you want Claude to do
task = "Analyze all luxury cruise lines and identify 5 market trends"

# Where to put the output
output_file = "/home/john/Thunderbird/output/my_analysis.txt"

# Spawn Claude in background
result = dispatch_to_headless_claude(
    task_description=task,
    output_file_path=output_file,
    task_name="cruise_market_trends"  # descriptive name for logs
)

# Check if it worked
if result["status"] == "SPAWNED":
    print(f"✅ Running as PID {result['pid']}")
    print(f"Output: {result['output_file']}")
else:
    print(f"❌ Failed: {result.get('error')}")
    print(f"Logs: {result.get('log_file')}")
```

---

## WHAT YOU GET BACK

| Field | Meaning |
|-------|---------|
| `status: "SPAWNED"` | ✅ Claude is running. You're done. Go. |
| `pid` | Process ID (for monitoring if needed) |
| `output_file` | Path where Claude will write output |
| `log_file` | Debug logs if something goes wrong |

---

## FULL REAL EXAMPLE

```python
#!/usr/bin/env python3
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

# Example: Generate a competitive analysis
result = dispatch_to_headless_claude(
    task_description="""
    Analyze the top 5 competitors in luxury cruise industry:
    - Silversea
    - Regent Seven Seas  
    - Seabourn
    - Oceania
    - Viking
    
    For each, identify:
    1. Their brand positioning
    2. Price point strategy
    3. Key differentiator vs others
    
    Write 800 words.
    """,
    output_file_path="/home/john/Thunderbird/output/cruise_competitive_analysis.txt",
    task_name="competitive_analysis_q2_2026"
)

# Done. Claude is running.
print(result)
```

---

## IF IT FAILS

1. Check the log file (path is in result)
2. Read the error message  
3. Tell COS: "Headless dispatch failed: [error]. Logs at [path]"

That's it.

---

## WHAT THE WRAPPER DOES FOR YOU

You don't need to understand this. But here it is:

✅ Checks token daemon  
✅ Checks credentials file  
✅ Loads OAuth token  
✅ Strips API key (forces OAuth)  
✅ Spawns Claude with correct auth  
✅ Writes prompt to stdin  
✅ Captures output to file  
✅ Returns immediately (Claude runs in background)  

All automatic. You just call one function.

---

## NEVER DO THIS

```python
# ❌ Wrong — Don't use subprocess
import subprocess
proc = subprocess.Popen(["claude", "-p", ...])
```

```python
# ❌ Wrong — Don't try to read output immediately
result = dispatch_to_headless_claude(...)
with open(result["output_file"]) as f:  # Crashes, not ready yet
    data = f.read()
```

```python
# ❌ Wrong — Don't use -p flag
proc = subprocess.Popen(["/home/john/.local/bin/claude", "-p", ...])
```

---

## THAT'S IT

```python
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

result = dispatch_to_headless_claude(
    task_description="your task here",
    output_file_path="/home/john/Thunderbird/output/output.txt",
    task_name="task_name"
)

print(result)
```

Done. Claude is running. Move on.
