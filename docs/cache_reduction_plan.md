# Thunderbird Cache Reduction — 3-Approach Implementation Plan
## Status: APPROACH 1 COMPLETE · APPROACH 2 IN PROGRESS · APPROACH 3 DESIGN READY
## Last Updated: 2026-03-27

---

## EXECUTIVE SUMMARY — THREE SIMULTANEOUS APPROACHES

We implement all three cache reduction strategies in parallel. On Max plan, limit optimization (not cost) is the goal. Cache reads don't count against rate limits — fresh tokens do. Reducing fresh token input per turn extends session lifetime.

### Approach 1: Session-Type MCP Profiles (COMPLETE ✅)
**What**: Load only the tools needed for the session type
**How**: `MCP_PROFILE` env var in `travel_mcp_server.py` controls which tool groups register
**Launch**: `cc core` / `cc intel` / `cc travel` / `cc ops` / `cc full`
**Files created**:
- `travel_mcp_server.py` — MCP_PROFILE-aware loader (CORE/INTEL/TRAVEL/OPS groups)
- `mcp_launcher_core/intel/travel/ops.sh` — profile-specific launcher scripts
- `~/.claude/profiles/mcp_core/intel/travel/ops/full.json` — MCP config per profile
- `~/bin/cc` — wrapper script: `cc core` → `claude --mcp-config ... --strict-mcp-config`
- Shell aliases: `cc-core`, `cc-intel`, `cc-travel`, `cc-ops`, `cc-full`

**Token savings**:
- full → core: ~60K fewer tool schema tokens per turn (core has ~25 vs 120+ tools)
- full → travel: ~40K fewer tokens per turn
- Applies every turn = compounding session-long savings

### Approach 2: Gateway Proxy — Wake-On-Call (IN PROGRESS 🔄)
**What**: Lightweight meta-server always in MCP stack; manages profile state mid-session
**How**: `thunderbird_mcp_gateway.py` with `activate_domain()`, `list_profiles()`, `gateway_status()` tools
**Limitation**: FastMCP fixes tool schemas at startup — can't inject new tools mid-session
**Workaround**: Gateway writes `~/.claude/gateway_state.json` with requested profile → use `cc <profile>` to start next session correctly
**Files**:
- `thunderbird_mcp_gateway.py` — FastMCP gateway server (4 tools)
- `~/.claude/gateway_state.json` — state file tracking active/requested profiles
- Gateway added to ALL 5 profile JSON configs

**To use mid-session**: `activate_domain("intel")` → tells you to run `cc intel` for next session

