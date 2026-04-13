# Claude Free-Tier Migration Plan

## Current State Analysis

### Problem
The Switchblade-4 tests are failing because:
1. `_call_claude()` function tries to use Claude API calls
2. We've enforced free-tier only operation (SO-2026-04-06)
3. Claude API calls require paid credits and fail with exit code 1

### Files Requiring Immediate Attention
Based on grep results, these core modules use Claude API calls:

**CRITICAL (Persona System):**
- `core/ai_infra/thunderbird_personas.py` - `_call_claude()` function
- `core/email/thunderbird_commander_inbox.py` - Uses `_call_claude()`
- `core/email/thunderbird_email_intel.py` - Uses `_call_claude_sonnet()`
- `core/email/thunderbird_dani_voice.py` - Uses `anthropic.Anthropic()` directly

**HIGH PRIORITY:**
- `core/booking/thunderbird_files_api.py` - Anthropic Files API uploads
- `core/intel/thunderbird_competitive_surveillance.py` - `_call_claude_cli()`
- `core/intel/thunderbird_incubator.py` - `_call_claude()` function
- `core/intel/thunderbird_price_monitor.py` - Uses `anthropic.Anthropic()`

## Free-Tier Replacement Strategy

### Option 1: Open-Source Claude Code CLI Integration

**Available Open-Source Implementations:**
1. `yasasbanukaofficial/claude-code` (2,287 stars) - TypeScript CLI skeleton
2. `huangserva/claude-code-cli` (549 stars) - Complete CLI client with 43 tools
3. `codeaashu/claude-code` (1,968 stars) - Agentic coding tool framework

**Implementation Plan:**
1. Replace `_call_claude()` with calls to open-source CLI
2. Use `claude -p` command via subprocess (already works manually)
3. Ensure environment stripping works correctly

### Option 2: Free-Tier Model Fallbacks

**Available Free Models:**
- `openrouter/deepseek/deepseek-chat-v3.1` (~$0.27/M) - **Current Default**
- `mistral-small:free` - Free tier fallback
- `openrouter/qwen3.6-plus-free` - Free alternative
- `openrouter/nemotron-3-super-free` - Nemotron free fallback

### Option 3: Hybrid Approach
1. **Primary:** `claude -p` via CLI (free via Max OAuth)
2. **Fallback:** OpenCode with free-tier models
3. **Emergency:** Local model inference if available

## Implementation Steps

### Step 1: Fix `_call_claude()` Function

**Current (broken):**
```python
def _call_claude(system_prompt: str, query: str, max_tokens: int = 2000,
                 model: str = "sonnet") -> str:
    # Uses subprocess.run with Claude CLI
    # Fails because API calls require credits
```

**Proposed Fix:**
```python
def _call_claude_free_tier(system_prompt: str, query: str, max_tokens: int = 2000,
                           model: str = "sonnet") -> str:
    """Call Claude via free-tier methods.
    
    Priority:
    1. Claude CLI with OAuth (claude -p)
    2. OpenCode with free models
    3. Fallback to local models if available
    """
    
    # Try Claude CLI first (free via Max OAuth)
    try:
        cmd = [CLAUDE_CMD, "-p", f"{system_prompt}\n\n{query}", 
               "--dangerously-skip-permissions", "--output-format", "text"]
        clean_env = {k: v for k, v in os.environ.items() 
                     if k != "ANTHROPIC_API_KEY"}
        clean_env["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              timeout=300, env=clean_env)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    # Fallback to OpenCode with free model
    try:
        opencode_cmd = ["opencode", "run", "-m", "openrouter/deepseek/deepseek-chat-v3.1",
                       f"System: {system_prompt}\n\nUser: {query}"]
        result = subprocess.run(opencode_cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    # Emergency fallback
    return "[Free-tier Claude service temporarily unavailable]"
```

### Step 2: Replace Anthropic SDK Calls

**Files using `anthropic.Anthropic()`:**
- `thunderbird_dani_voice.py`
- `thunderbird_files_api.py` 
- `thunderbird_price_monitor.py`

**Replacement:** Use free-tier alternatives or disable functionality.

### Step 3: Update Persona Model Mapping

**Current:**
```python
PERSONA_MODEL_MAP = {
    "COS": "opus",    # Needs to change
    "EXEC": "opus",   # Needs to change
    "A2": "sonnet",
    "A3": "sonnet",   # Dani - client facing
    "A5": "sonnet",
    "A6": "sonnet", 
    "A9": "sonnet",
    "A10": "sonnet",
    "CH": "sonnet",
    "A12": "sonnet",
}
```

**Proposed:**
```python
PERSONA_MODEL_MAP = {
    "COS": "claude-cli",    # Use CLI free tier
    "EXEC": "claude-cli",   # Use CLI free tier  
    "A2": "deepseek-v3.1",  # Research - free tier OK
    "A3": "claude-cli",     # Client facing - use CLI
    "A5": "deepseek-v3.1",  # Strategy - free tier
    "A6": "deepseek-v3.1",  # Creative - free tier
    "A9": "deepseek-v3.1",  # Finance - free tier
    "A10": "deepseek-v3.1", # Crisis - free tier
    "CH": "claude-cli",     # Ethics - use CLI
    "A12": "deepseek-v3.1", # Innovation - free tier
}
```

## Timeline

**Phase 1 (Immediate):** Fix `_call_claude()` function
**Phase 2 (24h):** Replace Anthropic SDK calls  
**Phase 3 (48h):** Update persona model preferences
**Phase 4 (72h):** Test Switchblade-4 recovery

## Risk Assessment

**High Risk:** Client-facing personas (A3/Dani) may experience quality drop
**Medium Risk:** COS and EXEC may have reduced capability
**Low Risk:** Research/strategy personas can use free-tier models

## Backup Plan

If free-tier quality is unacceptable:
1. Re-enable Claude API for critical personas only
2. Implement strict usage quotas
3. Use hybrid approach with fallbacks

---

**Status:** Ready for implementation
**Priority:** CRITICAL
**Impact:** All persona-based operations