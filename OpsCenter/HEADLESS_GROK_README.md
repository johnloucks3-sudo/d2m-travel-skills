# OpenCode Headless Grok Build Spawn Module

**Location:** `OpsCenter/opencode_headless_grok_spawn.py`  
**Status:** Production-ready ✅  
**Tests:** 3/3 passing (async, blocking, custom config)

---

## Overview

Reusable Python module for spawning OpenCode Grok Build as a detached headless process. Supports both **async** (fire-and-forget) and **blocking** (wait for answer) modes.

**Use cases:**
- Hale's ZEN counter-voice dispatch (background analysis during meetings)
- Standalone decision support (blocking mode with timeout)
- Advanced reasoning on strategic questions
- Integration with decision journals and institutional memory

---

## Quick Start

### 1. Simple Async (Fire-and-Forget)

```python
from OpsCenter.opencode_headless_grok_spawn import spawn_grok

result = spawn_grok("What is semantic context pruning?")
print(f"Running as PID {result.pid}")
print(f"Check {result.log_path} for output in ~10s")
```

**Output:**
```
✓ PID 2554665 | Log: /tmp/opencode_grok_1780262009463.log | Model: xai/grok-build-0.1
```

### 2. Blocking (Wait for Answer)

```python
result = spawn_grok(
    "Name three token optimization methods",
    blocking=True,
    timeout=30
)
print(result.output)
```

**Output:**
```
1. Semantic caching
2. Prompt compression
3. Context pruning / selective RAG
```

### 3. Custom Model

```python
from OpsCenter.opencode_headless_grok_spawn import spawn_grok_custom, GrokSpawnConfig

config = GrokSpawnConfig(
    model="xai/grok-4.20-0309-reasoning",  # Advanced reasoning
    blocking=True,
    timeout=60
)
result = spawn_grok_custom(config, "Your strategic question")
print(result.output)
```

---

## API Reference

### `spawn_grok(question, model, blocking, timeout, verbose)`

Simple convenience function for most use cases.

**Parameters:**
- `question` (str): Prompt/question for Grok
- `model` (str, default="xai/grok-build-0.1"): Model identifier
- `blocking` (bool, default=False): Wait for completion (vs async)
- `timeout` (int, default=None): Timeout in seconds (blocking mode only)
- `verbose` (bool, default=False): Print debug output

**Returns:** `GrokSpawnResult`

**Example:**
```python
result = spawn_grok(
    "Analyze the trade-offs between Sonnet and Opus for synthesis tasks",
    blocking=True,
    timeout=30,
    verbose=True
)
```

### `spawn_grok_custom(config, question)`

Advanced function for custom configuration.

**Parameters:**
- `config` (GrokSpawnConfig): Full configuration object
- `question` (str): Prompt/question

**Returns:** `GrokSpawnResult`

**Example:**
```python
config = GrokSpawnConfig(
    model="xai/grok-4.20-0309-reasoning",
    mode=SpawnMode.BLOCKING,
    timeout=60,
    verbose=True
)
result = spawn_grok_custom(config, "Your question")
```

### `GrokSpawnConfig` (Dataclass)

Configuration for spawn behavior.

**Fields:**
- `model` (str): Model identifier (default: "xai/grok-build-0.1")
- `fallback_model` (str): Fallback model (default: "deepseek/deepseek-chat")
- `mode` (SpawnMode): ASYNC or BLOCKING (default: ASYNC)
- `timeout` (int): Timeout seconds for blocking mode (default: 120)
- `log_dir` (Path): Directory for log files (default: /tmp)
- `log_prefix` (str): Log file prefix (default: "opencode_grok")
- `capture_output` (bool): Capture stdout/stderr (default: True)
- `verbose` (bool): Print debug output (default: False)

### `GrokSpawnResult` (Dataclass)

Result of spawn operation.

**Fields:**
- `success` (bool): Did the spawn succeed?
- `pid` (int): Process ID (async mode)
- `log_path` (Path): Path to log file
- `output` (str): Captured output (blocking mode)
- `exit_code` (int): Process exit code (blocking mode)
- `error` (str): Error message (if failed)
- `model_used` (str): Model that was used
- `duration_sec` (float): Elapsed time

**Example:**
```python
print(result)  # Readable string representation
# Output: ✓ PID 2554665 | Log: /tmp/opencode_grok_1780262009463.log | Model: xai/grok-build-0.1
```

---

## Authentication

The module automatically handles XAI_API_KEY:

1. **Environment variable** (checked first)
   ```bash
   export XAI_API_KEY="xai-..."
   ```

2. **From .env file** (fallback)
   ```bash
   # ~/.env or ~/Thunderbird/.env
   XAI_API_KEY="xai-..."
   ```

If neither is found, the module raises `EnvironmentError`.

---

## Modes Explained

### Async Mode (Default)

Returns immediately after spawning the process.

**Use when:**
- Running in the background while work continues
- Don't need the answer right now
- Analyzing while human team discusses

**Workflow:**
1. `spawn_grok(question)` → returns PID + log path
2. Process runs independently in detached session
3. Output written to log file
4. Read log later with `log_path.read_text()`

