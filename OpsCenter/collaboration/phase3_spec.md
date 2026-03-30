# PHASE 3 SPEC — D2M THUNDERBIRD WING
# Date: 2026-03-30 | Author: Claude Sonnet 4.6
# Basis: architectural_decisions.md (all decisions Commander-approved)
# Prerequisites: Phase 1 complete, Phase 2 stable, dependency audit clean
# Status: AWAITING COMMANDER APPROVAL

---

## PHASE 3 OBJECTIVES

1. SSE/HTTP migration — full MCP tool access from mobile
2. ADK evaluation — Goose-side orchestration upgrade
3. CrewAI evaluation — autonomous workflow assessment
4. LangGraph evaluation — stateful pipeline assessment
5. Routing data analysis — 90-day blackboard optimization
6. Session checkpoint — formalize and automate

---

## ITEM 1: SSE/HTTP MIGRATION OF D2M-COMMAND-HUB

### Goal
Commander accesses all 140+ MCP tools from mobile (Android/Claude.ai)
without manual intervention on YOGA.

### Current State
D2M-COMMAND-HUB runs stdio transport — local process only.
Unreachable from mobile or any remote client.
Cloudflare tunnel exists at api.d2mluxury.quest — natural ingress point.

### Architecture
```
Mobile (Claude.ai) → Cloudflare tunnel (api.d2mluxury.quest)
                           ↓
                   Auth layer (token validation)
                           ↓
                   D2M-COMMAND-HUB (SSE/HTTP transport)
                           ↓
                   140+ MCP tools on YOGA
```

### Implementation Steps

1. Convert D2M-COMMAND-HUB from stdio to SSE/HTTP transport
   - MCP Python SDK supports SSE natively via mcp[cli] — already in venv
   - Change server startup from stdio_server() to sse_server()
   - Bind to localhost:8765 (already used by MCP HTTP bridge in task_processor.py)

2. Add authentication layer
   - Bearer token validation on every MCP request
   - Token stored in .env — never hardcoded
   - Reverie API (already built) is the natural auth proxy candidate
   - Option A: Reverie proxies MCP calls with auth (cleanest — mobile talks to Reverie)
   - Option B: Direct token auth on MCP server (simpler — fewer hops)
   - DECISION REQUIRED: Option A or B

3. Cloudflare tunnel configuration
   - Add MCP endpoint route to existing tunnel config
   - Separate subdomain recommended: mcp.d2mluxury.quest
   - TLS handled by Cloudflare — no cert management on YOGA

4. Mobile trigger protocol
   - Claude.ai on Android connects to mcp.d2mluxury.quest
   - Auth token passed as Bearer header
   - All 140+ tools available identically to desktop

### Security Requirements
- Auth token rotation procedure documented
- Rate limiting on MCP endpoint (prevent abuse if token leaked)
- Audit log of all remote MCP calls (append to OpsCenter log)
- Fallback: if SSE endpoint unreachable, graceful error to Commander

### Risks
- websockets 15.0.1 compatibility with SSE transport — TEST FIRST
- Exposing MCP tools to internet increases attack surface — auth is non-negotiable
- YOGA must be running and tunnel active for mobile access — single point of failure

---

## ITEM 2: ADK EVALUATION

### Goal
Determine if Google ADK improves Goose-side orchestration vs. current custom Python.

### Installed
google-adk==1.28.0 in Thunderbird venv — ready for evaluation.

### Test Case: World Intel Sweep
Take thunderbird_overwatch.py world intel sweep — current multi-step pipeline —
and re-implement orchestration layer using ADK AgentTeam API.

### Evaluation Criteria
1. Setup effort — how much code replaced vs. written
2. MCP tool compatibility — do Thunderbird MCP tools register cleanly in ADK
3. Failure handling — does ADK recover from a bad data source gracefully
4. Output quality — same or better than current implementation
5. Dependency footprint — ADK brought in 40+ new packages; worth it?

### Pass Criteria
ADK version requires less custom orchestration code AND handles partial
pipeline failures more gracefully than current implementation.
MCP tools register without significant adaptation work.

### Do NOT use ADK[extensions] or ADK[eval] until LiteLLM supply chain
review complete (BerriAI/Mandiant — no completion date yet).

---

## ITEM 3: CREWAI EVALUATION

### Goal
Determine if CrewAI autonomous agent delegation reduces Commander trigger steps
for multi-leg workflows.

### Hypothesis
CrewAI adds value only if you want agents assigning tasks to each other without
Commander routing. Given Goose = Commander (Decision 6), this may be redundant.

### Test Case: Research-to-Client-Output Pipeline
Current: Commander triggers Goose (research) → Commander triggers Claude (synthesis)
         → Commander triggers Claude (client output) — 3 manual triggers

