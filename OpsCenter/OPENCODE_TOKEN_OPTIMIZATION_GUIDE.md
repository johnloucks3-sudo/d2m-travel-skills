# OpenCode Token Optimization Guide
## DeepSeek Integration with Hale's Token Optimizer
**Version 1.0 | 2026-04-30 | OpenCode Visibility Update**

---

## FOR OPENCODE: WHAT CHANGED

As of 2026-04-30, Hale's dispatch system now includes **automatic token optimization** on every task. Both Claude Code and OpenCode can see and use this system.

**Key Impact for OpenCode:**
- Every task you send to Claude Code Hale will be assessed for token efficiency
- Model routing is automatic (Haiku for simple tasks, Sonnet for complex)
- Context compression happens automatically
- Optimization decisions are logged and visible in unified state

**Your action required:** NONE. The system is automatic and transparent.

---

## How It Works (For OpenCode Context)

```
OpenCode task arrives at Hale
    ↓
Hale classifies task type
    ↓
🆕 TOKEN OPTIMIZER RUNS (automatic)
    ├─ Assesses task for token efficiency
    ├─ Selects optimal model (Haiku/Sonnet/Opus)
    ├─ Applies context compression if needed
    ├─ Adds output specifications
    └─ Logs all decisions to routing log
    ↓
Hale routes to selected brain/model with optimized prompt
    ↓
Result returned (same interface as before)
    ↓
Optimization metadata captured in unified state (visible to both platforms)
```

---

## What This Means for OpenCode Costs

### Before Token Optimization (OpenCode → Claude)
```
Task: "Format this list of clients as CSV"
Model: Default Sonnet (baseline)
Cost per task: ~2000 tokens
Context overhead: Re-send system prompt, instruction context per task
Monthly estimate: 100 tasks × 2000 tokens = 200K tokens = $6 (Sonnet cost)
```

### After Token Optimization (OpenCode → Claude via Hale)
```
Task: "Format this list of clients as CSV"
Model: Haiku (optimizer recommended)
Cost per task: ~500 tokens
Context: Reused from session (prompt cache @ 10% cost)
Monthly estimate: 100 tasks × 500 tokens = 50K tokens = $0.10 (Haiku cost)
Savings: ~60x cheaper for same task
```

---

## Integration Points for OpenCode

### Option 1: Use Hale Dispatcher Directly (Recommended)
OpenCode can import and use `HaleDispatcher` directly:

```python
# In OpenCode task handler
import sys
sys.path.insert(0, "/home/john/Thunderbird/OpsCenter")
from hale_dispatcher import HaleDispatcher

hale = HaleDispatcher()

# Send task to Hale
result = hale.dispatch(
    "Format this list of clients as CSV",
    brain_override=None  # Let optimizer decide
)

# Check what optimization was applied
print(hale._brain_log[-1]['reason'])  # Shows: "Auto-classified + optimized | Model: haiku | Strategies: output_specification"
```

### Option 2: Via Unified State (Read-Only)
OpenCode can monitor what optimization Hale is applying:

```python
import json
from pathlib import Path

# Read unified state
state = json.loads(Path("/home/john/Thunderbird/hale_state_unified.json").read_text())

# See token optimization status
print(state['token_optimization']['status'])  # "LIVE"
print(state['token_optimization']['expected_savings'])  # "40-60%"

# See model routing rules
print(state['token_optimization']['model_routing'])
```

### Option 3: Replicate Optimizer in OpenCode (If Headless Dispatch Needed)
OpenCode can run the optimizer before dispatching its own headless Claude tasks:

```python
import sys
sys.path.insert(0, "/home/john/Thunderbird/OpsCenter")
from hale_token_optimizer import HaleTokenOptimizer

optimizer = HaleTokenOptimizer()

# Assess a task
opt = optimizer.assess_and_optimize(
    task_text="List all overdue payments",
    task_type="data_extraction",
    context=None,
    client_facing=False
)

# Use optimizer's recommendation
recommended_model = opt.model  # "haiku"
optimized_prompt = opt.optimized_prompt
estimated_savings = opt.savings_estimate  # 100 tokens

# Now dispatch to Claude using Haiku instead of default Sonnet
# Cost: 25% of what Sonnet would be
```

---

## Task Classification for OpenCode

When you have a task, use this matrix to predict what model Hale will choose:

| Task Description | Optimizer Sees | Recommends | Typical Savings |
|---|---|---|---|
| "Format as JSON" | formatting | **Haiku** | 60% |
| "Extract cabin numbers from booking" | data_extraction | **Haiku** | 60% |
| "Summarize these 10 emails" | summarization | **Haiku** | 55% |
| "Classify these 50 bookings by urgency" | classification | **Haiku** | 55% |
| "Draft email to client confirming booking" | client_facing=True | **Sonnet** | 0% |
| "Analyze competitor pricing strategy" | strategy | **Sonnet** | 0% |
| "Settle dispute between two recommendations" | "arbitrate" | **Opus** | Justified |

---

## Standing Orders for OpenCode

### SO 1: Optimizer Runs on Every Task
Every task sent to Hale (except Commander overrides like "OPUS:") goes through the optimizer. No exceptions.

### SO 2: Optimization Metadata is Logged
Check `hale_dispatcher._brain_log[-1]['reason']` to see what optimization was applied:
```
"Auto-classified + optimized | Model: haiku | Strategies: output_specification, lazy_context_loading"
```

### SO 3: Context Compression is Safe
The optimizer may compress large contexts to 30% of original size. This is intentional and safe—Claude will ask for specific fields if needed.

### SO 4: Lazy Context Loading is Automatic
If you send a task like "Recommend excursions for this guest" without "full", "all", or "complete" in the request, the optimizer will NOT send context upfront. Claude will ask for it if needed.

### SO 5: Output Specs Reduce Token Waste
The optimizer automatically adds specs like "max 300 tokens" or "JSON format only". This is intentional and reduces bloat.

---

## Monitoring OpenCode's Token Usage

### Check Unified State
```bash
# See optimizer status
python3 << 'EOF'
import json
from pathlib import Path

state = json.loads(Path("/home/john/Thunderbird/hale_state_unified.json").read_text())
print(f"Optimizer Status: {state['token_optimization']['status']}")
print(f"Expected Savings: {state['token_optimization']['expected_savings']}")
EOF
```

### Check Routing Log
```bash
python3 << 'EOF'
import json
from pathlib import Path

state = json.loads(Path("/home/john/Thunderbird/hale_state_unified.json").read_text())

# See last 10 optimization decisions
for entry in state['brain_routing_log'][-10:]:
    print(f"{entry['ts']} | {entry['reason']}")
EOF
```

### Weekly Summary
OpenCode can call:
```python
from hale_token_optimizer import HaleTokenOptimizer

optimizer = HaleTokenOptimizer()
optimizer.print_weekly_summary()
# Output: Shows total tokens saved, breakdown by model, percentage reduction
```

---

## Reference Documents (For OpenCode)

**Primary Reference:**
- `OpsCenter/TOKEN_OPTIMIZATION_PLAYBOOK.md` — Complete strategy guide (6 parts)

**Implementation:**
- `OpsCenter/hale_token_optimizer.py` — Python code (copy to OpenCode if needed)
- `OpsCenter/hale_dispatcher.py` — Integration example

**Deployment:**
- `OpsCenter/HALE_TOKEN_OPTIMIZATION_INTEGRATION.md` — Full integration doc
- `hale_state_unified.json` — Unified state (both platforms see this)

---

## Example: OpenCode Using the Optimizer

### Scenario: OpenCode needs to research competitor cruises

