# MCP Headless Claude Integration
**Version 1.0 | 2026-04-26 | Production-Ready**

---

## Overview

Two MCP tools now enable long-running Claude tasks via the Thunderbird MCP server:

1. **`headless_claude_task`** — High-level interface for executing tasks with automatic prompt building, prerequisite verification, and retry logic
2. **`headless_claude_spawn`** — Low-level interface for advanced use cases requiring custom prompts and full parameter control

Both tools spawn Claude as a detached background process that continues running even if the calling agent exits. Output is written to disk, not returned to the caller.

**File Paths:**
- Module: `/home/john/Thunderbird/core/mcp/thunderbird_headless_claude.py`
- Integration: `/home/john/Thunderbird/core/mcp/travel_mcp_server.py` (imported and registered)
- Examples: `/home/john/Thunderbird/examples/headless_claude_mcp_example.py`

---

## Tool 1: headless_claude_task (High-Level)

### Purpose

Simple, high-level task execution. Best for general use cases.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `task_description` | string | ✓ | — | What Claude should do. Full task description, not code. Max 2000 chars recommended. |
| `output_path` | string | ✓ | — | Full path where Claude writes output (e.g., `/home/john/Thunderbird/output/analysis.txt`) |
| `task_name` | string | ✓ | — | Short identifier for logging (e.g., `market_analysis`, `competitor_research`). Alphanumeric + underscore. |
| `model` | string | ✗ | `claude-opus-4-7` | Claude model: `claude-opus-4-7`, `claude-sonnet-4-6`, or `claude-haiku-4-5-20251001` |
| `max_retries` | integer | ✗ | `1` | Retry attempts if spawn fails (0 = no retries, 1 = try once, retry once) |

### Response

Returns JSON string with fields:

```json
{
  "status": "SPAWNED" | "ESCALATED_TO_CLAUDE_CODE" | "FAILED",
  "pid": 12345,
  "output_file": "/home/john/Thunderbird/output/analysis.txt",
  "log_file": "/home/john/Thunderbird/logs/headless_task_20260426_143022.log",
  "task_name": "market_analysis",
  "model": "claude-opus-4-7",
  "timestamp": "2026-04-26T14:30:22.123456",
  "attempt": 1,
  "error": "null or error string if failed"
}
```

### Status Meanings

- **`SPAWNED`** — Process running successfully in background. Monitor output file for results.
- **`ESCALATED_TO_CLAUDE_CODE`** — OpenCode dispatch failed, escalated to Claude Code (fallback). Task still running.
- **`FAILED`** — Spawn failed after all retries exhausted. Check `error` field and log file.

### How It Works

The tool automatically:
1. Builds a complete prompt from your task description
2. Includes explicit `WRITE [output_path]` instruction (prevents silent output loss)
3. Verifies prerequisites (token daemon, supervisor, credentials)
4. Spawns Claude as detached process
5. Retries on failure (up to `max_retries` times)
6. Returns structured result

### Example Usage

```python
# Via MCP client (e.g., OpenCode, Claude Code)
result = await mcp_client.call_tool(
    "headless_claude_task",
    {
        "task_description": "Analyze Q2 2026 luxury cruise pricing trends by destination and cruise line.",
        "output_path": "/home/john/Thunderbird/output/q2_cruise_analysis.txt",
        "task_name": "q2_cruise_analysis",
        "model": "claude-opus-4-7",
        "max_retries": 1
    }
)

if result["status"] == "SPAWNED":
    print(f"Task running (PID {result['pid']})")
    print(f"Output: {result['output_file']}")
    # Monitor the file or continue with other work
else:
    print(f"Failed: {result['error']}")
```

---

## Tool 2: headless_claude_spawn (Low-Level)

### Purpose