**Advantages:** Non-blocking, parallel work  
**Disadvantages:** Need to check log file manually

### Blocking Mode

Waits for process to complete, then returns output.

**Use when:**
- Need the answer before proceeding
- Making a decision that requires Grok's input
- Building decision support workflows

**Workflow:**
1. `spawn_grok(question, blocking=True, timeout=30)` → blocks
2. Process runs to completion
3. Output returned directly in result.output
4. Exit code checked (success = 0)

**Advantages:** Simple, output immediately available  
**Disadvantages:** Blocks the calling process

---

## Examples & Patterns

### Pattern 1: Hale ZEN Counter-Voice (Async)

```python
# Staff is discussing a model selection decision
result = spawn_grok(
    "Should we use Opus or Sonnet for synthesis? Analyze cost/quality trade-offs.",
    blocking=False  # Async
)

print(f"ZEN analysis spawned: PID {result.pid}")
print(f"Check {result.log_path} in 10s for Grok perspective")

# Continue meeting while Grok analyzes in background
# Check log later and surface findings to Chief
```

### Pattern 2: Decision Support (Blocking)

```python
# Chief needs a perspective before deciding
result = spawn_grok(
    "Is the single-hop email pipeline architecture sound? Risks?",
    blocking=True,
    timeout=30
)

if result.success:
    print("ZEN Perspective:")
    print(result.output)
    # Chief reviews and decides
```

### Pattern 3: Institutional Memory (Decision Journal)

```python
# Log the ZEN perspective with the decision
decision_log = f"""
## Decision: Model Selection

**ZEN Counter-Voice:**
{result.output}

**Hale Assessment:** ...
**Status:** LOGGED
"""

# Append to hale_decisions.md for future reference
```

### Pattern 4: Advanced Reasoning

```python
config = GrokSpawnConfig(
    model="xai/grok-4.20-0309-reasoning",  # Newest reasoning model
    mode=SpawnMode.BLOCKING,
    timeout=60,
    verbose=True
)

result = spawn_grok_custom(config, "Complex strategic question")
```

---

## Available Models

Check with OpenCode:

```bash
opencode models xai      # All xAI Grok variants
opencode models openrouter   # OpenRouter models
```

**Recommended:**
- `xai/grok-build-0.1` — General reasoning (default, recommended)
- `xai/grok-4.3` — Stable older version
- `xai/grok-4.20-0309-reasoning` — Advanced reasoning (if available)

---

## Command-Line Testing

```bash
# Async spawn
python3 OpsCenter/opencode_headless_grok_spawn.py -v "Your question"

# Blocking spawn with timeout
python3 OpsCenter/opencode_headless_grok_spawn.py --blocking --timeout 30 "Your question"

# Custom model
python3 OpsCenter/opencode_headless_grok_spawn.py --model xai/grok-4.3 "Question"
```

---

## Troubleshooting

### "XAI_API_KEY not found"

**Solution:** Set environment variable
```bash
export XAI_API_KEY="xai-your-key"
```

Or add to `~/.env`:
```bash
XAI_API_KEY="xai-your-key"
```

### "OpenCode binary not found"

**Solution:** Install OpenCode
```bash
# OpenCode should be at ~/.opencode/bin/opencode
# If missing, follow OpenCode installation guide
```

### Timeout in blocking mode

**Solution:** Increase timeout or switch to async
```python
# Increase timeout
result = spawn_grok(question, blocking=True, timeout=60)

# Or use async
result = spawn_grok(question, blocking=False)
```

### Output is empty

For async mode, give the process time:
```bash
sleep 5 && cat /tmp/opencode_grok_*.log
```

For blocking mode, check result.exit_code (should be 0 for success).

---

## Integration with Hale Workflows

The module is designed for seamless Hale integration:

1. **ZEN Auto-Dispatch:** Keyword router detects "counter"/"challenge" → calls this module
2. **Decision Journal:** Results logged to hale_decisions.md for institutional memory
3. **No Blocking:** Async mode runs in background while Hale continues operations
4. **Clean API:** Simple function calls or advanced config objects

---

## Performance

**Spawn overhead:** ~200ms  
**Process startup:** ~500ms  
**Grok response:** 5-30s typical (depends on question complexity)  
**Total async time:** ~1s (return to caller)  
**Total blocking time:** Spawn + Process + Response (~6-30s)

---

## Version

- **Module:** opencode_headless_grok_spawn.py v1.0
- **Status:** Production
- **Tests:** 3/3 passing
- **Last Updated:** 2026-05-31
- **Commit:** `6efa821f` (xAI integration)

---

## Related Files

- `OpsCenter/opencode_zen_counter.py` — ZEN counter-voice CLI (uses this module)
- `OpsCenter/keyword_router.py` — Routes "counter"/"challenge" keywords to ZEN
- `OpsCenter/examples_headless_grok_integration.py` — 4 integration patterns
- `CLAUDE.md` § "Model Routing" — Grok documentation

---

**Questions?** See examples_headless_grok_integration.py for 4 real-world patterns.