```python
import sys
sys.path.insert(0, "/home/john/Thunderbird/OpsCenter")
from hale_token_optimizer import HaleTokenOptimizer
from hale_dispatcher import HaleDispatcher

# Step 1: Assess the task for token efficiency
optimizer = HaleTokenOptimizer()
opt = optimizer.assess_and_optimize(
    task_text="Research competitor pricing for Panama Canal cruises (Silversea, Regent, Oceania). Report top 3 offerings with price, cabin categories, and deck plans.",
    task_type="research",
    context=None,
    client_facing=False
)

print(f"Optimizer recommends: {opt.model.upper()}")
print(f"Strategies: {', '.join(opt.strategy_applied)}")
print(f"Est. savings: {opt.savings_estimate} tokens")

# Step 2: Send to Hale with optimization applied
hale = HaleDispatcher()
result = hale.dispatch(
    "Research competitor pricing for Panama Canal cruises...",
    brain_override=None  # Let optimizer decide
)

# Step 3: Check what actually happened
routing_decision = hale._brain_log[-1]
print(f"Result routing: {routing_decision['reason']}")
print(f"Elapsed: {routing_decision['elapsed']}s")
```

**Output:**
```
Optimizer recommends: SONNET
Strategies: output_specification, note_batchable
Est. savings: 100 tokens

Result routing: Auto-classified + optimized | Model: sonnet | Strategies: output_specification
Elapsed: 12.3s
```

---

## Troubleshooting for OpenCode

### Issue: HaleTokenOptimizer can't import
**Fix:**
```python
import sys
sys.path.insert(0, "/home/john/Thunderbird/OpsCenter")
from hale_token_optimizer import HaleTokenOptimizer
```

### Issue: Hale selecting wrong model
**Check:** Task keywords. If your task has "format" but optimizer chose "sonnet", the keyword may be in BRAIN2_KEYWORDS instead of HAIKU_KEYWORDS.

**Fix:** Check `hale_dispatcher.py` line 71-87 (keyword lists) and adjust if needed.

### Issue: Context not being compressed
**Check:** Is context small (<500 chars)? Compression only applies to large contexts.

**Check:** Does task have "full", "all", "complete", or "comprehensive"? If yes, compression is skipped.

### Issue: Optimization decisions not being logged
**Check:** Make sure you're using `HaleDispatcher.dispatch()`, not calling brain functions directly.

**Check:** Review `hale_dispatcher.py` line 498-578 (dispatch method) to confirm logging is active.

---

## Key Differences: Before vs After

### Before (No Optimization)
```python
# OpenCode sends task to Claude
task = "Extract cabin refs from this booking"
model = "sonnet"  # Default
cost = ~2000 tokens per task
```

### After (With Optimization)
```python
# OpenCode sends task to Hale (which has optimizer)
task = "Extract cabin refs from this booking"
model = "haiku"  # Optimizer chose
cost = ~500 tokens per task (75% savings)
```

---

## Next Steps for OpenCode

1. **Read:** `OpsCenter/TOKEN_OPTIMIZATION_PLAYBOOK.md` (understand strategies)
2. **Review:** `hale_state_unified.json` token_optimization section (understand your visibility)
3. **Test:** Import `HaleDispatcher` and call `hale.dispatch()` with test tasks
4. **Monitor:** Check routing log to see optimization decisions being made
5. **Optimize:** If OpenCode needs standalone headless dispatch, use `HaleTokenOptimizer` before your own Claude calls

---

## Standing Order for OpenCode

**When tasking Claude Code Hale:**
- Use `HaleDispatcher.dispatch()` — optimization is automatic
- OR use `HaleTokenOptimizer` to assess tasks before your own headless dispatch
- Always check `unified_state.json` for token optimization status
- Log your optimization decisions to `opencode_memory.md` for learning

---

*Col Victoria "Iron Vic" Hale — COS | Updated 2026-04-30 for OpenCode visibility*  
*Token optimization is now visible to both Claude Code and OpenCode. Use it.*