CrewAI version: Commander triggers crew once → Goose researches → Claude synthesizes
                → Claude produces client draft — 1 trigger, 0 Commander steps between

### Pass Criteria
1. Zero Commander intervention between research and final draft
2. Output quality equivalent to manual 3-trigger process
3. Graceful recovery when one agent step produces bad output
4. Does NOT require Commander to stay engaged during execution

### Likely Verdict (pre-evaluation assessment)
Low probability of passing criteria 3 — CrewAI error recovery is immature.
Evaluate anyway to confirm. If it fails, document why and close the question.

---

## ITEM 4: LANGGRAPH EVALUATION

### Goal
Determine if LangGraph stateful graph orchestration improves Thunderbird
intel pipeline reliability vs. current linear Python implementation.

### Relevant Problem
Current intel pipelines (morning brief, world intel sweep) are linear sequences.
A single bad data source can degrade or abort the entire run.
LangGraph would model each source as a node with conditional edges for failure.

### Test Case: Morning Briefing Pipeline
Re-implement thunderbird_morning_briefing.py using LangGraph.
Deliberately inject a failure at one node — does LangGraph skip and continue
or abort like the current implementation?

### Pass Criteria
1. LangGraph version handles deliberate mid-pipeline failure more gracefully
2. Adding a new data source requires less code change than current approach
3. Observability improvement — can see exactly where pipeline stalled

### Skip Criteria
If current morning brief pipeline has zero partial-failure aborts over
Phase 2 duration — LangGraph complexity is not justified. Skip it.

---

## ITEM 5: ROUTING DATA ANALYSIS (90-DAY REVIEW)

### Goal
Use routing_log.md data to optimize model routing rules based on reality,
not assumptions.

### Analysis Questions
1. Is Claude budget consistently GREEN or YELLOW by 0600 MT?
   → If RED: routing rules too aggressive with Claude, tighten further
   → If always GREEN: budget guard may be over-restrictive, loosen

2. Which task types have highest Claude override rate (/use claude)?
   → High override = routing rule is wrong for that task type, fix the table

3. Is Deepseek arbitration being invoked?
   → Zero entries in conflict_log.md = either system working or nobody logging
   → Investigate which before concluding

4. Goose-first/Claude-finish handoff rate
   → What % of Goose drafts required Claude finish pass?
   → If < 20%: Claude finish may be unnecessary overhead for most tasks

### Output
Updated routing_rules.md with data-driven adjustments.
Revised capability routing table in blackboard_detailed_plan.md.

---

## ITEM 6: SESSION CHECKPOINT — FORMALIZE AND AUTOMATE

### Goal
Claude auto-writes a session checkpoint at end of every session so context
is never lost across Claude Code / Desktop / mobile transitions.

### File
~/Thunderbird/OpsCenter/session_checkpoint_latest.md
Single rolling file — overwritten each session (not appended).

### Schema

```
# SESSION CHECKPOINT
written_at: [ISO timestamp MT]
written_by: Claude Sonnet 4.6
session_type: Claude Code | Claude Desktop | Claude.ai

## WHAT WAS WORKED ON
[2-3 sentences — tasks completed this session]

## DECISIONS MADE
[bullet list — any Commander decisions or standing orders changed]

## OPEN ITEMS
[bullet list — tasks started but not finished, things pending Commander action]

## BLACKBOARD STATE
claude_budget: GREEN | YELLOW | RED
active_tasks: [count and brief description]
last_deepseek_ruling: [task_id or NONE]

## NEXT SESSION PRIORITIES
[ordered list — what should be tackled first next session]

## FILES MODIFIED THIS SESSION
[list of files written or changed]
```

### Trigger
Claude writes checkpoint as final action before ending any session.
Commander pastes checkpoint content at start of next session for context restore.
Hale reads checkpoint at morning brief and includes open items in daily summary.

---

## PHASE 3 EXECUTION ORDER

Sequenced by risk and dependency:

1. Session checkpoint — zero risk, immediate value, implement first
2. Routing data analysis — passive, runs on Phase 2 data, no code needed
3. SSE/HTTP migration — highest value, moderate risk, needs auth design decision
4. ADK evaluation — low risk (already installed), needs test case execution
5. LangGraph evaluation — conditional on intel pipeline failure data from Phase 2
6. CrewAI evaluation — lowest priority, likely to be skipped based on assessment

---

## OPEN DECISIONS REQUIRED BEFORE SSE WORK BEGINS

Commander must decide:

DECISION A: Auth architecture for SSE endpoint
  Option A — Reverie proxies MCP (mobile → Reverie → MCP)
    Pro: Reverie already has auth scaffolding, single auth surface
    Con: Extra hop, Reverie must be running on Hetzner
  Option B — Direct token auth on MCP server (mobile → MCP directly)
    Pro: Simpler, fewer moving parts, no Hetzner dependency
    Con: Auth logic lives in MCP server code, harder to rotate tokens

