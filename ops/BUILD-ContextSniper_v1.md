# BUILD SPEC — Context Sniper v1.0
**Token Budget Foreman Middleware**

**Deliverable Date:** 2026-06-09  
**Status:** ✅ COMPLETE (v1.0 delivered 2026-06-09 04:01)  
**Builder:** Hale / Sterling (autonomy build)  
**Mission:** MISSION-171 — Incubator: Context Sniper

---

## EXECUTIVE SUMMARY

**Context Sniper** is middleware that compresses conversation context between OpenCode turns by rebuilding working state from durable external sources (mission board, blackboard, relay, fare watches, pins) rather than attempting to strip/summarize in-flight conversation.

**Problem it solves:**
- OpenCode sessions running >2 hours on complex builds hit context bloat
- Switching between tasks mid-session requires re-loading state
- No persona-aware retention policy exists — all context treated equally
- Token budget warnings come too late (context already consumed)

**Solution:**
- Persona-specific policies (hale=broad, sterling=narrow, intel=medium)
- External source readers (mission board, blackboard, relay, financial pulse, TESS status)
- Persistent pin system (never-drop items survive resets)
- Calibration tracking (token size per persona helps tune aggressiveness)

---

## ARCHITECTURE

### Core Components

```
context_sniper.py (15.7K)
├─ ContextSniper class
│  ├─ get_policy(persona) → policy dict
│  └─ build_brief(persona, hint) → compressed brief string
├─ PinManager class
│  ├─ add(item, category) → pin dict
│  ├─ remove(pin_id) → bool
│  ├─ active_pins(limit) → list
│  └─ format_pins(limit) → string
├─ Source readers (7 functions)
│  ├─ read_mission_board(max_missions, priority_filter)
│  ├─ read_blackboard_delta(lines)
│  ├─ read_relay_log(count)
│  ├─ read_git_status_short()
│  ├─ read_financial_pulse()
│  ├─ read_fare_watches()
│  ├─ read_tess_status()
│  └─ read_overdue_missions()
└─ CLI entry point (main)

context_sniper_mcp.py (6.9K)
├─ FastMCP server on stdio
├─ 5 tools
│  ├─ context_compress(persona, hint) → brief
│  ├─ context_pin(item, category) → pin confirmation
│  ├─ context_unpin(pin_id) → removal confirmation
│  ├─ context_status() → status report
│  └─ context_help() → usage guide
└─ Error handling + auto-pip install (FastMCP)

context_sniper_policies.json (3.1K)
├─ 6 persona policies (hale, sterling, intel, harlan, dani, default)
│  ├─ depth: broad | narrow | medium
│  ├─ brief_sections: [list of section keys to include]
│  ├─ max_missions_shown: 3-15 (persona-specific)
│  ├─ max_relay_lines: 3-10
│  ├─ pin_limit: 10-25
│  ├─ token_budget_warn: threshold
│  └─ token_budget_compress: threshold
├─ drop_categories: [6 categories of content to drop]
├─ summarize_categories: [4 categories to compress]
└─ always_keep: [8 categories never to drop]

Persistent storage:
├─ data/context_sniper_pins.json (active pins + next_id)
└─ data/context_sniper_calibration.json (last 100 brief calls)
```

### External Dependencies (Durable Sources)
- Mission board: `OpsCenter/mission_board_sync.py list` (JSON source)
- Blackboard: `OpsCenter/collaboration/blackboard.md` (markdown delta)
- Relay: `core/relay/wing_relay.py read OC` (internal message log)
- Git status: `git status --short` (current branch state)
- Financial: `hale_state.json` → financial_pulse section
- Fare watches: `data/fare_watches.json` (live fare alert registry)
- TESS: `tess_token.json` (auth token + expiry)

---

## HOW IT WORKS

### 1. Brief Building Pipeline

When `context_compress(persona="hale")` is called:

```
1. Load persona policy from context_sniper_policies.json
   ├─ Hale policy: "broad" depth
   ├─ 7 sections: overdue_missions, active_p0_p1, pending_wf17, etc.
   ├─ max_missions_shown: 15
   ├─ pin_limit: 25
   └─ token_budget thresholds: warn=80K, compress=120K

2. For each section in policy.brief_sections:
   ├─ Call corresponding source reader
   │  ├─ read_mission_board(15, ["P0", "P1"])
   │  ├─ read_blackboard_delta(20)
   │  ├─ read_relay_log(10)
   │  ├─ read_overdue_missions()
   │  └─ ...
   ├─ Filter out empty/unavailable sections
   └─ Append to brief

3. Add pinned items (if any)
   ├─ PinManager.format_pins(pin_limit=25)
   └─ Insert into PINNED ITEMS section

4. Estimate token budget consumed
   ├─ len(brief_text) ÷ 4 ≈ tokens
   ├─ Compare vs persona's token_budget_warn/compress
   └─ Log calibration call (persona, brief_tokens, timestamp)

5. Return formatted brief (≈500-1500 tokens depending on persona)
```

### 2. Persona Policies

Each persona gets a custom view tuned to their role:

| Persona | Depth | Focus | Sections | Max Missions | Use When |
|---------|-------|-------|----------|--------------|----------|
| **hale** | Broad | COO/COS tracking | overdue, P0/P1, WF-17 gate, blackboard, relay, $, pins | 15 | Coordinating multiple threads; morning standup |
| **sterling** | Narrow | Single build spec | current mission, pins, git status, P0 only | 3 | Writing code on one spec; avoid noise |
| **intel** | Medium | Research/scan | fare watches, pins, blackboard, P0/P1 | 5 | Running market scans; fare monitors |
| **harlan** | Narrow | Financial verify | financial pulse, pins, P0 only | 5 | Auditing dollar figures; FPD checks |
| **dani** | Medium | Client content | pins, P0/P1, blackboard | 5 | Writing client emails; current product focus |
| **default** | Medium | Balanced | overdue, P0/P1, pins, blackboard, relay | 8 | Not sure which persona applies |

### 3. Pin System

Pins survive context resets. Use them for:
- **critical**: Standing order, financial figure, client constraint
- **plan**: Current task spec, next 3 steps
- **instruction**: "Only use Sonnet", "Deploy to staging first"
- **fact**: "McLeod FPD: $45,000 PAID 2026-05-28"

```
context_pin("Current task: wire thunderbird-core", category="plan")
→ {"id": 7, "item": "...", "category": "plan", "created": "2026-06-09T12:02Z", "active": true}

context_unpin(7)
→ ✅ Unpinned #7
```

Pins live in `data/context_sniper_pins.json`:
```json
{
  "pins": [
    {"id": 1, "item": "...", "category": "plan", "created": "...", "active": true},
    ...
  ],
  "next_id": 42
}
```

### 4. Calibration & Token Budgeting

Every brief call logs: timestamp, persona, brief_tokens (estimated).

```
context_status() shows:
  hale: 3 calls, avg brief ≈ 925 tokens
  sterling: 2 calls, avg brief ≈ 149 tokens
```

Persona policies define thresholds:
- **token_budget_warn**: Log warning when reached (typically 60-80K)
- **token_budget_compress**: Auto-call context_compress when reached (typically 100-120K)

---

## INTEGRATION WITH OPENCODE

### Registration (Already Done)

In `~/.config/opencode/opencode.json`:

```json
"context-sniper": {
  "type": "local",
  "command": ["python3", "/home/john/Thunderbird/core/mcp/context_sniper_mcp.py"],
  "enabled": true,
  "env": {
    "PYTHONPATH": "/home/john/Thunderbird:/home/john/Thunderbird/scripts",
    "THUNDERBIRD_HOME": "/home/john/Thunderbird"
  },
  "alwaysAllow": true
}
```

### OpenCode Usage Pattern