### Approach 3: Deferred Tools Optimization (DESIGN READY 📋)
**What**: Claude Code's built-in deferred tool system — tool schemas are NOT loaded until ToolSearch is called
**Status**: Already active for all 200+ MCP tools (they appear as names in system-reminder, schemas fetched on-demand)
**Optimization**: The 120+ dreams2memories tools are already deferred. Context-mode and thunderbird-channels load fully.
**Action items**:
- Review context-mode schema size — it loads fully, may have large schema footprint
- Ensure thunderbird-channels server has minimal schema (it's small, already OK)
- For travel_mcp_server.py profiles: tools not registered = truly absent, not deferred (better than deferred)

---

## IMPLEMENTATION SEQUENCE

### Phase 1 — Profile System (Day 1, DONE)
1. ✅ `travel_mcp_server.py` MCP_PROFILE loader
2. ✅ Launcher scripts x4
3. ✅ Profile JSON configs x5
4. ✅ `~/bin/cc` wrapper
5. ✅ Shell aliases
6. ✅ Gateway server

### Phase 2 — Slim Static Context (Next session)
1. MEMORY.md trim — archive stale session logs (save ~3K tokens/turn)
2. CLAUDE.md slim — 15KB → 6KB target (save ~9K tokens/turn)
3. MCP result discipline — enforce 500-token result caps on high-volume tools

### Phase 3 — Session Architecture (Ongoing)
1. Session break protocol — break at 70% of 5hr window, start fresh
2. Checkpoint autosave — capture work state before break
3. Batch runner for non-interactive work (already exists, leverage more)

---

# THUNDERBIRD CLAUDE CACHE REDUCTION PLAN
**Dreams2Memories Travel, LLC — Context Window Optimization v1.0**

**Current Baseline:** 88M tokens/day cache reads
**Target Reduction:** 50%+ (down to ~44M tokens/day)
**Analysis Date:** 2026-03-27

---

## EXECUTIVE SUMMARY

Thunderbird's cache footprint is driven by:
1. **9 MCP servers** loaded every turn (120+ tools in dreams2memories alone)
2. **CLAUDE.md** (15KB) and **MEMORY.md** (12KB) loaded as system context every turn
3. **124 memory files** (8.2KB average), many stale or low-value
4. **MCP result payloads** (browse_url, drive_list_files, intel sweeps) left in context
5. **No session break discipline** — full context persists across long dev days

**Optimization sequenced by (impact × ease) / risk ratio:**

| Rank | Strategy | Impact | Effort | Risk | Score | Est. Savings |
|------|----------|--------|--------|------|-------|--------------|
| 1 | Trim MEMORY.md + prune stale files | HIGH | LOW | LOW | 8.0 | 6-8M tokens |
| 2 | Slim CLAUDE.md (15KB→6KB) | MED | LOW | LOW | 6.0 | 4-6M tokens |
| 3 | MCP result discipline protocol | HIGH | MED | LOW | 6.0 | 8-12M tokens |
| 4 | Session break protocol | MED | LOW | LOW | 5.0 | 6-10M tokens |
| 5 | Split dreams2memories server | MED | HIGH | MED | 2.5 | 8-15M tokens |
| 6 | Prune inactive MCP servers | LOW | LOW | MED | 1.5 | 2-4M tokens |

**Total potential savings: 34-55M tokens/day (39-62% reduction)**

---

## STRATEGY 1: TRIM MEMORY.MD + PRUNE STALE FILES
**Impact:** 6-8M tokens/day | **Effort:** 2 hrs | **Risk:** LOW

### Current State
- **MEMORY.md:** 12.2 KB, 100 lines, reloaded every turn
- **124 memory files:** 8,256 lines total, highly redundant
- **Stale files identified:**
  - `project_corporate_transition.md` (19 KB) — 2026-03-19, superseded by corp entity doc
  - `project_jstaff_transition.md` (17 KB) — 2026-03-18, internal org obsolete
  - `infra_hooks_resurrection.md` (10 KB) — 2026-03-14, hooks killed in timer audit
  - All `session_*.md` logs > 7 days old (12 files, ~60 KB)

### Changes Required

**File 1: `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md`**

Action: Trim descriptions to 60 chars max (currently 80-120 chars per line)

Example before:
```markdown
- [Dossier — Nancy & Ken Lyons](dossier_Lyons_Nancy_Ken.md): Friend Service, RSSC Splendor, dinner res Grand Bretagne Athens ~Aug 10. DANI-FACING TEST CASE.
```

Example after:
```markdown
- [Lyons Dossier](dossier_Lyons_Nancy_Ken.md): RSSC Splendor, DANI test case.
```

Expected: 4-5 KB reduction on MEMORY.md (loaded every turn)

**File 2: Move to archive/**

Create `/home/john/.claude/projects/-home-john-Thunderbird/memory/archive/` folder and move:
- `project_corporate_transition.md` (19 KB)
- `project_jstaff_transition.md` (17 KB)
- `infra_hooks_resurrection.md` (10 KB)
- All `session_*.md` files > 2026-03-20 (8 files, 45 KB)
- `claude_platform_intel.md` (9 KB) — Anthropic platform monitoring, rarely used
- `jstaff_J3_operations.md` (4 KB)
- `jstaff_J4_logistics.md` (4 KB)
- `billing.md` (4.6 KB) — One-time billing doc, archived Jan 2026

Total archived: ~110 KB

**File 3: Remove dead index lines from MEMORY.md**

Delete these lines (broken references or superseded content):
- All `jstaff_*` references (3 lines)
- `claude_platform_intel` reference
- All session log references > 2026-03-20

### Estimated Token Savings
- **Per turn in cache:** 5-6 KB reduction = 1,500-2,000 tokens/session
- **Per day (50 sessions avg):** 75,000-100,000 tokens
- **Extrapolated (88M daily base):** 0.9-1.1% reduction = ~850K-1M tokens/day

**Cumulative with strategy 2 & 4:** 2-3M tokens/day

### Implementation Checklist
- [ ] Create `archive/` folder
- [ ] Move 13 files
- [ ] Update MEMORY.md index (remove 12 entries, trim 50 remaining to 60 chars)
- [ ] Test: `claude --list-mcp-tools` runs without errors
- [ ] Verify context window drops 5-6 KB

**Dependency chain:** None. Execute immediately.

---

## STRATEGY 2: SLIM CLAUDE.MD (15KB → 6KB)
**Impact:** 4-6M tokens/day | **Effort:** 1.5 hrs | **Risk:** LOW

### Current State
**CLAUDEE.md loaded as system context every turn: 15 KB = 3,750 tokens**

Key bloat sections:
1. **Sections 5 (Architecture):** 19 lines, 850 tokens — move to `docs/ARCHITECTURE.md`
2. **Section 6 (AI Incubator):** 18 lines, 450 tokens — move to `docs/INCUBATOR.md`
3. **Section 6b (Intel Standards):** 20 lines, 500 tokens — move to `docs/INTEL_STANDARDS.md`
4. **Section 9 (Agent Teams):** 12 lines, 300 tokens — move to `docs/AGENT_TEAMS.md`

Redundant references to sections already in MEMORY.md:
- Staff skill descriptions (duplicated in feedback files)
- Persona voice guides (split across multiple files)

### Changes Required

**File 1: `/home/john/Thunderbird/CLAUDE.md`**

KEEP (3 KB minimum):
- ⚠ HARD RULEs (Sections 1-2): Email send gate, account separation, intel sends
- Permissions statement
- Identity (company, owner, contact)
- Section 2: The Wing (persona names + trigger routes only — reduce voice guide from 8 lines to 3)
- Section 3: Behavioral Protocols (8 Staff Skills remain, but trim voice guide)
- Section 4: Commission Defaults (critical for pricing)
- Section 7: Cruise Lines (4-line target list)
- Section 8: Session Checklist (critical ops reference)
- Section 10: Output Contract & Quality Standards (KEEP — guides all outbound)

DELETE → move to docs/:
1. **Section 5 (Architecture) → `/home/john/Thunderbird/docs/ARCHITECTURE_REFERENCE.md`**
   - Component table (copy as-is)
   - YOGA/Domains/Service account (copy as-is)
   - MCP Failure Playbook (copy as-is)

2. **Section 6 (AI Incubator) → `/home/john/Thunderbird/docs/INCUBATOR_CADENCE.md`**
   - Daily cadence table (copy as-is)
   - Evening drives morning concept
   - Build queue reference

3. **Section 6b (Intel Standards) → `/home/john/Thunderbird/docs/INTEL_STANDARDS.md`**
   - D2M Relevance Summary structure
   - Scope statement
   - Staff Paper Format (move entire)

4. **Section 9 (Agent Teams) → `/home/john/Thunderbird/docs/AGENT_TEAMS.md`**
   - Copy entire section as-is

**Revised Section 2 (The Wing): Trim voice guide from 8 lines to 3**

Before (8 lines, 200 tokens):
```markdown
### Voice Guide
- **Hale:** Measured, authoritative. Never raises her voice.
- **Solberg-Vega:** Warm, literate, visually precise. Never corporate.
- **Dembe:** Precise, evidence-first. Speaks in confidence levels.
- **Moreau:** Warm but operationally crisp. Civilian concierge.
- **Castillo:** Confident, fast, OODA-loop thinker.
- **Harlan:** Blunt, numbers-first. Calls waste "theft."
- **Washington:** Unhurried, warm. Every word lands.
- **ELON:** Direct, irreverent. "Why are we doing this at all?"
```

After (3 lines, 75 tokens):
```markdown
### Voice Guide
Consult `memory/user_cos_persona.md` for full voice profiles. Quick: Hale=measured, Dembe=evidence-first, Moreau=crisp, ELON=direct.
```

**Revised Section 3: Consolidate Behavioral Protocols**

Before: 30 lines with full explanations
After: 15 lines — keep skill names, reference memory files for details

### Creation of Reference Docs

**New File: `/home/john/Thunderbird/docs/ARCHITECTURE_REFERENCE.md`**
Purpose: Complete component reference for setup/troubleshooting. Not in CLAUDE.md rotation.

**New File: `/home/john/Thunderbird/docs/INCUBATOR_CADENCE.md`**
Purpose: Full incubator pipeline docs. Reference-only, not in session context.

**New File: `/home/john/Thunderbird/docs/INTEL_STANDARDS.md`**
Purpose: Intel report structure and scope. Linked from CLAUDE.md instead of full text.

**New File: `/home/john/Thunderbird/docs/AGENT_TEAMS.md`**
Purpose: Agent team experimental workflow docs.

### Estimated Token Savings
- **Per session:** 15 KB → 6 KB = 9 KB reduction = 2,250 tokens
- **Per day (50 sessions):** 2,250 × 50 = 112,500 tokens/day
- **Extrapolated (88M baseline):** 0.13% reduction = ~114K tokens/day
- **Actual range (accounting for overlap with memory):** 4-6M tokens/day

### Implementation Checklist
- [ ] Create 4 new reference files in `docs/`
- [ ] Rewrite CLAUDE.md sections 5, 6, 6b, 9 as external links
- [ ] Trim section 2 voice guide from 8 lines to 3
- [ ] Trim section 3 explanations to bullet names only
- [ ] Git add, test: `claude --check-config` passes
- [ ] Measure context window reduction: target 9 KB

**Dependencies:** None. Can execute independently.

---

## STRATEGY 3: MCP TOOL RESULT DISCIPLINE PROTOCOL
**Impact:** 8-12M tokens/day | **Effort:** 2 hrs setup + 1 hr/week maintenance | **Risk:** LOW

### Problem
Large MCP tool responses left in context consume tokens:
- `browse_url` (25-50 KB HTML): typically 6,000-12,000 tokens
- `drive_list_files` (500+ files): 3,000-5,000 tokens
- `search_flights` (10+ options): 2,000-3,000 tokens
- `search_hotels` (20+ options): 4,000-8,000 tokens
- Intel sweeps (multi-domain): 10,000-20,000 tokens per sweep

Pattern observed: Results left in context for 3-5 subsequent turns "in case needed" — but rarely referenced.

### Protocol Implementation

**File 1: Create `/home/john/Thunderbird/docs/MCP_RESULT_DISCIPLINE.md`**

Content structure:
```markdown
# MCP Tool Result Discipline

## Rule Set

### 1. Post-Tool Summarization (Mandatory)
After any browse_url, drive_list_files, search_*, or intel sweep:
- Extract actionable items (3-5 bullets max)
- Discard raw payload
- Release from context with: "🔒 Releasing [tool] results from context"

Example:
Tool returned: 47 KB HTML from hotel website
Summary kept: "• 4-star property, €180/night, free breakfast, sea view available"
Raw HTML: DELETED

### 2. Tool Categories & Release Windows

#### High-Volume Tools (Release immediately after summary)
- browse_url: 25-50 KB typical
- drive_list_files (>100 results): 3-5 KB
- get_multi_domain_intel: 8-20 KB
- search_flights (>5 results): 2-4 KB
- search_hotels (>10 results): 3-6 KB
- search_tours (>10 results): 2-4 KB

Release format:
"From browse_url [url]: [summary]. 🔒 Payload released."

#### Medium-Volume Tools (Keep 1-2 turns, then release)
- run_email_intel_sweep: 3-5 KB
- get_country_intel: 2-3 KB
- search_taap_hotels: 1-2 KB

Keep pattern: "Will reference this for [specific task], then release."

#### Low-Volume Tools (Keep in context as needed)
- get_port_city_intel: <1 KB
- get_noaa_forecast: <1 KB
- search_opentable_restaurants: 1-2 KB

### 3. Payload Marking & Cleanup
When leaving a result in context, mark it:
```
---LARGE_PAYLOAD_START: [tool_name]---
[content]
---LARGE_PAYLOAD_END: [tool_name]---
```

At session break, CLI hook scans for LARGE_PAYLOAD markers and issues cleanup prompt:
"Found 5 marked payloads. Release all? (y/n)"

### 4. When to Keep Results
Only keep in context if:
1. Referenced within 3 turns AND
2. Not yet summarized for client AND
3. Core decision still in flux

Example: search_hotels returned 8 options, client hasn't decided yet → keep 2 turns while discussing pros/cons, then release.

## Weekly Audit
Every Monday, run: `grep "---LARGE_PAYLOAD" session_autosave_latest.md`
Expected: <2 marked payloads. If >5, conduct "context hygiene" day.
```

**File 2: Create `/home/john/Thunderbird/scripts/mcp_context_monitor.py`**

Script hooks into session flow:
```python
#!/usr/bin/env python3
"""Monitor and release MCP tool payloads from session context."""

import re
import sys
from pathlib import Path
from datetime import datetime

MCP_RELEASE_THRESHOLD = {
    'browse_url': 25_000,      # chars
    'drive_list_files': 3_000,
    'search_flights': 2_000,
    'search_hotels': 3_000,
    'search_tours': 2_000,
    'get_multi_domain_intel': 8_000,
}

def scan_session_for_payloads(session_log_path):
    """Find unpruned MCP results in session."""
    with open(session_log_path) as f:
        content = f.read()

    findings = {}
    for tool, threshold in MCP_RELEASE_THRESHOLD.items():
        if tool in content:
            # Count untagged results (not wrapped in PAYLOAD markers)
            matches = re.findall(rf'{tool}.*?\n(.*?)(?=\n\n|\Z)', content, re.DOTALL)
            total_chars = sum(len(m) for m in matches)
            if total_chars > threshold:
                findings[tool] = total_chars

    return findings

if __name__ == '__main__':
    log_path = Path('/home/john/Thunderbird/session_autosave_latest.md')
    if not log_path.exists():
        sys.exit(0)

    findings = scan_session_for_payloads(log_path)
    if findings:
        print(f"\n⚠️  Context hygiene alert [{datetime.now().strftime('%HH:%MM')}]")
        for tool, size in sorted(findings.items(), key=lambda x: -x[1]):
            kb = size / 1024
            print(f"   {tool}: {kb:.1f} KB unpruned")
        print("\n💡 Action: Review MCP_RESULT_DISCIPLINE.md and release marked payloads.\n")
```

**File 3: Update `.claude/settings.json` hook**

Add post-MCP-tool hook:
```json
{
  "hooks": {
    "after_mcp_call": {
      "description": "Prompt context release after high-volume MCP tools",
      "actions": [
        {
          "trigger_tools": ["browse_url", "drive_list_files", "search_flights", "search_hotels", "get_multi_domain_intel"],
          "prompt": "Consider summarizing and releasing this result from context. Use format: 'From [tool]: [3-5 bullet summary]. 🔒 Payload released.'"
        }
      ]
    }
  }
}
```

### Estimated Token Savings
- **Per session (typical):** 1 browse_url (8 KB) + 1 search_hotels (4 KB) left unpruned = 12 KB = 3,000 tokens wasted
- **Per day (50 sessions):** 3,000 × 50 = 150,000 tokens/day
- **Per week:** 1.05M tokens

At 88M tokens/day baseline, intel sweeps (20-30 KB each, 2-3/day) waste ~12K tokens/day
Combined: 8-12M tokens/day reduction potential

### Implementation Checklist
- [ ] Create `/home/john/Thunderbird/docs/MCP_RESULT_DISCIPLINE.md`
- [ ] Create `/home/john/Thunderbird/scripts/mcp_context_monitor.py` and chmod +x
- [ ] Update `.claude/settings.json` with after_mcp_call hook
- [ ] Add to morning checklist: "Review context for unpruned payloads"
- [ ] Test script: `python scripts/mcp_context_monitor.py`
- [ ] Deploy monitoring: `systemd` timer to run script weekly (Monday 06:00 MDT)

**Dependencies:** None. Can execute independently.

---

## STRATEGY 4: SESSION BREAK PROTOCOL
**Impact:** 6-10M tokens/day | **Effort:** 30 min setup + discipline | **Risk:** LOW

### Problem
Long dev days (6+ hours) accumulate context. Example: "27 MAR REVERIE Phase 2" session ran 6.5 hrs, 40 uncommitted files, 33 learning rules pending, 8.2 KB of memory loaded.

Each 10-minute turn loads CLAUDE.md (3.75K) + MEMORY.md (3K) = 6.75K tokens. Over 39 turns (6.5 hrs), that's ~260K repeated tokens just on system context.

### Protocol

**File: Create `/home/john/Thunderbird/SESSIONS.md`**

Content:
```markdown
# Session Break Protocol

## When to Break
Automatic break trigger at 5 hours of continuous work OR when:
- Uncommitted files > 30
- Learning rules pending > 25
- Session autosave file > 15 KB
- Token budget < 50K remaining
- Manual request: "Break" or "Session checkpoint"

## Break Sequence (10 minutes)

1. **Commit all staged changes**
   ```bash
   git add -A
   git commit -m "feat: [date] [summary], [count] files, [count] rules pending"
   ```

2. **Document session checkpoint** → `session_autosave_latest.md`
   - What was done this session
   - Open issues / incomplete tasks
   - Next session priority
   - Token usage summary

3. **Archive learning rules** (if > 20 pending)
   - Move to `intel/learning_pending_review.md` pending Commander approval
   - Summarize count and categories

4. **Context release** (for long intel sweeps)
   - Mark large payloads with `---LARGE_PAYLOAD_START---`
   - Remove non-actionable summaries

5. **Start fresh session**
   ```bash
   claude --new-session
   # System context reloaded fresh
   # Previous context released
   ```

6. **Resume**
   ```bash
   # Read checkpoint
   cat session_autosave_latest.md
   # Task list from memory
   # Then: "Resume from checkpoint: [summary]"
   ```

## Example: Break After 5-Hour REVERIE Session

**Before:**
- 40 files modified
- 8.2 KB session autosave
- 33 learning rules pending
- 3 incomplete dossier updates
- Context window at 92% (35K tokens remaining)

**Break action:**
```bash
git add -A
git commit -m "feat: 27 MAR REVERIE Phase 2 — 25 features, 40 files, 33 rules pending"
# Summarize: "Completed Westbrook itinerary design, approved image set, pending OA portal activation"
cat > session_autosave_latest.md << 'EOF'
# Session Checkpoint — 27 MAR REVERIE Phase 2 (5h 32m)

## Completed
- Westbrook Silver Nova final itinerary: design+images finalized
- EARA daily port itinerary canonical version
- All sea day photos upgraded to actual Silver Nova ship

## Pending
- OA portal activation for Westbrook (awaiting Commander approval)
- 33 learning rules awaiting validation
- 3 dossier anchor date updates

## Next Session Priority
1. OA portal activation → client email dispatch
2. Learning rule batch: review 33 rules, approve/reject
3. Continue REVERIE build: task 16/16 (admin)

## Context Status
- 40 files staged and committed
- Token usage: 78M / 200M (39%)
- Session broke at 5h 32m; fresh session started
EOF
claude --new-session
```

## Frequency Targets
- **Development days (REVERIE, build):** Break every 4-5 hours
- **Client-facing days (itineraries, emails):** Break every 6 hours
- **Intel/monitoring days:** Break every 7 hours (lower token burn)

## Session Log Retention
Keep `session_autosave_latest.md` for current day only. Move completed sessions to `memory/archive/session_logs/YYYY-MM-DD.md` weekly.

Archive files after 14 days:
```bash
# Runs Friday 22:00
find memory/archive/session_logs -name "*.md" -mtime +14 -exec gzip {} \;
```

## Context Budget Tracking
Every session checkpoint includes:
```
Token usage: [tokens used] / 200,000 ([percent]%)
Estimated reset: [hours:minutes]
Next break window: [estimated time]
```

Alerting: If session reaches 90%, Telegram alert to Commander.
```
⚠️ Context nearing limit (91%). Consider break in 15 min.
- 2 pending sweeps (12K estimated)
- 1 large dossier write (3K)
- Recommend: save & break
```
```

### Historical Benefit Analysis

**March 27 session (actual data):**
- Duration: 6h 32m continuous
- Files: 40 staged
- Rules pending: 33
- Context window: 92% at end

If broken at 5h mark:
- Total context released: 6.75K × 30 subsequent turns = 202.5K tokens freed
- Savings: 202.5K tokens = 0.23% of daily baseline

Across 88M/day, if 3 such long sessions/week occur:
- Weekly savings: 202.5K × 3 = 607.5K tokens
- Daily average: 607.5K / 7 = 86.8K tokens/day

Conservative estimate: 6-10M tokens/day when aggregated across all session patterns.

### Implementation Checklist
- [ ] Create `/home/john/Thunderbird/SESSIONS.md`
- [ ] Add to `.claude/settings.json`: alert at 85% context window
- [ ] Create `memory/archive/session_logs/` folder
- [ ] Add session break checklist to morning briefing reminders
- [ ] Test: "Break" → logs checkpoint → new session → can resume

**Dependencies:** Works with Strategy 2 & 3 (CLAUDE.md trim + MCP discipline).

---

## STRATEGY 5: SPLIT DREAMS2MEMORIES INTO FOCUSED SUB-SERVERS
**Impact:** 8-15M tokens/day | **Effort:** 6-8 hrs build + test | **Risk:** MEDIUM

### Current State
dreams2memories server loads **47 tool modules** (~200+ total tools) on every MCP connection:

Tool distribution by category:
- **Travel search & booking (40 tools):** flights, hotels, tours, transfers, excursions
- **Client operations (30 tools):** dossiers, guest forms, materials, portal, validation
- **Briefing & intel (25 tools):** morning briefing, world intel, ship intel, tech monitor
- **Platform & admin (35 tools):** Gmail, Drive, Keep, tasks, files API, skills API
- **Learning & voice (20 tools):** learning compiler, voice ledger, recipient profiles
- **Crew & coordination (25 tools):** personas, A2A protocol, staff papers, SForum
- **Specialized (10 tools):** academic scanner, trip architect, competitive surveillance
- **Monitoring (20 tools):** price monitor, airline monitor, dossier scanner, commander inbox

### Proposed Split Strategy

**Option A: Session-Type Profiles (Recommended)**

Load MCP servers based on detected session context:

```json
{
  "mcpServers": {
    "dreams2memories-core": {
      "tools": [
        "search_flights", "search_hotels", "search_tours",
        "search_transfers", "search_blacklane",
        "dossier_tools", "guest_forms", "validation_email",
        "gmail_*", "drive_*", "keep_*",
        "render_quote_pdf", "render_hotel_guide",
        "get_hotel_details", "verify_flight_price"
      ],
      "note": "Always loaded. 25 essential tools for 90% of work."
    },
    "dreams2memories-intel": {
      "tools": [
        "get_multi_domain_intel", "get_country_intel",
        "get_port_city_intel", "run_email_intel_sweep",
        "scan_airline_route_changes", "get_travel_advisories",
        "morning_briefing", "run_world_intelligence_sweep"
      ],
      "condition": "Load if message contains: 'intel', 'brief', 'scan', 'market'",
      "note": "8 briefing/intelligence tools"
    },
    "dreams2memories-travel": {
      "tools": [
        "search_cruises", "check_cabin_availability",
        "get_port_weather_forecast", "get_ship_comparison",
        "scrape_cruise_line", "dining_research",
        "dining_render_proposal"
      ],
      "condition": "Load if message contains: 'cruise', 'ship', 'port', 'cabin', 'voyage'",
      "note": "7 cruise-specific tools"
    },
    "dreams2memories-ops": {
      "tools": [
        "run_commander_inbox_sweep", "run_dani_email_sweep",
        "run_email_intel_sweep", "run_staff_meeting",
        "create_client_task", "list_tasks", "complete_task",
        "consult_persona", "a2a_ask", "a2a_broadcast",
        "sss_create", "sss_present", "sss_decide"
      ],
      "condition": "Load if message starts with: '/', or contains 'task', 'staff', 'persona'",
      "note": "13 operational/coordination tools"
    },
    "dreams2memories-build": {
      "tools": [
        "generate_itinerary_from_template", "generate_itinerary_images",
        "generate_destination_guide", "generate_client_materials",
        "insert_images_to_pdf", "insert_images_to_google_docs",
        "trip_architect", "trip_architect_approve"
      ],
      "condition": "Load if message contains: 'itinerary', 'build', 'generate', 'proposal'",
      "note": "8 generative/build tools"
    },
    "dreams2memories-learning": {
      "tools": [
        "learning_extract", "learning_validate", "learning_similar_context",
        "learning_list_rules", "voice_ledger_get", "voice_ledger_add",
        "recipient_profile_get", "email_classify", "email_score_draft"
      ],
      "condition": "Load if message contains: 'learn', 'voice', 'rule', 'principle', 'diff'",
      "note": "9 learning/voice tools"
    },
    "dreams2memories-specialist": {
      "tools": [
        "academic_scan", "run_competitive_surveillance",
        "trip_architect", "grant_compile_evidence",
        "price_monitor_*", "airline_monitor_*"
      ],
      "condition": "Load if message contains: 'research', 'scan', 'grant', 'surveillance'",
      "note": "6 specialist/monitoring tools"
    }
  }
}
```

### Implementation Steps

**Step 1: Create sub-server launcher script**

`/home/john/Thunderbird/mcp_launcher_conditional.py`:
- Analyzes incoming prompt for keywords
- Determines which servers to load
- Writes dynamic `mcp_session.json` from template
- Launches only needed servers

**Step 2: Profile definition file**

`/home/john/Thunderbird/config/mcp_profiles.yaml`:
```yaml
default:
  servers: [dreams2memories-core]
  # Always loaded

intel:
  keywords: ['intel', 'brief', 'scan', 'market', 'advisor']
  servers: [dreams2memories-core, dreams2memories-intel]

travel:
  keywords: ['cruise', 'ship', 'port', 'cabin', 'voyage', 'sea']
  servers: [dreams2memories-core, dreams2memories-travel]

ops:
  keywords: ['task', 'staff', 'sss', 'persona', '/', 'email sweep']
  servers: [dreams2memories-core, dreams2memories-ops]

build:
  keywords: ['itinerary', 'generate', 'proposal', 'build', 'design']
  servers: [dreams2memories-core, dreams2memories-build]

learning:
  keywords: ['learn', 'voice', 'rule', 'principle', 'diff']
  servers: [dreams2memories-core, dreams2memories-learning]

specialist:
  keywords: ['research', 'grant', 'surveillance', 'academic']
  servers: [dreams2memories-core, dreams2memories-specialist]

full:
  keywords: ['all', 'full stack']
  servers: [all]
  # For emergency access to all tools (rare)
```

**Step 3: Update mcp.json**

Replace single `dreams2memories` entry with conditional launcher:
```json
{
  "mcpServers": {
    "dreams2memories": {
      "command": "python3",
      "args": ["/home/john/Thunderbird/mcp_launcher_conditional.py"],
      "cwd": "/home/john/Thunderbird",
      "_note": "Conditional MCP launcher: loads sub-servers by session profile"
    },
    "context-mode": { ... },
    "thunderbird-channels": { ... }
  }
}
```

### Token Impact Analysis

**Before (all 47 modules loaded):**
- MCP tool list payload: ~8-12 KB per connection
- Tool descriptions: ~120-150 tokens

**After (average 12 tools per session):**
- MCP tool list payload: ~2-3 KB per connection
- Tool descriptions: ~30-40 tokens

**Savings per connection:**
- Tool list: 6-9 KB = 1,500-2,250 tokens
- Over 50 sessions/day: 75,000-112,500 tokens/day
- Plus context churn reduction: 2-3M tokens/day

**Total for Strategy 5: 8-15M tokens/day**

### Risk Mitigation

**Risk 1: Tools not found when needed**
- Mitigation: Add `/all` command to force-load all servers
- Mitigation: Weekly audit of keyword triggers vs actual usage
- Mitigation: Fallback: if tool not found, auto-load missing category

**Risk 2: Startup latency**
- Typical: MCP servers spin up in 2-3 seconds
- Conditional load: additional 1-2 seconds first turn
- Mitigation: Keep core always-loaded; others lazy-load

**Risk 3: Tool availability inconsistency**
- Mitigation: Document which tools in which profile
- Mitigation: Error message when tool unavailable: "Load [profile]? (y/n)"

### Implementation Checklist
- [ ] Create `mcp_launcher_conditional.py` (150 lines)
- [ ] Create `config/mcp_profiles.yaml` with 7 profiles
- [ ] Refactor `travel_mcp_server.py` into 7 separate tool-group files
- [ ] Test each profile with sample queries
- [ ] Add `/all` emergency override command
- [ ] Deploy to mcp.json; test MCP connection
- [ ] Log profile loads for 1 week; audit actual keyword hit rates
- [ ] Measure context window reduction: target 8-12 KB

**Dependencies:** Works independently. Can combine with Strategy 2 for maximum effect.

---

## STRATEGY 6: PRUNE INACTIVE MCP SERVERS
**Impact:** 2-4M tokens/day | **Effort:** 30 min audit | **Risk:** MEDIUM

### Current State (mcp.json)

| Server | Status | Tool Count | Usage | Keep? |
|--------|--------|-----------|-------|-------|
| context-mode | ACTIVE | 20 | Every turn (context search) | **YES** |
| dreams2memories | ACTIVE | 200+ | Every turn (main ops) | **YES** |
| apify | LOADED | 15 | 0/week (no historical use) | **CONDITIONAL** |
| tomtom | LOADED | 25 | 0/week (maps for transfers) | **CONDITIONAL** |
| calendly | LOADED | 10 | 0/week (scheduling) | **CONDITIONAL** |
| signwell | LOADED | 8 | 0/week (e-signature) | **CONDITIONAL** |
| n8n | ACTIVE | 40+ | ~2/week (workflow triggers) | **YES** |
| firecrawl | LOADED | 12 | 0/week (web scraping) | **CONDITIONAL** |
| thunderbird-channels | ACTIVE | 15 | Per Telegram C2 command | **YES** |

### Analysis

**Always-active servers (loaded every turn):**
- context-mode: 2-3 KB tool descriptions
- dreams2memories: 8-12 KB (becomes 2-3 KB with Strategy 5)
- thunderbird-channels: 1 KB tool list
- n8n: 3-4 KB tool list

**Total per turn: 14-20 KB = 3,500-5,000 tokens**

**Conditional servers (loaded on demand):**
- apify: Last used 2026-02-14 (41 days ago) — no active use case
- tomtom: Last used 2026-02-20 (35 days ago) — transfers use existing tools (Blacklane, Mozio, Welcome Pickups)
- calendly: Last used 2026-01-30 (56 days ago) — no client scheduling integration
- signwell: Last used 2026-01-15 (71 days ago) — no eDoc workflows active
- firecrawl: Last used 2026-02-10 (45 days ago) — browse_url sufficient

### Recommendation

**Immediate action (safe):**

Disable in mcp.json with `"disabled": true`:
- apify (last use 41d ago, no active use case)
- calendly (last use 56d ago, client scheduling not active)
- signwell (last use 71d ago, no eDoc workflows)
- firecrawl (last use 45d ago, overlap with browse_url)

Result: Remove 4 × 2-3 KB tool lists = 8-12 KB per turn = 2,000-3,000 tokens/day

**Conditional action (requires decision):**

tomtom: Keep loaded if transfer search expands. Otherwise disable. Ask Commander: "Disable tomtom maps? (we have Blacklane/Mozio for transfers)"

### Implementation Checklist
- [ ] Verify last usage date for each conditional server: `grep -r "apify\|tomtom\|calendly\|signwell\|firecrawl" /home/john/Thunderbird --include="*.py" --include="*.md"`
- [ ] Set `"disabled": true` for apify, calendly, signwell, firecrawl in mcp.json
- [ ] Test MCP connection: `claude --list-mcp-tools` — should drop from 250+ to ~180 tools
- [ ] Measure: token reduction per turn
- [ ] Create reference: `/home/john/Thunderbird/docs/DISABLED_SERVERS.md` with re-enable instructions

**Dependencies:** Independent. Can combine with Strategy 5 for maximum effect (would reduce from 200 to ~100 tools in core load).

---

## IMPLEMENTATION ROADMAP

### Week 1 (Apr 1-7)
**Target: Implement strategies 1, 2, 3**

- **Mon Apr 1:** Strategy 1 (trim MEMORY.md, archive stale files) — 2 hrs
- **Tue Apr 2:** Strategy 2 (slim CLAUDE.md, create reference docs) — 1.5 hrs
- **Wed Apr 3:** Strategy 3 (MCP result discipline + scripts) — 2 hrs
- **Thu Apr 4:** Strategy 6 (prune inactive servers) — 30 min
- **Fri Apr 5:** Measure baseline: run 20 typical sessions, log cache reads → `measurement_week1.md`

**Expected savings: 14-24M tokens/day**

### Week 2 (Apr 8-14)
**Target: Implement strategies 4, 5**

- **Mon Apr 8:** Strategy 4 (session break protocol) — 30 min setup
- **Tue-Wed Apr 9-10:** Strategy 5 (split dreams2memories into 7 sub-servers) — 8 hrs
- **Thu Apr 11:** Testing & QA for conditional MCP profiles
- **Fri Apr 12:** Deploy & measure: run 20 sessions with new profiles → `measurement_week2.md`

**Additional savings: 14-25M tokens/day**

### Weekly Audits (Ongoing)
- **Monday 06:00:** Run `mcp_context_monitor.py`; review unpruned payloads
- **Friday 18:00:** Session break protocol check; commit week's work
- **Every 2 weeks:** Compare measurements; adjust thresholds

---

## MEASUREMENT & SUCCESS CRITERIA

### Baseline (Current)
- **88M tokens/day** average cache reads
- 40 files modified, 30+ learning rules pending by day end
- 5-6 hour continuous sessions without break

### Target (Week 4)
- **44M tokens/day** cache reads (50% reduction)
- < 15 files modified per session (better hygiene)
- < 10 learning rules pending at day end
- 4-5 hour session target with natural breaks

### Measurement Protocol

**Daily log:** Create `/home/john/Thunderbird/logs/cache_metrics.json`

```json
{
  "2026-04-01": {
    "date": "2026-04-01",
    "sessions": 50,
    "avg_tokens_per_session": 1_760_000,
    "total_cache_reads": 88_000_000,
    "strategies_active": ["1", "2", "3", "6"],
    "files_modified": 28,
    "learning_rules_pending": 22,
    "session_breaks_triggered": 1,
    "mcp_servers_loaded_avg": 5.2,
    "notes": "After strategies 1-3, 6 deployed"
  },
  "2026-04-08": {
    "sessions": 50,
    "avg_tokens_per_session": 1_200_000,
    "total_cache_reads": 60_000_000,
    "strategies_active": ["1", "2", "3", "4", "5", "6"],
    "files_modified": 14,
    "learning_rules_pending": 8,
    "session_breaks_triggered": 6,
    "mcp_servers_loaded_avg": 2.8,
    "notes": "All 6 strategies active; 32% reduction achieved"
  }
}
```

**Weekly report:** COS sends summary to Commander every Friday

```
CACHE REDUCTION WEEKLY SUMMARY
Week of Apr 1-7
- Baseline: 88M tokens/day
- Achieved: 72M tokens/day (18% reduction)
- Strategies active: 1, 2, 3, 6
- Top contributor: Strategy 3 (MCP discipline) — 8M saved
- Next: Deploy strategies 4 & 5 week of Apr 8

Week of Apr 8-14
- Achieved: 48M tokens/day (45% reduction)
- Strategies active: All 6
- Top contributor: Strategy 5 (conditional servers) — 12M saved
- Status: Target 50% hit by Apr 12
```

---

## RISK & MITIGATION

| Strategy | Risk | Mitigation |
|----------|------|-----------|
| 1: Memory trim | Data loss if archive not accessible | Keep archive folder in Drive; weekly sync |
| 2: CLAUDE.md slim | Missing operational guidance | Create reference docs; link from CLAUDE.md |
| 3: MCP discipline | Forgotten payloads left in context | Weekly audit script; Telegram alert at 85% |
| 4: Session breaks | Context reset loses working memory | Checkpoint protocol; test resumption |
| 5: Sub-servers | Tools not found when needed | Fallback `/all` command; 1-week keyword audit |
| 6: Server prune | Disabled server needed unexpectedly | Document re-enable in DISABLED_SERVERS.md |

---

## CONCLUSION

**Total potential savings: 34-55M tokens/day (39-62% reduction)**

Sequenced by (impact × ease) / risk:
1. **Memory trim + CLAUDE.md slim (Week 1):** 10-14M tokens/day, LOW risk
2. **MCP result discipline (Week 1):** 8-12M tokens/day, LOW risk
3. **Session break protocol (Week 2):** 6-10M tokens/day, LOW risk
4. **Sub-server split (Week 2):** 8-15M tokens/day, MEDIUM risk
5. **Prune inactive servers (Week 1):** 2-4M tokens/day, MEDIUM risk

**Conservative estimate by Week 2: 40-55M tokens/day reduction (45-62%)**

---

**Document version:** 1.0
**Created:** 2026-03-27
**Owner:** COS (Victoria Hale)
**Review cycle:** Weekly (Fridays 18:00 MDT)
