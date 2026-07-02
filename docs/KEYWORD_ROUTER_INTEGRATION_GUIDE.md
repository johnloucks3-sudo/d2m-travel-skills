# Keyword Auto-Router Integration Guide

**Status:** Code complete, integration pending  
**Files:** 5 new + 1 config  
**When:** Wire into session_init.py on next session  
**Goal:** Reduce token burn 60-80%, enable seamless OpenCode takeover

---

## Files Created

### 1. Core Router & Config

- **`core/ai_infra/keyword_auto_router.py`** (450 lines)
  - `KeywordAutoRouter` class — classifies prompts by keyword
  - `parse_commander_keyword()` — extracts @ctx, @zen, @free, @oc from text
  - `route_and_execute()` — main dispatch function
  - Supports 6 layers: ctx → zen → free → opencode → claude

- **`config/keyword_router_enhanced.yaml`** (250 lines)
  - 6 routing rules (ctx_data_processing, zen_reasoning, free_synthesis, free_extraction, opencode_handoff, default_claude)
  - 15+ keywords per layer
  - Provider chain config (Cerebras, GitHub, Groq, Ollama, Poe)
  - Commander keyword reference (@ctx, @zen, @free, @oc, @oc-takeover)

### 2. Inter-Instance Handoff

- **`core/hale_bus/hale_bus_handoff.py`** (320 lines)
  - `HaleBusHandoff` class — shared state via JSON
  - Mission claiming/releasing, status updates
  - Alert/FPD deadline tracking
  - ZEN response caching (24h TTL)
  - Decision logging
  - CC ↔ OC checkpoint protocol

### 3. Session Integration

- **`core/ai_infra/session_startup_keyword_router.py`** (180 lines)
  - `init_keyword_router()` — loads router + prior context
  - `detect_commander_keyword()` — parses user override
  - `session_startup_banner()` — prints alerts, missions, FPD on startup

- **`OpsCenter/opencode_keyword_dispatcher.py`** (240 lines)
  - `OpenCodeDispatcher` class — OpenCode's main router
  - Loads prior context from hale_bus on startup
  - Claims open missions from CC
  - Routes new work via shared keyword router
  - `handle_ctx_data_processing()`, `handle_free_infer()`, `handle_zen_reasoning()`

---

## Integration Steps (Checklist)

### Step 1: Wire into Claude Code Session Startup

In `OpsCenter/session_init.py` or similar, add:

```python
# At session startup (after logging init)
from core.ai_infra.session_startup_keyword_router import (
    init_keyword_router,
    session_startup_banner
)

router, prior_context = init_keyword_router("claude-code")
session_startup_banner("claude-code", prior_context)
```

This loads the router, prior context, and prints alerts on startup.

### Step 2: Add Keyword Detection to Main Loop

In your main loop (where you read Commander input):

```python
from core.ai_infra.keyword_auto_router import parse_commander_keyword

# When you receive prompt from Commander
keyword = parse_commander_keyword(prompt)

# Pass to router
layer, rule = router.classify(prompt, override_keyword=keyword)

# Route based on layer
if layer == "ctx_data_processing":
    # Use ctx_execute_file tool
    result = ctx_execute_file(prompt, rule["model"])
elif layer == "zen_independent_reasoning":
    # Use free_infer for ZEN
    result = free_infer(prompt, provider="github-r1")
elif layer.startswith("free_"):
    # Use free_model_router
    result = free_infer(prompt, provider=rule["provider"])
elif layer == "handoff_opencode":
    # Checkpoint and hand off
    hale_bus.checkpoint_session()
    # Signal OpenCode to take over
    return "HANDOFF_OPENCODE"
else:  # default_claude
    # Route to Haiku/Sonnet
    result = ask_haiku(prompt)
```

### Step 3: Add Session Checkpoint Before Exit

In your session shutdown/stop hook:

```python
from core.hale_bus.hale_bus_handoff import HaleBusHandoff

hale_bus = HaleBusHandoff("claude-code")
hale_bus.checkpoint_session()  # Save state for next instance
```

### Step 4: OpenCode Startup (Parallel)

In OpenCode `session_init.py`:

```python
from OpsCenter.opencode_keyword_dispatcher import OpenCodeDispatcher

dispatcher = OpenCodeDispatcher()  # Loads prior context from hale_bus
dispatcher.print_status()          # Print alerts, missions, etc.

# In main loop
result, tool, metadata = dispatcher.route_and_execute(prompt)

# At shutdown
dispatcher.checkpoint()
```

---

## Testing the Integration

### Quick Test: Router Classification