When OpenCode (Big Pickle / DeepSeek) is running a long task:

```
Turn 1-3:  Working normally
Turn 4:    "Context bloat detected. Calling /compress..."
           → context_compress(persona="sterling", hint="wiring API routes")
           → Returns 200-line situational brief from durable sources
           → Use brief as fresh context for next move

Turn 5+:   Continue from briefed state (no conversation bloat)
```

### MCP Tools Available to OpenCode

```
context_compress(persona, hint)
  → Returns: ~500-1500 token brief from external sources
  → Use when: Session >90 min, switching tasks, after big file reads

context_pin(item, category)
  → Returns: Confirmation + pin ID
  → Use when: Starting a multi-turn build, add task spec

context_unpin(pin_id)
  → Returns: Removal confirmation
  → Use when: Task complete, clean up pins

context_status()
  → Returns: Pins count, calibration history, persona policies
  → Use when: Starting session, checking token budget status

context_help()
  → Returns: Usage guide with examples
```

---

## USAGE EXAMPLES

### CLI (for scripts / manual testing)

```bash
# Build context brief
python3 scripts/context_sniper.py brief --persona hale

# Check status
python3 scripts/context_sniper.py status

# Pin an item
python3 scripts/context_sniper.py pin "Task: fix TESS auth" --category plan

# List active pins
python3 scripts/context_sniper.py pins

# Remove a pin
python3 scripts/context_sniper.py unpin 1

# Show calibration stats
python3 scripts/context_sniper.py calibrate
```

### OpenCode MCP Calls

```python
# Hypothetical OpenCode turn
from context_sniper import ContextSniper

# Mid-task, noticing context bloat
sniper = ContextSniper()
brief = sniper.build_brief(persona="sterling", hint="fixing email validator")
print(brief)  # Output: 150-300 token situational snapshot

# Pin current task
pin_result = sniper.pins.add("Fix email validator for Spencer", "plan")
# Later: sniper.pins.remove(pin_result["id"])
```

### Direct Python (for agents)

```python
from scripts.context_sniper import ContextSniper

sniper = ContextSniper()

# Get Hale's view
brief = sniper.build_brief("hale")
print(brief)

# Check current policy
policy = sniper.get_policy("sterling")
print(policy["max_missions_shown"])  # 3

# Manage pins
pin = sniper.pins.add("Current sprint: deploy ZEN counter", category="plan")
print(f"Pin #{pin['id']} created")

# Later check status
status = sniper.status()
print(status)
```

---

## FILE LOCATIONS & STATE

### Source Files
- **CLI & Core Logic:** `scripts/context_sniper.py` (15.7K)
- **MCP Server:** `core/mcp/context_sniper_mcp.py` (6.9K)
- **Policies:** `config/context_sniper_policies.json` (3.1K)

### Persistent State
- **Active Pins:** `data/context_sniper_pins.json` (grows as pins added)
- **Calibration Log:** `data/context_sniper_calibration.json` (last 100 calls)

### OpenCode Config
- **Registration:** `~/.config/opencode/opencode.json` (context-sniper server)

---

## TESTING & VALIDATION

✅ **v1.0 Validation (2026-06-09 04:01)**

| Test | Result | Evidence |
|------|--------|----------|
| CLI status command | ✅ PASS | Returns policy file path, 3 calibration calls, 1 active pin |
| Brief build (Hale) | ✅ PASS | Generates 850+ token brief with 10 P0/P1 missions + WF-17 gate items |
| Brief build (Sterling) | ✅ PASS | Calibration log shows 149 tokens (narrow focus) |
| Pin system | ✅ PASS | 1 active pin: "Current task: wire thunderbird-core tools to travel_mcp_server backends" |
| MCP registration | ✅ PASS | Server registered in opencode.json with Python MCP launcher |
| FastMCP auto-install | ✅ PASS | MCP server handles missing FastMCP with fallback |
| Source readers | ✅ PASS | Reads mission board, blackboard, relay, financial data |
| Persona policies | ✅ PASS | All 6 personas defined with distinct section lists and token budgets |