Advanced control for custom prompts and non-standard use cases.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `prompt` | string | ✓ | — | Complete prompt for Claude. **MUST include `WRITE [PATH]` instruction or output is lost.** |
| `output_file` | string | ✓ | — | Full path where Claude writes output (same path as in WRITE instruction in prompt) |
| `model` | string | ✗ | `claude-opus-4-7` | Claude model selection |
| `task_name` | string | ✗ | `headless_task` | Identifier for logging |
| `log_file` | string | ✗ | `null` | Path for process logs. If null, auto-generates in `/home/john/Thunderbird/logs/` |

### Response

Returns JSON string:

```json
{
  "status": "SPAWNED" | "FAILED",
  "pid": 12346,
  "output_file": "/home/john/Thunderbird/output/custom_output.txt",
  "log_file": "/home/john/Thunderbird/logs/headless_custom_task_20260426_143022.log",
  "task_name": "custom_analysis",
  "model": "claude-sonnet-4-6",
  "timestamp": "2026-04-26T14:30:22.654321",
  "error": "null or error string if failed"
}
```

### Critical: WRITE Instruction

Your prompt **MUST** include an explicit `WRITE [PATH]` instruction:

```python
# CORRECT ✓
prompt = f"""
Analyze the data and identify trends.
WRITE your complete analysis to {output_file}
"""

# WRONG ✗ — output will be lost
prompt = "Analyze the data and identify trends."
```

The path in `WRITE [PATH]` must match the `output_file` parameter.

### Example Usage

```python
# Custom JSON output format
output_file = "/home/john/Thunderbird/output/pricing.json"

prompt = f"""
Analyze Q2 2026 pricing for 7-day Mediterranean cruises.

OUTPUT FORMAT:
Provide valid JSON with this structure:
{{
  "voyages": [
    {{"name": "...", "price": 5000, "discount": "10%"}}
  ],
  "trends": ["...", "..."],
  "sources": ["URL1", "URL2"]
}}

WRITE your JSON output to {output_file}
Do NOT output to stdout.
"""

result = await mcp_client.call_tool(
    "headless_claude_spawn",
    {
        "prompt": prompt,
        "output_file": output_file,
        "model": "claude-opus-4-7",
        "task_name": "pricing_json_analysis"
    }
)

if result["status"] == "SPAWNED":
    # Monitor the file for JSON results
    import json
    while not Path(output_file).exists():
        await asyncio.sleep(2)
    with open(output_file) as f:
        pricing_data = json.load(f)
```

---

## Return Values & Status Codes

### Status: SPAWNED

✅ Process is running in background.

**What to do:**
1. Monitor output file for completion: `while not Path(output_file).exists(): sleep()`
2. Check logs: `tail -f {log_file}`
3. When file appears, read the results
4. Clean up log file if desired

### Status: ESCALATED_TO_CLAUDE_CODE (Task 1 only)

⚠️ OpenCode's dispatch failed, but task was escalated to Claude Code as fallback.

**What to do:**
- Same as SPAWNED — task is still running, output will be written
- Check both log file and output file to verify completion
- Fallback is transparent to the caller

### Status: FAILED

❌ Spawn failed after all retries.

**What to do:**
1. Check `error` field for error message
2. Check log file: `cat {log_file}` (last 50 lines)
3. Verify prerequisites:
   ```bash
   systemctl --user status claude-token-monitor.timer --no-pager
   systemctl --user status claude-oauth-keepalive.timer --no-pager
   systemctl --user status thunderbird-watchdog.timer --no-pager
   ls -la ~/.claude/.credentials.json
   ```
4. If credentials missing, have Commander re-authenticate in Claude Desktop
5. Alert COS with full error trace

---

## OpenCode Integration Pattern

### Step 1: Import and Call

```python
# In your OpenCode agent code
from mcp_client import MCPClient

async def run_background_analysis():
    mcp = MCPClient("mcp.d2mluxury.quest:8765")

    result = await mcp.call_tool(
        "headless_claude_task",
        {
            "task_description": "Your task here",
            "output_path": "/home/john/Thunderbird/output/result.txt",
            "task_name": "analysis_task"
        }
    )
    return result
```

### Step 2: Handle Result

