# SWITCHBLADE ANALYSIS — DIRECT-INTELLIGENCE PIPELINE (DIP)
## Thunderbird Wing · OpsCenter · 2026-03-30
**Analyst:** Claude Sonnet (A5-adjacent strategic review)
**Task ID:** GT-20260330-2236-STRA
**Classification:** INTERNAL — COMMANDER REVIEW

---

## EXECUTIVE SUMMARY

The DIP architecture is **conditionally viable** for intel-only workloads. Its core trade — blackboard oversight for latency/cost efficiency — is sound, but the current proposal has **three critical failure modes** that could produce runaway token spend, stale shared state, or scope creep into client-facing pipelines. A Dead-Man's Switch (DMS) design is proposed at the end of this document.

---

## PART 1 — FAILURE MODE INVENTORY

### FM-1: Blackboard Desync (SEVERITY: HIGH)

**What happens:** DIP executes `Search → Parse → Synthesize → Publish` and writes directly to `/intel/` without posting a task entry to the blackboard. The blackboard shows `Active tasks: 0` while DIP is actively running.

**Consequence:** COS sweeps or Goose's next cycle see no running task and re-dispatch the same intel job. Two DIP instances race to write to `/intel/`, producing duplicate or overwritten output. The routing_log has no record of what ran.

**Trigger condition:** Any restart of the orchestration cycle while DIP is mid-run.

---

### FM-2: Safe-CLI Gate as Single Point of Failure (SEVERITY: HIGH)

**What happens:** The entire safety model is `safe_cli_gate.py`. The fallback on gate crash is "disable all mcp2cli access until human override." This is correct fail-safe behavior — but it also means DIP has **no graceful degradation path** back to blackboard-mediated flow.

**Consequence:** Gate crash = total intel pipeline stoppage, no partial results, no Commander alert unless the gate itself sends the Telegram alert before dying. If the gate crashes mid-execution (after tool call, before publish), the partial result is orphaned in memory with no record in `star_protocol_log.csv` or the blackboard.

**Secondary risk:** The gate validates syntax and whitelist, but not **semantic intent**. A valid-schema manifest with a crafted parameter string that passes regex could invoke a tool with unintended scope (e.g., `search_hotels` with a client name embedded, routing PII to a non-PII-safe tool chain).

---

### FM-3: Token Runaway — No Circuit Breaker (SEVERITY: HIGH)

**What happens:** The proposal claims lower token usage but specifies no hard cap. The synthesis step (Step 3) is an unconstrained LLM call.

**Consequence:** If the orchestrator re-queues stale tasks (e.g., because `/intel/` output is missing due to FM-1 race condition), or if the synthesis LLM is called iteratively on the same input, token spend compounds without limit. Current budget state is Claude YELLOW — this is an existential risk to the session.

**Trigger condition:** Any retry logic in `dossier_intelligence_bot.py` without an exit condition.

---

### FM-4: Hallucinated Tool Parameters Passing the Gate (SEVERITY: MEDIUM)

**What happens:** The synthesis LLM (Step 3) may hallucinate structured output that becomes input for a downstream tool call. The safe_cli_gate.py does regex/whitelist checks but does not validate whether tool parameters are *semantically plausible*.

**Example:** LLM synthesis produces a `search_flights` call with a fabricated booking reference. The gate sees a valid JSON manifest with a whitelisted tool name. It executes. The tool call fails with an API error, but the error is logged, not surfaced — and the orchestrator may retry.

**Consequence:** Cascading failed tool calls, each consuming tokens and API quota, all passing the gate silently.

---

### FM-5: Star Protocol Log Divergence (SEVERITY: MEDIUM)

**What happens:** DIP logs tool calls to `star_protocol_log.csv` via the Safe-CLI gate. However, the star protocol is currently **DISABLED** (Timer Audit SO — disabled due to token burn risk). The log destination may not be actively monitored or processed.

**Consequence:** Audit trail exists on disk but is not surfaced to Commander. DIP runs are invisible to the normal oversight layer. If a bad run occurs, forensic reconstruction requires reading raw CSV rather than a live dashboard.

---

