# Agent Control, Evaluation & Progress-UX — SOTA Survey (2026)

*Compiled 2026-07-29. Scope: how a single human operator retains fine-grained control, rigorous appraisal, and live visibility over a fleet of LLM agent "seats" — surveyed for application to the Thunderbird / Hale multi-Hale (CC/OC/AG) system.*

---

## Executive Summary

1. **Durable workflow engines (Temporal, Restate, DBOS, Inngest) are converging on agent orchestration** as their flagship use case in 2026 — journaled steps, automatic retry/replay, signals-in/queries-out, and human-approval pauses that can last months, not seconds.
2. **LangGraph's `interrupt()` + checkpointer is the reference pattern for HITL pause/resume/time-travel** — pause before risky nodes, edit state mid-flight, replay-and-branch from any past checkpoint. v1.2 (May 2026) tightened interrupt semantics.
3. **OpenAI Agents SDK and Claude Agent SDK both formalize the same three primitives** — guardrails/hooks that can hard-stop a run (tripwire / exit-code-2), lifecycle hooks for cross-cutting observation, and handoffs/subagents for delegation — but neither ships durable execution; that's what Temporal/Restate/DBOS bolt on.
4. **CrewAI's hierarchical manager-worker mode is documented but empirically unreliable** — multiple 2026 sources report the "manager" degrading to sequential execution with excess tool calls; treat it as a cautionary tale, not a template, for Hale's own manager/worker delegation.
5. **"Plan → approve → execute" (propose-diff-then-apply) is now the industry-default pattern for consequential agent actions** — GitHub Copilot Plan Mode, Antigravity, and Claude Code's own plan mode all converge on: investigate → produce a reviewable diff/plan → human gate → execute.
6. **tau²-bench's `pass^k` metric is the load-bearing 2026 eval number**, not pass@1 — it measures whether an agent solves the *same* task on *every one* of k tries. Reported gap: pass^4 often runs 15-25 points below pass^1; a 90% benchmark score can mean ~70% real-world reliability.
7. **LLM-as-judge has five named, separately-mitigated biases** (position, verbosity, self-preference, format, calibration drift) — mechanical fixes exist for each (shuffle order, length-normalize, cross-family judge, rubric anchoring, Cohen's-kappa calibration against human labels) and are treated as mandatory, not optional, in production 2026 setups.
8. **SRE error-budget math applied to agents is brutal and useful**: a 5-step workflow at 95% per-step accuracy is only 77% end-to-end; at 10 steps, 60%. Compounding failure, not any single failure mode, is the dominant driver of agent unreliability — this argues for decomposing Hale's SSS chop-chain into short chains with hard verification gates, not long unverified ones.
9. **CI-gated regression eval for agents is now a named discipline** (EvalView, Confident AI/promptfoo, AgentAssay's Pass/Fail/Inconclusive three-valued verdict) — the standing practice is: deterministic checks first (cheap, fast, fail-closed), then LLM-judge on a 50-100 case representative sample, then production-trace replay.
10. **Terminal-first progress UX has become a legitimate product category**, not a hack — Fleet (tmux dashboard for multi-agent sessions), Ralph TUI (mission control with stop/recover/ship-safely), and Claude Code/Codex/OpenHands all read as "the terminal is current again." The common vocabulary: phase-labeled todo/checklist streams, desktop-notification-on-block, and explicit escalation markers rather than silent stalls.

---

## Area A — Orchestration Control & Human Oversight

### A.1 LangGraph — interrupt / checkpoint / time-travel

- **Checkpointer** persists full graph state after every superstep to a pluggable backend (in-memory, SQLite, Postgres). This is the substrate everything else in LangGraph's HITL story is built on.
- **`interrupt_before` / `interrupt_after`**: declare specific nodes as hard stops. Execution reaches the node, the checkpointer commits state, control yields to the host app — the human can inspect, edit, approve, or reject before the graph resumes.
- **`interrupt()` function-call pattern** (tightened in v1.2, released 2026-05-11): pause *inside* a node body, not just at node boundaries — finer granularity than the older before/after-node interrupts.
- **Time travel**: because every step is checkpointed, you can rewind to any prior checkpoint, edit the state there, and fork a new branch of execution from that point — effectively "undo" plus "what-if" for a running agent.
- v1.2 also added content-block-aware streaming and Python 3.10–3.14 support.
- Sources: [LangGraph HITL — Towards AI](https://pub.towardsai.net/langgraph-human-in-the-loop-pausing-reviewing-and-rewinding-your-agent-4028bd05b049), [DeepWiki HITL & Interrupts](https://deepwiki.com/langchain-ai/langgraph/3.7-human-in-the-loop-and-interrupts), [Time-Travel Workflows](https://christianmendieta.ca/human-in-the-loop-ai-time-travel-workflows-with-langgraph/), [State Management: Checkpointing and Time Travel](https://rajatpandit.com/agentic-ai/langgraph-state-management-checkpoints/)

**STEAL THIS:** Thunderbird's SSS chop-chain has no equivalent of "interrupt_before" on the highest-risk verbs (client send, financial commit). Right now the three gates are enforced by convention/CLAUDE.md, not by a state machine that mechanically halts and requires a resume signal. A lightweight Python state machine (even without full LangGraph) that (a) persists a JSON checkpoint before WF-17/financial/strategic actions, (b) blocks until a Commander-side signal file or Sheet cell flips, (c) supports state-edit-then-resume, would give mechanical (not just prose) enforcement of the Three Gates.

### A.2 Durable workflow engines (Temporal / Restate / DBOS / Inngest)

All four have pivoted hard toward "AI agent orchestration" as a named use case in 2026. Comparison:

| Engine | Model | Retries | Human-in-loop | Signals/Queries | Heartbeats | Self-host | Notable 2026 detail |
|---|---|---|---|---|---|---|---|
| **Temporal** | Event-sourced workflow history, replay-based recovery | Automatic activity retry w/ backoff | Signals unblock a waiting workflow (can wait months) | Native `signal` (in) + `query` (out, read-only) | Yes — missing heartbeat within one interval → activity rescheduled | Self-hostable, but heavier (needs its own server cluster) | OpenAI Codex and Replit Agent reportedly run production workflows on Temporal |
| **Restate** | Durable journal per handler invocation | Automatic, step-journaled | "Resilient human approvals that might take minutes or months" | Durable RPC + K/V-keyed sessions | Built-in timeout/cancel/kill/rollback controls | Single binary, no extra DB, no separate worker process | Ships an Arize Phoenix integration for observable agents |
| **DBOS** | Library, not a server — wraps your existing Python/TS process | Automatic checkpoint-to-Postgres per step | `agent-inbox` pattern for HITL | Workflow alerting (Q1 2026) | N/A (library, not orchestrator) | Yes — just Postgres, no separate server | MCP server (2026) lets agents *inspect their own workflow failures* to self-diagnose |
| **Inngest** | Event-driven step functions | Per-step independent retry | `waitForEvent` blocks a step for external signal | Event-driven (`step.run`, `step.sleep`, `waitForEvent`) | Implicit via step timeouts | Cloud-first, self-host available | Full step-level trace (timing/input/output/retry) with zero extra instrumentation |

Sources: [Temporal — durable execution meets AI](https://temporal.io/blog/durable-execution-meets-ai-why-temporal-is-the-perfect-foundation-for-ai), [Temporal — orchestrating ambient agents](https://temporal.io/blog/orchestrating-ambient-agents-with-temporal), [Restate — durable AI loops](https://www.restate.dev/blog/durable-ai-loops-fault-tolerance-across-frameworks-and-without-handcuffs), [Restate — durable agents docs](https://docs.restate.dev/ai/patterns/durable-agents), [DBOS — March 2026 features](https://www.dbos.dev/blog/dbos-new-features-march-2026), [DBOS — human-in-the-loop](https://docs.dbos.dev/python/examples/agent-inbox), [Inngest — durable AI agent](https://www.inngest.com/blog/ai-agents-inngest-durable-steps), [Spheron — Temporal/Inngest/Restate comparison](https://www.spheron.network/blog/ai-agent-workflow-orchestration-temporal-inngest-restate-gpu-cloud/)

**STEAL THIS:** DBOS is the best architectural fit for Thunderbird — it's a *library*, not a service you stand up. Wrapping `staff_summary_sheet.py`'s state transitions (`sss|chop|decide|accomplish|closeout`) in DBOS-style Postgres-checkpointed steps would give crash-safe resume ("if the box reboots mid-chop, resume at the chop, not from scratch") without adopting a whole new orchestrator daemon — a much smaller lift than Temporal, and it directly targets the gap this system already has (systemd restarts losing in-flight SSS state). Restate is the fallback if a standalone durable-agent server becomes worth the ops cost.

### A.3 OpenAI Agents SDK

- **Guardrails**: run in parallel with the agent's main execution, not serially after. Each guardrail can raise a "tripwire" — as soon as it trips, the SDK immediately halts execution and raises an exception. This is a hard veto, not advisory.
- **Handoffs**: an agent hands control to another agent; the SDK runner keeps the tool loop and switches agents, and can pause the whole run for approval mid-handoff.
- **Tracing**: on by default. Captures LLM generations, tool calls, handoffs, guardrail trips, and custom events as spans.
- **Lifecycle hooks**: `RunHooks` (one observer for the whole run) vs `AgentHooks` (per-agent side effects); `on_handoff` fires specifically at agent-transfer boundaries.
- Sources: [OpenAI Agents SDK — guardrails](https://openai.github.io/openai-agents-python/guardrails/), [OpenAI Agents SDK — agents/hooks](https://openai.github.io/openai-agents-python/agents/), [Tracing](https://openai.github.io/openai-agents-python/tracing/)

### A.4 Claude Agent SDK (what CC itself runs on)

- Full hook event surface: `pre_tool_use`, `post_tool_use`, `post_tool_use_failure`, `user_prompt_submit`, `stop`, `subagent_start`, `subagent_stop`, `pre_compact`, `notification`, `permission_request`, `session_start`, `session_end`, `message_display`.
- **PreToolUse** can outright deny a call; **PostToolUse** sees the result and can react to it. Tool-use IDs correlate the pre/post pair for the same call.
- **Stop hook**: exits 2 (or returns `decision: "block"`) to force the agent to keep going — this is literally how a Stop-hook-based compliance ledger (already live per Thunderbird memory) enforces "don't declare done yet."
- **Subagents do not inherit parent permissions** — `SubagentStart`/`SubagentStop` hooks carry `agent_id`, `agent_type`, `agent_transcript_path`, so a parent can audit exactly what a spawned subagent asked to do.
- Layered permission system: declarative allow/deny rules → permission modes → `can_use_tool` runtime callback → hooks. A hook returning "allow" does *not* bypass the deny/ask layer beneath it — defense in depth by design.
- Sources: [Claude Agent SDK — Hooks](https://code.claude.com/docs/en/agent-sdk/hooks), [Claude Code Hooks — 30 Hook Events](https://www.morphllm.com/claude-code-hooks), [Claude Code Hooks — deterministic enforcement](https://hidekazu-konishi.com/entry/claude_code_hooks_complete_guide.html)

**STEAL THIS:** Thunderbird's existing Stop-hook compliance ledger (per memory: `project_hale_orchestrator_capability`) is already using the highest-leverage mechanism in this SDK. The unexploited piece is `SubagentStart`/`SubagentStop` — wiring these to auto-log every spawned subagent's declared `agent_type` + transcript path into the delegation-outcomes ledger would close the "was this actually delegated or silently self-executed" gap without new code in `delegation_wiring.py` itself, just a hook.

### A.5 CrewAI / hierarchical manager-worker — a cautionary case study

- Nominal design: a manager agent decides which specialist handles each subtask, can reassign on unsatisfactory output, `allow_delegation=True` on manager only.
- **Reported failure mode (2026, multiple independent sources)**: in real workflows the "manager" frequently degrades into pure sequential execution — no actual coordination — producing wrong reasoning, redundant tool calls, and high latency. The manager-worker abstraction is real in docs but not reliably real in execution.
- Sources: [Why CrewAI's Manager-Worker Architecture Fails](https://towardsdatascience.com/why-crewais-manager-worker-architecture-fails-and-how-to-fix-it/), [CrewAI Hierarchical Process docs](https://docs.crewai.com/en/learn/hierarchical-process)

**STEAL THIS (as warning):** Hale-as-orchestrator over CC/OC/AG is structurally the same shape as CrewAI's manager-worker. The lesson isn't "don't do hierarchical delegation" — it's "don't trust the delegation happened just because the abstraction says it did." This is exactly why Thunderbird's `integrity_check.verify_and_record()` (independent cross-engine verification, not self-report) already exists — the CrewAI failure mode is direct evidence that pattern is necessary, not paranoia.

### A.6 Microsoft Agent Framework (AutoGen successor)

- Unifies AutoGen's simple agent abstractions with Semantic Kernel's enterprise features (session state, type safety, middleware, telemetry) plus graph-based workflows.
- Stable orchestration patterns: sequential, concurrent, handoff, group chat, and "Magentic-One." All support streaming, checkpointing, human-in-the-loop approval, and pause/resume for long-running work.
- `BackgroundAgentsProvider` fans out subtasks to child agents running in parallel.
- Sources: [MAF at Build 2026](https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-at-build-2026-announce/), [MAF v1.0](https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/)

### A.7 Plan-then-execute / propose-diff-then-apply

- Now the de-facto standard for any agent taking consequential real-world action: **investigate → produce a reviewable plan/diff (no side effects yet) → human approval gate → execute the approved plan only.**
- Concretely implemented in GitHub Copilot's Plan Mode, Google Antigravity ("prune a plan before you approve it"), and Claude Code's own Plan Mode (which this very session's harness uses, including the `ExitPlanMode` PreToolUse hook gating on captured must-haves).
- Dry-run/preview variant: validate inputs → read current state → compute the proposed diff → surface a change-preview → only then apply, closing the gap between "what the reviewer saw" and "what actually executed."
- Sources: [LangChain — Plan-and-Execute Agents](https://www.langchain.com/blog/planning-agents), [Antigravity — prune a plan before approval](https://antigravitylab.net/en/articles/agents/antigravity-plan-prune-before-approval-partial-edit), [Execute/Verify/Rollback control-plane series](https://digitalthoughtdisruption.com/2026/07/25/execute-verify-rollback-agent-actions/)

**STEAL THIS:** Thunderbird already has this (SO 2026-07-19 PLAN-MODE MANDATE). The missing piece per the pattern literature is the **dry-run/diff-preview step for the highest-risk SSS actions** (financial commit, client send) — not just a plan narrative but a literal "here is the exact draft/amount/recipient, unexecuted" artifact the Commander sees before COORD/APPR/SIG.

### A.8 Escalation: signaling "stuck" vs. silent failure

- A **silent failure** produces no signal at the moment it occurs — no crash, no red test, work just doesn't happen or happens wrong, and it propagates downstream through pipeline handoffs.
- The recommended "three-layer defense" on every agent deployment: **a time limit, a success definition, and an escalation path.** If no signal arrives within the SLA, a timer fires and the system takes a *defined* action (escalate / auto-approve / auto-reject / notify secondary reviewer) — never "keep waiting silently."
- The structural fix for worker patterns: an explicit timeout on every dispatched task, with the orchestrator marking a non-responsive worker as failed and invoking a named fallback — never leaving the pipeline stalled indefinitely.
- Sources: [Silent Failure — Encyclopedia of Agentic Coding Patterns](https://aipatternbook.com/silent-failure), [The silent failures: When AI agents break without alerts](https://medium.com/@milesk_33/the-silent-failures-when-ai-agents-break-without-alerts-23a050488b16), [Temporal AI Agent Failures: 11 Production Pitfalls](https://www.xgrid.co/resources/temporal-ai-agent-orchestration-failure-patterns/)

**STEAL THIS:** Thunderbird's `core/relay/reconcile_oc.py` (`reconcile_due()`) already implements "unclaimed / stalled / vanished → paged as DROPPED/STALLED, not silently re-queued" — this is exactly the recommended pattern. The gap is that this only runs from the evening brief; per the "timer fires and takes a defined action" principle, an SLA-driven check (not just a daily batch) would catch a stuck AG/OC ticket hours sooner.

---

## Area B — Effectiveness Appraisal & Agent Accountability

### B.1 Benchmarks that matter in 2026 (and their pitfalls)

Six benchmarks widely cited as the current production-relevant set:

- **GAIA** — general assistant tasks
- **SWE-Bench Verified** — real GitHub bug-fixes
- **OSWorld** (now OSWorld2.0) — computer-use on a real desktop, long-horizon
- **tau²-bench** — tool-agent-user interactions with policy adherence (customer service domain; Sierra AI)
- **WebArena** — 812 long-horizon multi-step browser tasks (original best agent: 14.4% vs. 78.2% human baseline; by 2025, IBM CUGA hit 61.7%, OpenAI CUA hit 58.1%)
- **METR HCAST / Time Horizons** — the longest task an agent can complete 50% of the time (a "time-horizon" framing, not a pass-rate framing)

**The critical 2026 metric is `pass^k`, not `pass@1`.** `pass^k` asks: does the agent solve the *identical* task on *every one* of k independent tries? This measures reliability, not luck. Reported finding: **pass^4 scores commonly run 15–25 points below pass^1** — meaning a 90% single-shot benchmark score can correspond to as little as ~70% real production reliability once you account for retried sessions.

Newer diagnostic work (2026) goes further: **Odysseys** (200 long-horizon multi-site tasks from real browsing histories) and **HORIZON** both argue that trajectory-level LLM-as-judge scoring is *inadequate* for long-horizon tasks — terminal pass/fail metrics systematically under-characterize *where* in a long trajectory things actually broke. **AgentLens** documents a related "lucky pass" problem specifically in SWE-agent evaluation (passing for the wrong reason).

Sources: [AI Agent Benchmarks 2026: 6 Tests That Matter](https://decodethefuture.org/en/ai-agent-benchmarks-2026/), [τ-bench 2026 guide](https://benchmarkingagents.com/tau-bench/), [Beyond pass@1: Reliability Science for Long-Horizon Agents](https://arxiv.org/pdf/2603.29231), [AgentLens — Lucky Pass Problem](https://arxiv.org/pdf/2605.12925), [Holistic Agent Leaderboard](https://arxiv.org/pdf/2510.11977), [Odysseys](https://arxiv.org/pdf/2604.24964), [Log analysis necessary for credible agent evaluation](https://arxiv.org/pdf/2605.08545)

**STEAL THIS:** Thunderbird's Opus Compliance V1-V8 review structure and the equal-performance-standard-across-seats memory already gesture at this, but nothing in the described system currently re-runs the *same* SSS/mission-type task multiple times to check for `pass^k`-style consistency. A monthly "replay the same 5 canonical mission types across CC/OC/AG, 3x each, score variance" would surface exactly the kind of hidden unreliability pass^1-only grading misses — directly answering "did an engine get worse" with numbers instead of vibes.

### B.2 LLM-as-judge: five named biases, five mechanical fixes

| Bias | Failure mode | Mitigation |
|---|---|---|
| Position | Judge favors whichever option is listed first/second | Shuffle/rearrange comparison order, average both orders |
| Verbosity | Judge favors longer answers regardless of quality | Explicit "do not prefer longer answers" rubric line; length-normalize scores |
| Self-preference | Judge favors output from its own model family | Use a judge from a *different* model family than the agent being graded |
| Format | Judge favors superficial formatting polish over substance | Rubric anchored to substance-only criteria, blind formatting where possible |
| Calibration drift | Judge's absolute scores drift over time/model versions | Calibrate against human-labeled gold set via Cohen's kappa periodically |

2026 production guidance: "the mitigation that works is mechanical; 'better prompts' is the layer on top" — i.e., don't rely on judge-prompt wording alone; build the structural controls (shuffling, cross-family judging, length norm, kappa calibration) into the eval harness itself.

Sources: [LLM-Judge Bias Mitigation 2026](https://futureagi.com/blog/evaluating-llm-judge-bias-mitigation-2026/), [Self-Preference Bias in LLM-as-a-Judge](https://arxiv.org/pdf/2410.21819), [Judging the Judges: Systematic Evaluation of Bias Mitigation](https://arxiv.org/pdf/2604.23178), [Justice or Prejudice? Quantifying Biases](https://arxiv.org/pdf/2410.02736)

**STEAL THIS:** Any Wing use of "have Claude grade Claude's work" (e.g., WF-17 gates, presend_evaluate) is exactly the self-preference-bias failure mode described above unless the judge is a *different* model family than the author. Concretely: CC-authored client drafts should be graded by AG (Gemini) or a DeepSeek arbitrator, never by CC itself claiming a passing score — which is already Thunderbird's stated "PII fence: Deepseek / arbitrator" pattern per the blackboard, so the doctrine is right; the audit question is whether `presend_evaluate` / `email_score_draft` actually enforce cross-family judging in code, or just in policy.

### B.3 Production agent scorecards — what's actually in one

- Best-practice structure: a rubric explainable in one minute, starting with 5-7 weighted criteria, expanding slowly. Score **tool choice, inputs, retries, and side effects** — not just final-answer correctness.
- Distinguish graded rubrics (1-5 scale with defined descriptions per level) from pass/fail "tests" (binary criteria that must hold).
- Continuous production monitoring tracks performance *drift* over time — the named failure patterns to watch for are unreachable services, behavior deviations, and integration failures.
- Sources: [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), [Build Agent Scorecards for Tool Use](https://www.agentixlabs.com/blog/general/build-agent-scorecards-for-tool-use-catch-hidden-failures-in-weekly-deploys/), [Rubric-Based Evaluation for Agentic Systems](https://medium.com/@aiforhuman/rubric-based-evaluation-for-agentic-systems-db6cb14d8526)

### B.4 SRE applied to agents — error budgets, compounding failure

- SLO defines a target reliability; the gap between perfect (100%) and the SLO target is the **error budget** — the "allowed" failure per period. This becomes the *mechanism*, not just a metric, that gates how much autonomy an agent is allowed: "if remaining budget < Z%, restrict auto-remediation and require human approval."
- **The compounding-failure math is the single most important number in this whole survey for a multi-step system**: at 95% per-step accuracy, a 5-step workflow lands at 0.95^5 ≈ 77.4% end-to-end; at 10 steps, 0.95^10 ≈ 59.9%. Long chains silently erode reliability even when every individual step looks fine in isolation.
- MTTR = time from detection through investigation, remediation, and verified correction (not just "fix pushed").
- Sources: [Applying SRE to Autonomous AI Agents — Microsoft](https://techcommunity.microsoft.com/blog/linuxandopensourceblog/applying-site-reliability-engineering-to-autonomous-ai-agents/4521357), [Error Budgets in SRE — Sedai](https://sedai.io/blog/sre-error-budgets), [AI Agent Error Budgets — SRE Reliability for Autonomous Agents](https://www.buildmvpfast.com/blog/ai-agent-error-budget-sre-reliability-autonomous-2026)

**STEAL THIS — this is the single highest-value finding in the whole survey:** the USAF SSS chop-chain (OPR → OCR chop → COORD/APPR/SIG → OPR executes → CHIEF SILVER front+back gate) is a long chain — each additional cross-Hale hop multiplies compounding-failure risk per the 0.95^n math above. This is a *quantitative* argument for what Thunberd's SO-2026-07-19 already does qualitatively (mandatory cross-seat certification catches exactly this), but it also argues for **measuring and publishing an actual per-hop reliability number** (not assuming 95%) so the chop-chain length vs. risk tradeoff is visible, and for keeping SSS chains as short as the gate structure allows.

### B.5 Regression detection in CI

- Standard 2026 pipeline shape: **deterministic checks first** (cheap, fail-closed) → **LLM-as-judge on a 50-100 case representative sample** (catches major regressions without full-corpus cost) → **production-trace replay** (staging evaluated against real production traces, not just synthetic cases).
- Named tools: **EvalView** (snapshot behavior, diff tool calls, catch regressions in CI, works with LangGraph/CrewAI/OpenAI/Anthropic), **Confident AI / promptfoo** (git-style branching/PRs for prompts, eval-on-commit, 50+ drift metrics), **AgentAssay** (introduces three-valued Pass/Fail/Inconclusive verdicts via statistical hypothesis testing instead of forcing a binary call on inherently noisy agent behavior).
- Root cause framing: regressions come from changes that *look* harmless — a reworded system prompt, a silent model-version bump, a provider updating a checkpoint under the same public name.
- Sources: [EvalView (GitHub)](https://github.com/hidai25/eval-view), [Testing LLM prompts like code — promptfoo](https://medium.com/@alexrodriguesj/testing-llm-prompts-like-code-regression-evals-in-ci-cd-with-promptfoo-5242b4dcb9be), [AgentAssay](https://arxiv.org/pdf/2603.02601), [MLflow — Regression Testing and CI/CD](https://mlflow.org/docs/latest/genai/eval-monitor/regression-testing/)

**STEAL THIS:** The three-valued Pass/Fail/Inconclusive verdict (AgentAssay) directly addresses a known Thunderbird pain point (per memory: `feedback_credential_doomsday_false_alarms` — false-alarm noise from binary pass/fail on inherently noisy checks). Adopting a three-state verdict for e.g. CI probes and heartbeat scans, not just eval, would reduce false-alarm paging while still surfacing genuine regressions.

### B.6 Cost accounting per agent/task

- **Cost per successful task** (not cost per token/request) is the 2026-standard economic unit: total cost of running the agent on a task ÷ rate of *correct* completion. This bakes failure cost into the denominator, unlike raw token cost.
- Attribution should be built along three axes from day one — per-user, per-task, per-tenant — so views can be recombined without re-instrumenting.
- Practical rollup: attach request metadata to spans, then roll up cost against users/features/agent-runs/customers/quality-outcomes together, not cost in isolation.
- Sources: [Cost per Successful Task — LangWatch](https://langwatch.ai/blog/cost-per-successful-task), [How to track LLM costs 2026 — Braintrust](https://www.braintrust.dev/articles/how-to-track-llm-costs-2026), [AI Agent Cost Optimization and Observability 2026](https://futureagi.com/blog/ai-agent-cost-optimization-observability-2026/)

**STEAL THIS:** Thunderbird's `delegation_outcomes.py` ledger already records action/outcome; adding a cost field (tokens × rate, or Poe points consumed) per recorded outcome turns the existing ledger into a cost-per-successful-outcome report almost for free — directly answering "is self-executing on the MAX meter actually cheaper than delegating to OC/AG" with numbers instead of the current soft-guidance heuristic.

---

## Area C — Live Progress UX for a Solo Operator

### C.1 Terminal/TUI dashboards for agent fleets

- **Fleet** (github.com/nicknisi/fleet) — a terminal dashboard for managing multiple AI agent sessions inside tmux. Tracks per-agent state (waiting / asking / ready) via hooks, so each pane shows real status, and fires silent OS-native desktop notifications specifically when an agent finishes a turn *or* stops to ask for input — i.e., interrupt only on state changes that need a human, never on routine progress.
- **Ralph TUI** — "mission control" framing: real-time visibility into tasks, ability to stop infinite loops, recover state, ship safely. Aimed explicitly at giving a human operator control over otherwise-autonomous long runs.
- **Textual** (Python, asyncio-based) is the dominant framework underneath these — rich layouts/widgets/tables with web-app-like responsiveness, purpose-built for dashboards and CLI tools.
- Sources: [Fleet (GitHub)](https://github.com/nicknisi/fleet), [Ralph TUI: Mission Control Dashboard](https://www.verdent.ai/guides/ralph-tui-ai-agent-dashboard), [Textual TUI Widgets](https://johal.in/textual-tui-widgets-python-rich-terminal-user-interfaces-apps-2025/)

**STEAL THIS:** A Fleet-style tmux dashboard over CC/OC/AG's live sessions (state: waiting/asking/ready per seat) plus desktop-notify-only-on-block would directly serve "maximum control and visibility" without requiring the retired TCD web app. This is a smaller, more durable investment than rebuilding a web UI — it rides on tmux + hooks, both of which Thunderbird already has (Claude Agent SDK hooks are exactly the state source Fleet consumes).

### C.2 Progress representation for non-deterministic work

- The emerging vocabulary across tools: **phase-labeled todo/checklist streams** (a running list of discrete steps, checked off live — this is literally what Claude Code's own TodoWrite tool renders), rather than a percentage progress bar (which is meaningless for open-ended agentic work where step count isn't known in advance).
- **Elapsed-vs-estimated timers** are used sparingly since agent task duration is high-variance; burn-down framing works better for known-finite backlogs (e.g., "12 of 40 dossiers refreshed") than for open-ended reasoning.
- **Escalation markers**: the recommended UX pattern is a clear, distinct "here is where I got stuck" visual marker distinguishable from routine progress lines — matching the Area A finding that silent failure is the thing to design against.

### C.3 Notification/paging strategy

- Consistent finding across sources: **page/interrupt only on state transitions that require a human decision** (blocked, asking, finished); everything else belongs in a passive digest. Fleet's implementation (desktop notification only on "finished" or "asking") is the concrete embodiment of this.
- The three-layer defense pattern from Area A.8 (time limit / success definition / escalation path) doubles as the paging policy: silence is fine until the SLA timer fires, then a *defined* action fires — not an open-ended alert flood.

**STEAL THIS:** This directly matches Thunderbird's own stated doctrine (`feedback_telegram_channel_discipline`: Telegram urgent-only; `feedback_overnight_message_volume`: overnight digest not flood) — the external research confirms the doctrine is right, and suggests the Fleet-style "notify only on waiting/asking/ready transitions" is the concrete mechanism to apply it to CC/OC/AG session monitoring specifically, not just email/Telegram.

### C.4 How the named coding-agent products actually surface progress (2026)

- **Claude Code / Codex**: terminal-centered — read files, run commands, edit code, report results, without a separate desktop window; the todo-checklist stream is the primary progress signal.
- **Devin / Cognition**: "Devin Local" (successor to the Cascade agent) runs terminal commands and browser previews, streaming what it *sees* back into the session live as it iterates — visual/terminal feedback loop, not just text status. Cognition rebranded its IDE as "Devin Desktop" (June 2026) and added an "Agent Command Center" plus parallel agent sessions in the 2.0 release — i.e., a fleet-of-agents view is now a first-class product surface, not a hack.
- **OpenHands**: positions itself as the open, model-agnostic, community-driven alternative to Devin — sandboxed execution, 10+ model providers behind one interface, real user control over model choice and cost (relevant directly to Thunderbird's own multi-model CC/OC/AG/Poe routing).
- Sources: [OpenHands — Claude Code Alternatives 2026](https://www.openhands.dev/blog/claude-code-alternatives), [Devin vs Claude Code vs Codex 2026](https://techsy.io/en/blog/background-coding-agents-compared), [Best AI Agent Multiplexers 2026](https://amux.io/guides/best-ai-agent-multiplexers-2026/)

---

## Comparison Table — Durable Workflow Engines for Agent Orchestration

| Dimension | Temporal | Restate | DBOS | Inngest |
|---|---|---|---|---|
| Deployment model | Dedicated server cluster | Single self-hostable binary | Library inside your app (Postgres-backed) | Cloud-first SaaS (self-host available) |
| Unit of durability | Full workflow event history, replay-based | Per-handler journal | Per-step Postgres checkpoint | Per-step checkpoint store |
| Human-in-the-loop | Signal can wait indefinitely | Built-in "resilient approvals," minutes-to-months | `agent-inbox` pattern | `waitForEvent` blocks a step |
| Observability | Full workflow history + replay debugging | Arize Phoenix integration | MCP server: agent inspects its own failures | Full step trace (timing/IO/retry) auto-captured |
| Best fit for Thunderbird | If a standalone orchestrator daemon becomes justified | Middle ground — single binary, still a service | **Best near-term fit** — no new daemon, wraps existing Python | Good if moving to event-driven cloud functions |

---

## Top-Line Recommendations for Thunderbird

1. **Wrap SSS state transitions in a DBOS-style durable-step pattern** (Postgres-checkpointed) so a systemd restart mid-chop resumes instead of losing state — smallest-lift fix for the compounding-failure risk in a long chop-chain.
2. **Wire `SubagentStart`/`SubagentStop` hooks directly into `delegation_outcomes` recording** — closes the "was this really delegated" gap with near-zero new code, riding the same Stop-hook mechanism already proven live.
3. **Enforce cross-family judging in code, not just policy**, anywhere Thunderbird self-grades its own client-facing output (`presend_evaluate`, `email_score_draft`) — audit whether these actually call a different model family or just claim to.
4. **Adopt AgentAssay-style three-valued (Pass/Fail/Inconclusive) verdicts** for CI probes and heartbeat scans specifically to cut the known false-alarm noise pattern, without losing genuine-regression detection.
5. **Add a cost field to `delegation_outcomes` rows** to turn the existing ledger into a real cost-per-successful-outcome report, replacing the current soft self-execute-vs-delegate heuristic with numbers.
6. **Build a Fleet-style tmux/hook dashboard over CC/OC/AG sessions** (waiting/asking/ready + desktop-notify-only-on-block) as the lightweight, durable replacement for the retired TCD web app's live-visibility function.
7. **Run a monthly pass^k-style replay** (same canonical mission types, 3x each, across CC/OC/AG) to catch hidden reliability regressions that a one-shot pass@1 grading would miss.