```python
if result["status"] == "SPAWNED":
    # Task is running — log and continue
    logging.info(f"Task spawned: PID {result['pid']}")
    logging.info(f"Output: {result['output_file']}")

elif result["status"] in ["ESCALATED_TO_CLAUDE_CODE"]:
    # Fallback triggered — still running
    logging.info(f"Task escalated to Claude Code, continuing...")

else:  # FAILED
    # Handle error
    logging.error(f"Spawn failed: {result['error']}")
    raise Exception(f"Failed to spawn task: {result['error']}")
```

### Step 3: Monitor Output (Optional)

```python
# If you need to wait for results
import asyncio
from pathlib import Path

output_file = result["output_file"]
max_wait = 600  # seconds

# Poll for output
elapsed = 0
while not Path(output_file).exists() and elapsed < max_wait:
    await asyncio.sleep(10)
    elapsed += 10

if Path(output_file).exists():
    with open(output_file) as f:
        output = f.read()
    return output
else:
    raise TimeoutError(f"Task did not complete within {max_wait}s")
```

---

## Common Patterns

### Pattern 1: Fire-and-Forget

Spawn a task and don't wait for results:

```python
result = await mcp_client.call_tool("headless_claude_task", {...})
# Log PID for monitoring, then return immediately
logging.info(f"Task spawned: {result['pid']}")
# Caller continues; results appear in output file when ready
```

### Pattern 2: Monitor with Polling

Spawn a task and poll for completion:

```python
result = await mcp_client.call_tool("headless_claude_task", {...})
if result["status"] == "SPAWNED":
    output_file = result["output_file"]
    while not Path(output_file).exists():
        await asyncio.sleep(5)
    with open(output_file) as f:
        return f.read()
```

### Pattern 3: Structured Output

Request JSON or other structured format:

```python
prompt = f"""
Analyze data and return JSON.
WRITE to {output_file}
"""
result = await mcp_client.call_tool("headless_claude_spawn", {...})
# When output appears:
import json
data = json.load(open(output_file))
```

### Pattern 4: Custom Model Selection

Use Haiku for fast, cheap tasks:

```python
result = await mcp_client.call_tool(
    "headless_claude_task",
    {
        "task_description": "Generate 10 email subject lines",
        "output_path": "/home/john/Thunderbird/output/subjects.txt",
        "task_name": "email_subjects",
        "model": "claude-haiku-4-5-20251001"  # Cheap and fast
    }
)
```

---

## Prerequisites & Verification

Before spawning headless Claude, verify:

### 1. Token Refresh Timer

```bash
systemctl --user status claude-token-monitor.timer --no-pager
# Expected: Active: active (waiting)
```

If inactive:
```bash
systemctl --user enable --now claude-token-monitor.timer
```

### 2. OAuth Keepalive Timer

```bash
systemctl --user status claude-oauth-keepalive.timer --no-pager
# Expected: Active: active (waiting)
```

If inactive:
```bash
systemctl --user enable --now claude-oauth-keepalive.timer
```

### 3. Watchdog Timer

```bash
systemctl --user status thunderbird-watchdog.timer --no-pager
# Expected: Active: active (waiting)
```

If inactive:
```bash
systemctl --user enable --now thunderbird-watchdog.timer
```

### 4. OAuth Credentials

```bash
ls -la ~/.claude/.credentials.json
# Expected: File exists, contains claudeAiOauth with accessToken
```

If missing: Have Commander re-authenticate in Claude Desktop.

---

## Error Handling

### Error: Token Expired

**Symptom:** Log shows `401 Unauthorized`

**Fix:**
```bash
systemctl --user restart claude-token-monitor.timer
# Wait 30 seconds, then retry
```

### Error: Supervisor Not Running

**Symptom:** Log shows `supervisor daemon inactive`

**Fix:**
```bash
systemctl --user enable --now thunderbird-watchdog.timer
```

### Error: Credentials Missing

**Symptom:** Log shows `credentials.json not found`