### FM-6: Scope Creep Into Client-Facing Pipelines (SEVERITY: MEDIUM)

**What happens:** DIP is designed for intel. But the orchestrator (`dossier_intelligence_bot.py`) has "dossier" in its name. If scope drifts — or if a future task type is added without updating the policy engine — DIP could write to `dossiers/` or `output/` directories.

**Consequence:** Client-facing content bypasses WF-17. Commander reviews output that has already been published. This violates Standing Order: client products require draft approval flow.

**Note:** This is not a current risk — it's a future risk that requires a hard guard now, before it becomes one.

---

### FM-7: PII Fence Breach at Synthesis Layer (SEVERITY: MEDIUM)

**What happens:** The synthesis LLM call receives parsed JSON from tool results. If any tool result contains client names, booking numbers, or email addresses (e.g., from a dossier-adjacent intel scan), and that context is passed to Groq for synthesis, the PII fence is violated.

**Consequence:** Client PII on Groq — standing directive violation. No current filter is described in the DIP proposal.

---

### FM-8: No Rollback / Retraction Mechanism (SEVERITY: LOW-MEDIUM)

**What happens:** Once DIP publishes to `/intel/`, downstream consumers (morning brief pipeline, blackboard sync) may read the output before Commander can review.

**Consequence:** A hallucinated or incorrect recommendation propagates to Commander and potentially into client communications before the error is caught.

---

## PART 2 — BLACKBOARD BYPASS RISK ASSESSMENT

The blackboard serves two architectural functions that DIP eliminates:

| Function | Blackboard (Current) | DIP (Proposed) |
|---|---|---|
| **Shared State** | All agents see active tasks | Blind — no task registration |
| **Commander Oversight Hook** | All task flow visible in routing_log | Invisible until `/intel/` publish |
| **Deduplication** | Blackboard prevents double-dispatch | No guard |
| **Budget Awareness** | Budget status read before dispatch | Not integrated |

**Verdict:** The bypass is acceptable for low-risk intel tasks **if and only if** DIP registers task state to the blackboard at START and COMPLETE, and checks budget status before initiating a synthesis call. The blackboard doesn't need to *mediate* the execution — it just needs to *know* about it.

The Safe-CLI gate is the strongest existing control in this architecture. The proposal correctly makes it the choke point for all mcp2cli access. The analysis recommends extending that gate — not replacing the blackboard model entirely.

---

## PART 3 — DEAD-MAN'S SWITCH DESIGN

The following DMS controls are recommended. They are listed in implementation priority order.

---

### DMS-1: Blackboard Heartbeat Registration (P0 — REQUIRED)

DIP must write to the blackboard at task lifecycle boundaries:
- **START:** `Active tasks: +1 | DIP-{task_id} running | started: {timestamp}`
- **COMPLETE:** `Active tasks: -1 | DIP-{task_id} done | published: {output_path}`
- **ABORT:** `Active tasks: -1 | DIP-{task_id} ABORTED | reason: {error}`

This costs ~100 tokens (file write, no LLM call) and eliminates FM-1 entirely.

---

### DMS-2: Token Budget Hard Cap (P0 — REQUIRED)

Before any synthesis LLM call, DIP must:
1. Read current budget status from `OpsCenter/collaboration/blackboard.md`
2. If status is YELLOW or RED — abort synthesis, write partial intel to `/intel/` with a `[SYNTHESIS DEFERRED — BUDGET]` header, and alert Commander via Telegram.
3. Track cumulative token spend per run. If estimated spend exceeds **30K tokens in a single DIP session**, halt and alert before proceeding.

This directly addresses FM-3 and the current YELLOW budget state.

---

### DMS-3: Write-Scope Lock (P0 — REQUIRED)

The `dossier_intelligence_bot.py` orchestrator must enforce a hard-coded allowlist of write-permitted directories:

```
ALLOWED_WRITE_PATHS = ["/home/john/Thunderbird/intel/"]
BLOCKED_WRITE_PATHS = [
    "/home/john/Thunderbird/dossiers/",
    "/home/john/Thunderbird/output/",
    "/home/john/Thunderbird/OpsCenter/collaboration/",
]
```