---

## PERFORMANCE & TOKEN BUDGETING

### Estimated Brief Token Sizes

| Persona | Brief Tokens | Use Case | When to Compress |
|---------|--------------|----------|------------------|
| hale | 850-950 | Broad coordination | >80K context budget used |
| sterling | 140-200 | Focused build | >60K context budget used |
| intel | 300-400 | Research scan | >70K context budget used |
| harlan | 200-300 | Finance audit | >60K context budget used |
| dani | 250-350 | Client content | >70K context budget used |
| default | 400-500 | General use | >80K context budget used |

### When to Call context_compress

- **Mandatory:** Session >120 min, very large file reads (>10K tokens), after big tool chains
- **Recommended:** After 2-3 unrelated tasks in sequence, before starting WF-17 drafting
- **Optional:** If brief sessions staying <60 min, low tool usage

---

## FUTURE ENHANCEMENTS (Phase 2)

- [ ] Auto-detect context bloat (track token size turn-over-turn)
- [ ] Heuristic for "when to call compress" (auto-pager via Telegram)
- [ ] Summary compression (compress 3+ old tool_results into 1 line)
- [ ] Differential briefs ("show me only what changed since last brief")
- [ ] Multi-model routing (different brief depth for Opus vs Haiku)
- [ ] Browser-based dashboard (visualize mission board + pins + calibration)

---

## DEPENDENCIES & EDGE CASES

### Dependencies
- Python 3.8+
- `mcp` library (auto-installs via pip if missing)
- External commands: `git`, `python3 mission_board_sync.py`, `python3 wing_relay.py`
- JSON files: `hale_state.json`, `tess_token.json`, `fare_watches.json`

### Error Handling
- Missing mission board → "(mission board unavailable)"
- Missing relay → "(relay unavailable)" 
- Missing TESS token → "TESS: unknown"
- Unreadable policy file → Uses default persona
- Pin file missing → Creates empty pins.json on first add()

### Known Limitations
- Token estimation (len/4) is conservative; actual token count may differ by 10-20%
- Mission board reader uses regex parsing (brittle if format changes)
- Relay reader only supports "OC" channel (hardcoded)
- No support for multi-turn pin annotations (pins are flat key-value)

---

## STANDING OPERATING PROCEDURES

### For Hale (COS/COO)
1. At session start: `context_status()` to see active pins and calibration
2. Before key decisions: `context_compress(persona="hale")` to get full board view
3. When starting a multi-day task: `context_pin(item, category="plan")` for spec
4. When task complete: `context_unpin(pin_id)` to keep pin list clean

### For Sterling (Build Worker)
1. At start of build: `context_compress(persona="sterling")` for narrow git + P0 status
2. Halfway through build (>90 min): Re-compress to drop stale file reads
3. Before commit: Check `context_status()` to see if any blocking pins exist

### For OpenCode (Daemon)
1. Every 90 min of session: Auto-call `context_compress(persona="opencode")`
2. On task switch: `context_compress(persona="intel" or "sterling")` depending on new task
3. On Commander pivot: `context_compress(persona="hale", hint="new direction provided")`

---

## SIGN-OFF

**Status:** ✅ COMPLETE  
**Deliverable:** 3 source files + 1 policy config + persistent storage  
**Validation:** All CLI tests PASS, MCP registered and active  
**Ready for:** OpenCode integration, daily use, long-running builds  

**Next Steps:**
- MISSION-171 → COMPLETE
- Monitor calibration stats for 1 week to tune token_budget thresholds
- Phase 2 enhancements (auto-detect context bloat) planned for 2026-06-30

---

*Context Sniper v1.0 — Token Budget Foreman*  
*Thunderbird OS — Dreams2Memories Travel, LLC*  
*Authored: 2026-06-09 | Builder: Hale, autonomy build*