DECISION B: Fallback behavior when YOGA is offline
  Option A — Hard fail with clear error message to Commander
  Option B — Graceful degradation to cloud-only tools (Drive, Gmail via cloud MCP)
  Option C — Telegram alert to Commander that YOGA is unreachable

---
*Phase 3 spec complete. Awaiting Commander approval and Decision A + B answers.*

## OPEN DECISIONS — RESOLVED (2026-03-30)

### Decision A: SSE Auth Architecture
Decision: TAILSCALE IS THE AUTH LAYER
Rationale: Commander already runs Tailscale — YOGA is reachable from any
Commander device via private Tailscale network. No additional auth needed
on the MCP server itself. Tailscale handles identity and encryption.
Architecture change: NONE to current stack.
MCP server binds to Tailscale IP (not public internet).
Cloudflare tunnel NOT used for MCP — Tailscale only.
Result: Mobile (on Tailscale) → YOGA MCP directly. Zero new auth code.

### Decision B: YOGA Uptime / Offline Fallback
Context: Commander departs for Japan + Pacific April 10 — May 11, 2026.
YOGA must stay online unattended for 31 days.
Priority: Engineer for uptime, not fallback.
Fallback (last resort only): Telegram alert if YOGA goes unreachable.
Graceful degradation to cloud-only tools is NOT a goal — full MCP or nothing.

### SSE Architecture — Revised (simpler than originally spec'd)
```
Mobile Claude.ai (on Tailscale)
         ↓
  YOGA Tailscale IP:8765
         ↓
  D2M-COMMAND-HUB (SSE/HTTP transport)
         ↓
  140+ MCP tools
```
No Cloudflare. No Reverie proxy. No token auth. Tailscale handles it all.
This is the minimum-disruption path Commander requested.

## REVISED PHASE 3 PRIORITY ORDER — APRIL 10 DEPARTURE CONSTRAINT

Commander departs Japan + Pacific: April 10 — May 11, 2026 (31 days unattended)
Days remaining before departure: ~11

REVISED EXECUTION ORDER:
1. WATCHDOG HARDENING — before anything else (YOGA must survive 31 days alone)
2. SSE/HTTP MIGRATION — critical, must be tested before April 10
3. SESSION CHECKPOINT — low effort, high value for Japan ops
4. ADK EVALUATION — if time permits before April 10, else post-return
5. ROUTING DATA ANALYSIS — passive, runs itself during Japan trip
6. LANGGRAPH EVALUATION — post-return
7. CREWAI EVALUATION — post-return, lowest priority

---

## WATCHDOG HARDENING SPEC (NEW — HIGHEST PRIORITY)

### Current State
thunderbird-overwatch systemd service exists.
thunderbird-telegram-c2 systemd service exists.
Unknown: restart policies, failure recovery, alert behavior.

### Required Before April 10
1. Verify both services have restart=always or restart=on-failure in unit files
2. Verify RestartSec is set (recommended: 10s — fast enough, not hammering)
3. Verify WatchdogSec is set for process hang detection (not just crash)
4. Add StartLimitIntervalSec + StartLimitBurst to prevent restart storms
5. Telegram alert on service restart — Commander knows something happened
6. Daily heartbeat Telegram message — "YOGA alive, all services green"
7. Test: deliberately kill each service, verify restart and Telegram alert fires

### Unit File Target Config (both services)
```
[Service]
Restart=on-failure
RestartSec=10s
WatchdogSec=60s
StartLimitIntervalSec=300
StartLimitBurst=5
```

### Additional YOGA Stability Items
- Verify no pending OS updates that could auto-restart YOGA
- Verify swap is configured (OOM killer won't take down services)
- Verify disk space — 31 days of logs could fill disk
- Set up log rotation if not already active (Goose completed G3 — verify still working)
- UPS or power strip with surge protection — physical layer

---

## SSE MIGRATION SPEC — TAILSCALE ARCHITECTURE

### Auth: Tailscale only
No additional auth code. MCP server binds to Tailscale IP.
Only devices on Commander's Tailscale network can reach it.

### Implementation Steps (before April 10)
1. Check current D2M-COMMAND-HUB server startup code — identify stdio calls
2. Add SSE transport option alongside existing stdio (not replacing — both modes)
3. Bind SSE server to Tailscale IP on port 8766 (8765 already used by HTTP bridge)
4. Test from mobile on Tailscale — verify all 140+ tools reachable
5. Add to systemd as third service: thunderbird-mcp-sse
6. Verify watchdog config applied to new service before departure

### Why port 8766 not 8765
8765 = existing MCP HTTP bridge used by task_processor.py — do not disturb.
8766 = new SSE endpoint for mobile access — clean separation.

---
*Updated 2026-03-30. April 10 is the hard deadline.*