**Fix:**
1. Have Commander authenticate in Claude Desktop app
2. Credentials file will be created: `~/.claude/.credentials.json`
3. Retry task

### Error: Claude Binary Not Found

**Symptom:** Log shows `[Errno 2] No such file or directory: /home/john/.local/bin/claude`

**Fix:**
```bash
# Verify Claude Code is installed
which claude
# If not found, reinstall Claude Code CLI
```

### General Troubleshooting

1. **Check log file:**
   ```bash
   tail -50 {log_file}
   ```

2. **Monitor process:**
   ```bash
   ps aux | grep claude
   ```

3. **Verify output file creation:**
   ```bash
   ls -la {output_file}
   ```

4. **Alert COS:**
   ```
   Message: "Headless Claude spawn failed for task [NAME]
   Check log: [PATH]
   Prerequisites: [status of timers]"
   ```

---

## Performance & Limits

| Factor | Value | Notes |
|--------|-------|-------|
| Max concurrent tasks | Unlimited | System limits apply (memory, processes) |
| Spawn latency | ~500ms | Time from call to process running |
| Process overhead | ~30MB | Per spawned Claude process |
| Log file size | ~10-50MB | Per long task; clean up after completion |
| Output file size | Unlimited | Depends on task output |
| Model selection | 3 models | Opus (expensive), Sonnet (balanced), Haiku (cheap) |

---

## Examples

See `/home/john/Thunderbird/examples/headless_claude_mcp_example.py` for:
1. Market analysis (high-level)
2. Competitor research (high-level)
3. Custom JSON output (low-level)
4. Error handling patterns
5. OpenCode integration

---

## Monitoring & Logs

### View Recent Spawns

```bash
tail -50 /home/john/Thunderbird/logs/headless_*.log
```

### Monitor Running Tasks

```bash
ps aux | grep headless
# or
watch -n 2 "ps aux | grep claude"
```

### Supervisor Logs

```bash
tail -50 /home/john/Thunderbird/logs/haiku_supervisor.log | grep "Spawning\|FAILED"
```

---

## Architecture Overview

```
MCP Client (OpenCode, Claude Code, etc.)
    ↓ call_tool("headless_claude_task", {...})
    ↓
MCP Server (travel_mcp_server.py)
    ↓ register_headless_claude_tools(mcp)
    ↓
thunderbird_headless_claude.py
    ├─ headless_claude_task() → builds prompt
    └─ headless_claude_spawn() → direct spawn
        ↓
    spawn_headless_claude() [Layer 1 wrapper]
        ├─ Verify token daemon ✓
        ├─ Verify supervisor ✓
        ├─ Verify credentials ✓
        ├─ Inject OAuth token
        └─ subprocess.Popen(start_new_session=True) → detached process
            ↓
        Claude process running independently
        Writes to /home/john/Thunderbird/output/[file]
        Logs to /home/john/Thunderbird/logs/[log]
```

---

## Integration Checklist

- [ ] MCP tools registered: `register_headless_claude_tools(mcp)` called in `travel_mcp_server.py`
- [ ] Import added: `from thunderbird_headless_claude import register_headless_claude_tools`
- [ ] Logs directory exists: `/home/john/Thunderbird/logs/`
- [ ] Output directory exists: `/home/john/Thunderbird/output/`
- [ ] Timers running: token-monitor, oauth-keepalive, watchdog
- [ ] Credentials file exists: `~/.claude/.credentials.json`
- [ ] Claude binary available: `/home/john/.local/bin/claude`

---

## References

- **Module:** `core/mcp/thunderbird_headless_claude.py` (production implementation)
- **Server:** `core/mcp/travel_mcp_server.py` (registration point)
- **Examples:** `examples/headless_claude_mcp_example.py` (usage patterns)
- **Spawn Guide:** `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` (foolproof reference)
- **Architecture:** `docs/AGENTS_HEADLESS_DISPATCH_ARCHITECTURE.md` (deep dive)

---

*MCP Headless Claude Integration | Version 1.0 | 2026-04-26*