Any attempt to write outside `ALLOWED_WRITE_PATHS` triggers an immediate abort + Telegram alert + `dissent_log.md` entry. This prevents FM-6 before it occurs.

---

### DMS-4: PII Pre-Filter at Synthesis Boundary (P1 — REQUIRED)

Before any tool result is passed to the synthesis LLM, a lightweight local filter must scan for PII markers:

- Client last names (against active dossier list)
- Email address patterns (`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`)
- Booking reference patterns (`[A-Z]{2,3}[0-9]{4,8}`)

If PII is detected: **strip it before synthesis**, log the strip event to `dissent_log.md`, and flag the output as `[PII STRIPPED — VERIFY]`.

This addresses FM-7 without blocking the pipeline.

---

### DMS-5: Watchdog Timer — Max Wall-Clock Execution (P1 — REQUIRED)

Each DIP run must register a maximum wall-clock execution time: **300 seconds (5 minutes)** for a standard intel scan.

If the orchestrator does not reach COMPLETE state within 300 seconds, the watchdog:
1. Sends SIGTERM to `dossier_intelligence_bot.py`
2. Writes abort entry to blackboard
3. Sends Telegram alert: `DIP WATCHDOG: {task_id} exceeded 5min wall-clock limit. Terminated.`

This addresses FM-2 (gate crash mid-execution) and FM-3 (runaway retry loops).

---

### DMS-6: Synthesis Confidence Gate (P2 — RECOMMENDED)

The synthesis LLM prompt must include an explicit uncertainty directive:

> "If you cannot synthesize a confident recommendation from the provided data, return `CONFIDENCE: LOW` in your response header. Do not fabricate specifics."

If `CONFIDENCE: LOW` appears in synthesis output: DIP writes the raw parsed JSON to `/intel/` with a `[SYNTHESIS DEFERRED — LOW CONFIDENCE]` header, and skips the recommend/publish step. Commander can trigger manual synthesis on review.

This addresses FM-4 at the output level.

---

### DMS-7: Star Protocol Log Migration (P2 — RECOMMENDED)

While the star protocol timer is disabled (correct per SO), the CSV log is still the right audit destination. Recommend:
- Keep `star_protocol_log.csv` as the DIP audit trail
- Add a simple tail-monitor cron (no LLM, pure bash) that alerts Commander if the log grows by >50 entries without a corresponding blackboard COMPLETE entry — indicating a runaway retry condition

This restores audit visibility (FM-5) without re-enabling the token-burning star protocol timer.

---

## PART 4 — RECOMMENDED DIP ROLLOUT GATES

Before DIP goes live, the following gates must clear:

| Gate | Check | Owner |
|---|---|---|
| **G-1** | Blackboard heartbeat writes tested in dry run | Goose / Commander |
| **G-2** | Token cap logic verified against YELLOW budget state | Claude / Commander |
| **G-3** | Write-scope lock unit tested — confirm `/dossiers/` write is blocked | Goose |
| **G-4** | PII filter tested against a sample dossier intel result | Claude |
| **G-5** | Watchdog timer tested — confirm SIGTERM fires at 300s | Goose |
| **G-6** | One full dry run with no LLM synthesis — tool call + parse + publish only | Commander sign-off |

**Recommended first live run:** `runInnovationScan` only — lowest PII risk, bounded output, well-understood tool behavior.

---

## CLOSING ASSESSMENT

DIP is architecturally sound for the goal (lower latency, lower cost, autonomous intel). The Safe-CLI gate is a genuine safety improvement over the raw blackboard-watcher model. The gaps are compensable without redesigning the architecture — they require adding state registration hooks, budget awareness, and scope guards that the current proposal omits.

**The dead-man's switch is DMS-1 + DMS-2 + DMS-3 as a non-negotiable trio.** Without those three, DIP is a well-gated tool executor with an ungated LLM synthesis step and no shared state — and that's a token fire waiting to happen on a YELLOW budget day.

---

*Analysis produced by Claude Sonnet for Commander John Loucks. Task GT-20260330-2236-STRA. 2026-03-30.*