```python
from core.ai_infra.keyword_auto_router import KeywordAutoRouter

router = KeywordAutoRouter()

prompts = [
    "Extract JSON from this log",      # → ctx_data_processing
    "Counter my argument with refutation",  # → zen_independent_reasoning
    "Compare these two approaches",    # → free_synthesis
    "Run a health check on all systems",    # → ctx_parallel_monitoring
]

for prompt in prompts:
    layer, rule = router.classify(prompt)
    print(f"{prompt[:30]}... → {layer}")
```

### Full Integration Test: CC → OC Handoff

```python
from core.hale_bus.hale_bus_handoff import HaleBusHandoff
from OpsCenter.opencode_keyword_dispatcher import OpenCodeDispatcher

# Claude Code session
print("[CC] Checkpointing state...")
hale_bus_cc = HaleBusHandoff("claude-code")
hale_bus_cc.claim_work("MISSION-123", "in_progress")
hale_bus_cc.add_fpd_alert("McLeod", "2026-07-22", 11943.15, "2984034")
hale_bus_cc.checkpoint_session()

# OpenCode session
print("\n[OC] Loading prior context...")
dispatcher = OpenCodeDispatcher()
context = dispatcher.prior_context
print(f"[OC] {len(context['open_tasks'])} prior tasks claimed")
print(f"[OC] {len(context['fpd_deadlines'])} FPD alerts loaded")

# Checkpoint for next instance
dispatcher.checkpoint()
```

---

## Commander Keywords (Quick Reference)

When usage is high, Commander can type:

| Keyword | Behavior | Use Case |
|---------|----------|----------|
| `@ctx` | Force all work to sandbox | Data-heavy session, need immediate cost control |
| `@zen` | Spawn ZEN immediately | Need independent reasoning now |
| `@free` | All work via free models | Sonnet/Opus quota exhausted |
| `@oc` | Hand off to OpenCode, CC dormant | CC at >60% usage |
| `@oc-takeover` | OpenCode primary, CC fallback | Extended OpenCode operation |

Example:
```
User: @oc Extract JSON from this log
→ Parser detects @oc keyword
→ Router returns "handoff_opencode"
→ CC checkpoints, signals OC
→ OC's dispatcher receives "Extract JSON..."
→ OC routes to ctx_execute_file (sandbox)
```

---

## Architecture Diagram

```
Claude Code Session                 OpenCode Session
═══════════════════════════════    ══════════════════════════════════
User Prompt
    ↓
parse_commander_keyword() 
    ↓
KeywordAutoRouter.classify()
    ├─ ctx_data_processing      ← sandbox execution (zero-cost)
    ├─ zen_independent_reasoning ← free_infer (Groq/Cerebras/GitHub)
    ├─ free_synthesis           ← free_infer (reasoning tier)
    ├─ free_extraction          ← free_infer (Mistral, deterministic)
    ├─ handoff_opencode         → hale_bus.checkpoint() → OC startup
    │                                                    ↓
    │                           OpenCodeDispatcher.route_and_execute()
    │                                   ↓
    │                           (same router, same rules)
    │                                   ↓
    │                           ctx_execute_file / free_infer / etc.
    │                                   ↓
    │                           OpenCode cached ZEN, prior context
    │                                   ↓
    │                           hale_bus.checkpoint() ← CC on next start
    │
    └─ default_claude           → Haiku (escalate if needed)
        ↓
    Execute (ctx_execute / free_infer / Claude)
        ↓
    hale_bus.checkpoint()       (on shutdown)
```

---

## Token Burn Reduction (Expected)

| Scenario | Before | After | Savings |
|----------|--------|-------|---------|
| Data extraction (1KB log) | 2K tokens (Haiku read + process) | 50 tokens (ctx_execute) | 97% |
| ZEN counter-voice | 1.5K tokens (Sonnet) | 0 tokens (free-infer) | 100% |
| Multi-source synthesis | 3K tokens (Sonnet) | 0 tokens (free-infer) | 100% |
| 5h cycle (with auto-routing) | ~320 tokens | ~120 tokens | 62% |

---

## Known Limitations & Future Work

- DeepInfra blocked (MISSION-394 — HTTP 402, requires paid balance)
- OpenCode dispatcher is skeleton (framework ready for full implementation)
- ctx_execute_file dispatch doesn't auto-apply results (caller must handle)
- No automatic retry loop (manual for now, loop logic TBD)

---

## Related Memory & Tasks

- **Memory:** `project_free_model_ecosystem_20260625.md` — integrated providers
- **Memory:** `project_keyword_auto_routing_plus_opencode.md` — full design
- **Task:** `MISSION-810` — implement auto-routing (this work)

---

## Questions?

Refer to:
- `project_keyword_auto_routing_plus_opencode.md` (design details)
- `keyword_auto_router.py` (docstrings + examples)
- `hale_bus_handoff.py` (state management)

