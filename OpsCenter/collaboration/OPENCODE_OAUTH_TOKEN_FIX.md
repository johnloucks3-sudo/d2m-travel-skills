# OpenCode OAuth Token Injection Fix
**Status:** DEPLOYED 2026-04-08  
**File:** `/home/john/Thunderbird/OpsCenter/thunderbird_tasking_watcher.py`  
**Function:** `spawn_opencode_headless()`

---

## Problem
OpenCode (DeepSeek V3.1 headless) spawned by the tasking watcher was unable to dispatch to `claude -p` headless because the `CLAUDE_CODE_OAUTH_TOKEN` was not in its subprocess environment.

**Symptom:** OpenCode tasks that required Claude headless dispatch would fail silently or hang.

---

## Solution
Before calling `subprocess.Popen()`, inject the cached OAuth token into the environment.

### Code Pattern
```python
env = os.environ.copy()
env["PATH"] = "/home/john/.opencode/bin:" + env.get("PATH", "")

# Load fresh OAuth token from cache file
_oauth_cache = "/home/john/Thunderbird/OpsCenter/.claude_oauth_cache"
try:
    with open(_oauth_cache) as _f:
        for _line in _f:
            if _line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
                env["CLAUDE_CODE_OAUTH_TOKEN"] = _line.strip().split("=", 1)[1]
                logging.info("Loaded CLAUDE_CODE_OAUTH_TOKEN from cache file for OpenCode.")
                break
except Exception as _e:
    logging.warning(f"Could not load OAuth token cache for OpenCode: {_e}")
```

### Where the Token Lives
- **Cache file:** `/home/john/Thunderbird/OpsCenter/.claude_oauth_cache`
- **Format:** `CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...`
- **Written by:** `~/.claude/hooks/refresh_claude_oauth_cache.sh` (during Claude Code session)
- **Read by:** `spawn_opencode_headless()` and `spawn_claude_headless()` before subprocess spawn

---

## How It Works
1. Tasking watcher calls `spawn_opencode_headless()`
2. Function loads cache file and extracts the token
3. Token is injected into the subprocess environment via `env` parameter
4. OpenCode subprocess inherits the token
5. When OpenCode calls `claude -p "instructions"`, the token is available → Max OAuth kicks in → no API key needed

---

## Fallback: If Cache Load Fails
If the cache file is missing or unreadable:
- A warning is logged: `"Could not load OAuth token cache for OpenCode: {error}"`
- OpenCode still spawns (doesn't crash)
- OpenCode tasks will fail at the point they try to dispatch to Claude headless
- **Action:** Check if Claude Code session is running and refreshing the cache

---

## Reference Pattern
This exact pattern was already proven in `spawn_claude_headless()` (lines ~185-220 of the same file).

---

## Commit
```
fix: inject CLAUDE_CODE_OAUTH_TOKEN into OpenCode subprocess environment

OpenCode was spawning without access to the Claude Code OAuth token, preventing it from
dispatching to claude -p headless for complex tasks. Applied the same token-loading pattern
used by spawn_claude_headless() — reads from .claude_oauth_cache and injects into env before
subprocess.Popen().
```

---

## Verification
To verify the fix is active:
1. Check that `thunderbird_tasking_watcher.py` has the token-loading code in `spawn_opencode_headless()`
2. Verify cache file exists: `cat /home/john/Thunderbird/OpsCenter/.claude_oauth_cache`
3. Watch logs: `tail -f /home/john/Thunderbird/logs/inbox_watcher.log`
4. Look for: `"Loaded CLAUDE_CODE_OAUTH_TOKEN from cache file for OpenCode."`
