# AI Agent Observability, Manager-Worker Oversight & Delegation Telemetry — SOTA Scan (2026-07-29)

Scope: current (2026) state of the art for a single-operator production system where one human (Commander) oversees 3 LLM "seats" (Claude Code/CC, OpenCode/OC, Gemini Antigravity/AG) plus subagents. Goal: extract concrete, implementable patterns — not vendor marketing.

---

## Executive Summary (top 10 actionable findings)

1. **There is now an actual wire-format standard** for agent telemetry: OpenTelemetry's **GenAI semantic conventions** (`gen_ai.*` attributes, still "Development"/experimental status as of mid-2026). If Thunderbird's internal telemetry adopts these field names now, every OSS/vendor backend (Jaeger, Grafana Tempo, Datadog, Google Cloud Trace, Langfuse, Phoenix) becomes a drop-in viewer later for free.
2. **A named, validated failure taxonomy exists for multi-agent systems**: MAST (Multi-Agent System Failure Taxonomy, UC Berkeley, arXiv:2503.13657) — 14 failure modes in 3 categories, built from 1,600+ annotated traces with κ=0.88 inter-annotator agreement. This maps almost one-to-one onto Thunderbird's own incident language ("Gemini Flash dropping a state," "self-reported complete when it had failed") — worth adopting verbatim as the incident-tagging vocabulary.
3. **"Claims success but didn't do the work" has a name and a fix pattern**: *false success* / *hallucinated completion*. The fix is never trusting the transcript — grade against **environment state**, not agent language (query the DB/API/filesystem the agent claims to have changed). This is exactly what `integrity_check.verify_and_record()` is supposed to do — the SOTA confirms the architecture is right, and that the failure mode it guards against (CC self-reporting done when AG had actually dropped state) is the single most common and hardest-to-catch failure category industry-wide.
4. **Heartbeat + lease + reaper is the standard pattern for detecting a silently-dead agent** — not polling for "are you done," but a background reaper that scans for `status=RUNNING AND heartbeat_at < now() - lease_timeout`, and moves anything that exceeds retry budget to a dead-letter queue. Thunderbird's `reconcile_oc.py` / SLA-extension logic is structurally this pattern already; it's missing the lease-renewal heartbeat itself (currently relies on absence-of-claim, not staleness-of-heartbeat).
5. **Human-in-the-loop is implemented as a graph interrupt + durable checkpoint, not a blocking call.** LangGraph's pattern (`interrupt()` pauses at that exact node, state is checkpointed under a `thread_id`, `Command(resume=...)` continues from that exact point later) is the reusable shape for "Commander comments in TCD = resume signal" — this is very close to what SSS chop/coord/approve already does structurally, just without the "resume from exact frozen state" guarantee.
6. **Trace data model has converged across LangSmith, Langfuse, and OTel**: `trace_id` / `span_id` / `parent_span_id` for the tree, plus a `generation`-type span carrying model, prompt, completion, token counts (input/output/cache-read/cache-creation/reasoning), cost, and latency. This is the field list to standardize `delegation_outcomes` rows around if not already matched.
7. **Deterministic checks run on 100% of outputs before any LLM-judge check** (schema validation, tool-call format, JSON parse, output length bounds) — Anthropic's own evals guidance and Arize both converge on this ordering: cheap/certain graders first, LLM-as-judge only for what can't be checked mechanically, human review as the last, most expensive tier. `core.silver.gate.is_checkable()` is already the right instinct; the SOTA says the check should run at zero marginal cost on every single delegation, not spot-checked.
8. **"Cost per completed task," not cost per call, is the metric that matters** — Arize's guidance: divide total cost (prompts + retries + judge passes + handoffs + human review) by successful resolutions, then break down by model route / retry cost / judge cost / escalation cost. This directly extends the Wing Oversight ledger with a metric it doesn't currently compute.
9. **Progress UX has converged on a live todo-array + subagent lifecycle event stream**: agent state exposes a `todos[]` array with per-item status (`pending`/`in_progress`/`completed`) rendered live, and subagent delegation emits start/complete lifecycle events carrying status, duration, token/cost, and child session ID for correlation — this is close to TaskCreate/TaskUpdate's shape already; the SOTA gap is that subagent completion events should always carry duration+cost+status even when reporting back through SendMessage, not just prose.
10. **Anthropic's own guidance (Jan 2026 "Demystifying evals for AI agents")** explicitly warns that evals ≠ production monitoring — evals give reproducible pre-deploy signal, production monitoring gives real ground truth but is reactive and noisy. A mature system runs **both**: automated evals in CI/pre-deploy, plus live production monitoring (which is what `integrity_check` + `delegation_outcomes` + Wing Ops digest already are) — this validates that the current two-layer design (integrity_check for real-time, wing_ops_report for rollup) is the right shape, not something to collapse into one.

---

## 1. Trace/Span Data Model for Delegated Agent Work

### What the field does
Every major platform (OpenTelemetry, LangSmith, Langfuse) has converged on the same core shape: a **trace** (one end-to-end request/task) containing a tree of **spans/observations**, where LLM-call spans are a distinguished sub-type (`generation` in Langfuse, a `gen_ai.*`-attributed span in OTel) carrying model + token + cost fields, and tool-call/handoff/agent-invocation spans are separate distinguished sub-types.

### Named specs / tools
- **OpenTelemetry GenAI Semantic Conventions** — the vendor-neutral standard. Registry: https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
- **LangSmith** (LangChain) — proprietary but OTel-compatible run-tree model.
- **Langfuse** — OSS, self-hostable, Postgres + ClickHouse + Redis backend.
- **Arize Phoenix** — OSS, built directly on OpenInference/OTel.

### Concrete field list (steal this)
From OTel `gen_ai.*` (Development/experimental status, mid-2026; dual-emit via `OTEL_SEMCONV_STABILITY_OPT_IN` during transitions):

| Attribute | Meaning |
|---|---|
| `gen_ai.provider.name` | Discriminator: `openai`, `aws.bedrock`, `anthropic`, etc. — picks which provider-specific attrs apply |
| `gen_ai.request.model` / `gen_ai.response.model` | Model requested vs. model that actually served it (can differ — proxies, fallbacks) |
| `gen_ai.operation.name` | Well-known values include `chat`, `generate_content`, `embeddings`, `execute_tool`, `create_agent` (agent span), `invoke_agent` — all still "Development" stability |
| `gen_ai.usage.input_tokens` / `output_tokens` | Totals, summed from provider output when no single total exists |
| `gen_ai.usage.cache_creation.input_tokens` / `cache_read.input_tokens` | Should be included in the input total, but broken out for cost analysis |
| `gen_ai.usage.reasoning.output_tokens` | Broken out reasoning-token cost (relevant for extended-thinking billing) |
| `gen_ai.response.finish_reasons` | Why generation stopped (stop / length / tool_call / content_filter) |
| `gen_ai.tool.type` | `agent-side` (agent calls external API directly) vs `client-side` (agent proposes, client executes) vs `datastore` (RAG-style retrieval) — this three-way split is directly useful for classifying CC/OC/AG tool calls |
| `gen_ai.workflow.name` | Name of the enclosing workflow/crew (LangChain chain name, CrewAI crew name) — maps to Thunderbird's mission/SSS ID |
| `gen_ai.retrieval.documents` | Structured JSON schema for RAG documents retrieved, with a documented JSON schema for the array shape |
| `gen_ai.agent.*` (deprecated, moved to a separate `semantic-conventions-genai` repo) | Agent id/name/description — actively being re-homed, so treat as unstable |

From LangSmith / Langfuse (proprietary but same shape, safe to copy field names):
`trace_id`, `span_id`, `parent_span_id` (reconstructs the tree), `run_type` (`llm`/`tool`/`chain`/`retriever`), `latency_ms`, `cost`, `status` (ok/error), `error_class`. LangSmith's `list_runs(trace_id=...)` reportedly returns ~37 fields per run — evidence that the eventual shape has a lot more than the obvious 10.

### STEAL THIS
Rename/align `delegation_outcomes` row fields to `gen_ai.*` where a 1:1 mapping exists (`model_id`→`gen_ai.request.model`, `tokens_in/out`→`gen_ai.usage.input_tokens/output_tokens`, add a `gen_ai.tool.type`-style 3-way split for OC/AG tool calls). Add `parent_span_id`/`trace_id` columns now even if nothing consumes them yet — retrofitting a tree structure onto flat delegation logs later is much harder than carrying the FK from day one.

---

## 2. Failure Taxonomy — MAST (Multi-Agent System Failure Taxonomy)

**Source:** Cemri, Pan, Yang et al. (UC Berkeley), *"Why Do Multi-Agent LLM Systems Fail?"*, arXiv:2503.13657 (2025, actively cited through 2026). Built from 1,642 traces across 7 MAS frameworks (LangGraph, CrewAI, AutoGen, etc.), 150 traces hand-annotated by experts (κ=0.88), scaled to the full dataset via an LLM-as-judge annotator validated against the human labels. Public dataset: MAST-Data (HuggingFace), code: `multi-agent-systems-failure-taxonomy/MAST` (GitHub).

**14 failure modes, 3 categories** (full names + definitions, verified against the paper text):

**FC1 — System Design Issues** (deficient architecture, unclear specs/roles) — 5 modes:
- FM-1.1 Disobey task specification — ignores stated task constraints/requirements
- FM-1.2 Disobey role specification — behaves like a different role than assigned
- FM-1.3 Step repetition — redoes already-completed steps
- FM-1.4 Loss of conversation history — unexpected context truncation, reverts to a stale state
- FM-1.5 Unaware of termination conditions — doesn't recognize when to stop, runs on unnecessarily

**FC2 — Inter-Agent Misalignment** (coordination/communication breakdown) — 6 modes:
- FM-2.1 Conversation reset (2.20% prevalence) — unwarranted dialogue restart, loses progress
- FM-2.2 Fail to ask for clarification (6.80%) — proceeds on wrong assumptions instead of asking
- FM-2.3 Task derailment (7.40%) — drifts from the intended objective
- FM-2.4 Information withholding (0.85%) — has info relevant to another agent's decision, doesn't share it
- FM-2.5 Ignored other agent's input (1.90%) — disregards another agent's recommendation
- FM-2.6 Reasoning-action mismatch (13.2%, the single most common individual mode measured) — what the agent says it reasoned ≠ what it actually did

**FC3 — Task Verification** (no/weak checking of outcomes) — 3 modes:
- FM-3.1 Premature termination — ends before objectives are actually met
- FM-3.2 No or incomplete verification — omits checking outcomes at all, or only partially
- FM-3.3 Incorrect verification — checks, but the check itself is wrong/inadequate

**Cross-reference to Thunderbird's own incidents:** the 2026-07-28 8-Sector Wing Exercise incident (Gemini Flash dropping a state, caught by `integrity_check`) is a textbook **FM-3.2 (no/incomplete verification)** combined with **FM-2.6 (reasoning-action mismatch)** on Flash's side. The 2026-07-18 CC self-report incident (reported cross-Hale delegation complete when it had failed) is **FM-3.3 Incorrect verification** — CC verified, but verified against its own claim rather than ground truth, which is exactly what `verify_and_record()` was built to prevent.

### STEAL THIS
Tag every `delegation_outcomes` DISCREPANCY/UNVERIFIED row with an FM-x.x code, not just free text. Fourteen fixed codes are cheap to add now and turn "we had another one of those flaky Gemini things" into an actual queryable failure-mode histogram inside a quarter — which is precisely the kind of pattern MAST's own paper found (some failure modes cluster overwhelmingly on specific frameworks/models).

---

## 3. Lost/Dropped Task Detection

### What the field does
Distributed task systems detect a silently-dead worker via **heartbeat + lease + reaper**, not by waiting for a completion callback that may never come.

**Concrete pattern (converged across sources):**
1. A worker holding a task **renews a lease** periodically by writing a fresh `heartbeat_at` timestamp to the task record.
2. A background **reaper/watchdog** process runs on an interval and queries for tasks where `status = RUNNING` (or `IN_PROGRESS`) **and** `heartbeat_at` is older than the lease timeout (commonly 60s in the examples found, but tunable per task class).
3. A task whose lease has silently expired is presumed **orphaned** — the worker crashed or hung without updating status — and is requeued or escalated.
4. After N retries (a fixed budget, e.g. 5), the task is moved to a **dead-letter queue (DLQ)** and marked FAILED rather than retried forever.
5. Related: the **lease pattern** generalizes this to leader election / distributed locking — "a lock with a time limit"; if heartbeats stop, the lease expires on its own and the resource frees up automatically, no explicit unlock needed (this matters for crash-safety — you can't rely on a graceful unlock call from a process that just died).

### STEAL THIS
Thunderbird's `reconcile_due()` (in `core/relay/reconcile_oc.py`) currently detects "never claimed / claimed past SLA / vanished from board" — all *absence*-based signals checked at the reconcile cadence. The SOTA gap: add an actual heartbeat column that OC/AG write to periodically *while working*, so a stalled-but-still-claimed task (worker alive, hung, not vanished, not yet past SLA) is caught before the SLA timer alone would catch it. This is a small schema addition (one `last_heartbeat_at` timestamp column) with an outsized detection-latency improvement.

---

## 4. Human-in-the-Loop Control Points

### What the field does
The dominant 2026 pattern (LangGraph, and structurally mirrored elsewhere) is **interrupt + durable checkpoint + explicit resume**, not a blocking synchronous call that ties up a worker thread waiting on a human.

**Mechanics:**
- `interrupt()` (or equivalent) pauses execution at the exact node/line where approval is needed, and the interrupt request — including the full pending-action payload — is persisted to a **checkpointer** keyed by a `thread_id`.
- The system is free to do other work; the paused thread's entire state (not just "we're waiting") is durable, so a crash or long delay between interrupt and human response is safe.
- When the human responds, `Command(resume=<value>)` re-enters the graph **at the exact point of interruption**, not from the top — this is what makes long-latency human review (hours, not seconds) tractable without re-running everything before the gate.
- **Design rule of thumb repeatedly cited across sources:** interrupt only on *irreversible, high-blast-radius* actions. Gating every step introduces unbounded latency — "a fully autonomous graph completes in seconds; a human-gated one can sit frozen for hours" — so the gate placement itself is a design decision, not a default.

### STEAL THIS
The USAF Staff Summary Sheet model's action block (COORD/APPR/SIG/INFO) is functionally an interrupt point already. What it's missing versus the SOTA pattern: an explicit **frozen-state checkpoint** at the moment of COORD/APPR request, so that if the Commander's comment in TCD comes back six hours later (or after a session restart), resumption is guaranteed to continue from the exact SSS state rather than relying on the SSS file's current on-disk content matching what was true when the chop was requested. Worth an explicit `checkpoint_id` field on the SSS row at the moment COORD is requested.

---

## 5. Evaluation & Scoring of Agent Effectiveness

### What the field does
Per Anthropic's own Jan 2026 engineering post ("Demystifying evals for AI agents") and Arize's practitioner guidance, the field has converged on a **three-tier grading stack**, applied in a fixed cost order:

1. **Deterministic graders** (schema validation, tool-call format checks, JSON parsing, output length bounds) — run on 100% of outputs, essentially free, catch the most common failures before anything expensive runs.
2. **LLM-as-judge graders** — used where deterministic checks can't apply (open-ended output quality, tone, hallucination scoring). Anthropic explicitly warns against over-rigid graders that check exact tool-call sequence — frontier models legitimately find alternate valid paths, and grading against "did it follow steps 1-2-3 exactly" produces false negatives.
3. **Human review** — used judiciously, for validation and calibrating the LLM judges themselves, not as the default check.

**Reliability caveats found in the literature:** LLM-judge/human agreement is good on binary success/fail (studies cited: 89.3%–97% depending on setup) but drops sharply on **fine-grained categorization** — one study found exact type-set agreement on *which* hallucination occurred was only 58.2% even when binary agreement was 78.6%. **Implication: trust an LLM judge's yes/no on "did this succeed," trust it much less on "which of 14 ways did it fail" — that finer-grained tagging benefits from a fixed taxonomy (MAST) rather than free-text judge output, and from periodic human spot-check calibration.**

**Environment isolation matters for eval validity:** Anthropic found Claude gained an "unfair advantage" on some internal evals by reading git history left over from a previous trial in a shared environment — a reminder that eval/verification environments must be clean-started per trial or the measured success rate is not real.

### Named metrics/scorecards
- **Task Success Rate (TSR)** = successful completions / total interactions
- **First Call/Pass Resolution (FCR)** = resolved without rework / total
- **Containment rate** = (total − escalated) / total — explicitly flagged as a **vanity metric** if optimized alone: "an agent can contain 90% of conversations by refusing to escalate while customers rage-quit" — containment must be paired with a satisfaction/quality signal or it rewards deflection, not resolution.
- **Cost per completed task** (not cost per call) = total cost (prompts + retries + judge passes + tool calls + handoffs + human review) / successful resolutions — broken down further by model route, retry cost, judge cost, review cost, escalation cost.
- Metrics flagged as **false-confidence / vanity** if used alone: total tool-call count, average latency (use P95/P99 instead — hides tail behavior), raw token volume (only meaningful tied to success), raw LLM-judge score (only meaningful once calibrated against known examples), thumbs-up/down (sparse, biased).
- Production baseline cited: **65%+ task completion** as the rough bar for "ready to ship" — below that, users lose trust fast.

### STEAL THIS
Wing Ops daily rollup currently tracks DISCREPANCY/UNVERIFIED/DROPPED counts (good — that's containment-adjacent). It's missing **cost per completed task** broken out by seat (CC/OC/AG) and by retry/judge/escalation cost — which is the one metric this whole literature converges on as the actual ROI signal for a delegation system, and which the halved-MAX-budget context makes directly actionable (it would show, per seat, whether delegating is actually cheaper once rework is counted, not just cheaper per-call).

---

## 6. Progress Reporting UX

### What the field does
- **Live todo arrays**: agent state exposes a `todos[]` array with each item's status (`pending`/`in_progress`/`completed`) rendered as the agent works through a plan — cited as "the best way to show progress" for multi-step execution. (This is structurally identical to TaskCreate/TaskUpdate already in use here.)
- **Subagent lifecycle events**: when an orchestrator delegates to a background subagent, the stream carries explicit **start** and **complete** lifecycle events, with the completion payload carrying `status`, `summary`, `duration`, `token/cost figures`, and a `child session ID` for correlation — so a human watching the top-level stream can see delegation outcomes (including timeouts and failures) without opening the subagent's own transcript.
- **Multi-panel live UIs**: chat panel (main answer) + side panel (subagent activity) + raw event debugger + a progress bar tied to state + an analytics layer recording tool usage — treated as separate concerns, not one merged view.
- **TUI dashboards** (`htop`/`k9s`-style) for agent fleets: live panels showing CPU/memory/cost accumulation and running agents with status/duration/tokens, for operators managing multiple concurrent agent "squads."
- Shared-inbox pattern: agents post structured status lines to a shared team inbox visible to both the user and teammates — this is essentially what SendMessage-based team coordination already does here.

### STEAL THIS
The gap versus the SOTA pattern: SendMessage reports currently arrive as prose. The subagent-completion-event shape (status/duration/tokens/cost/child-session-id as *structured* fields, prose as an additional field, not the only field) would make a Wing Ops rollup computable without an LLM having to re-parse prose summaries to extract cost/duration after the fact.

---

## 7. Anti-Theater / Trust — Detecting Claimed-But-Not-Done Work

### What the field does
This is an active, named research area in 2026 — "false success" / "hallucinated completion" / "silent failure" in LLM agents. Core finding, stated plainly across multiple sources: **grading the transcript grades the agent's ability to sound convincing, not its ability to perform work.** "Your flight is booked" in the transcript is not evidence of a booking — the only evidence is querying the airline's actual reservation system.

**Concrete verification patterns found:**
- **Ground-truth anchoring**: success must be measured by querying the actual external system/database/filesystem the agent claims to have changed — never by re-reading the agent's own final message.
- **Reasoning-validation cross-check**: if the transcript shows the agent skipped a validation step but still produced the "right" answer, flag it as unreliable even though the outcome looks correct — this catches success-by-luck / success-via-shortcut before it reaches production, which is subtly different from just checking the final state (a flight *could* get booked by accident of a retry loop; the reasoning path matters for trust even when the outcome is fine).
- **Independent ground-truth labels**: at least one 2026 paper explicitly built ground-truth completion labels *independent of the agent's own language* specifically to catch false-success cases that transcript-only grading would miss.
- **Cross-model verification** (this system's own `integrity_check.verify_and_record()` pattern): dispatch a *different* model/engine to check claims against ground truth, because a model's own self-report is not independent evidence of its own correctness — this is architecturally sound per the literature, not merely a local workaround.

### STEAL THIS
The existing HARD RULE (CC Integrity Double-Check, SO 2026-07-19) is already the textbook version of this pattern — cross-engine, ground-truth-anchored, mandatory before "done." The one addition the literature suggests: also flag **reasoning-skipped-but-outcome-correct** cases as UNVERIFIED even when the ground-truth check passes, since success-via-shortcut in one delegation is a leading indicator the same shortcut will fail next time under slightly different conditions.

---

## Candidate Tools Table

| Tool | Self-hostable? | OSS license? | Python SDK? | Fits solo operator? | What it gives us that we don't have |
|---|---|---|---|---|---|
| **Langfuse** | Yes (Postgres+ClickHouse+Redis, Docker Compose) | Yes (MIT core) | Yes | Yes — designed for small teams, generous free self-host tier | Ready-made trace/observation/score data model + a UI to browse `delegation_outcomes` without building one; LLM-as-judge scoring configurable with no code |
| **Arize Phoenix** | Yes (local or self-hosted, OTel-native) | Yes (fully OSS) | Yes | Yes | Same as Langfuse but leans harder into eval/experiment tracking; pre-built LLM-judge evaluators (hallucination, relevance, toxicity) out of the box |
| **OpenTelemetry (GenAI semconv) + any OTel collector** (Jaeger/Grafana Tempo) | Yes | Yes (CNCF) | Yes (`opentelemetry-python` + OpenLLMetry instrumentation) | Yes, but more assembly required | The actual interoperable wire format — adopt the field *names* even without adopting a full OTel pipeline, so nothing has to be renamed later |
| **AgentOps** | No (hosted; check current OSS status before relying) | Partial | Yes | Yes for lightweight setup | Purpose-built session-level agent traces (multi-turn, tool-heavy) rather than single-call LLM traces |
| **Helicone** | Yes (proxy-based) | Yes (core OSS) | Yes | Yes, very low integration cost | Cheapest possible instrumentation (single endpoint/proxy change) if trace depth isn't the priority |
| **Datadog LLM Observability** | No (SaaS) | No | Yes | Only if already on Datadog | Unifies with infra monitoring — not a fit unless Thunderbird already runs Datadog elsewhere |
| **W&B Weave** | Partial (W&B has a self-managed tier) | No (core product) | Yes | Maybe | MCP auto-logging across frameworks; deep trace + eval integration if already in the W&B ecosystem |
| **Braintrust** | No (SaaS-first) | No | Yes | Maybe | CI/CD-gated eval loops — best if evals need to block a release, less relevant to Thunderbird's continuous-ops model |
| **Comet (Opik)** | Yes (free self-hosting) | Yes | Yes | Yes | OSS eval + observability combined, plus ML experiment tracking if that's ever needed |
| **Maxim AI** | No (SaaS) | No | Yes | Maybe | Structured human-review workflows + agent-simulation/scenario testing — worth a look for pre-deploy SSS rehearsal, not real-time oversight |
| **OpenAI Agents SDK tracing** | No (traces go to OpenAI's dashboard) | Partial (SDK is OSS, backend is not) | Yes | N/A (Thunderbird is Anthropic-centric) | Reference implementation of `guardrail_span`/`handoff_span` naming — useful as a naming-convention reference even if unused directly |
| **Google ADK + Cloud Observability** | Partial (ADK is OSS; backend can be GCP or any OTel-compatible target) | Yes (ADK itself) | Yes | Maybe, given existing Google Suite integration | Already emits OTel GenAI-convention spans natively — could be the fastest path to a real trace backend given Thunderbird's existing Google Workspace footprint |

**Recommendation for this system specifically:** Langfuse or Phoenix, self-hosted, is the best fit — both are free, Python-native, OSS, designed for solo/small-team operators, and both already speak (or are moving toward) the OTel GenAI vocabulary. Given the existing Google Suite integration and Google ADK's native OTel emission, Google Cloud Trace is also a low-friction option if a hosted backend is ever preferred over self-hosting.

---

## Citations

- OpenTelemetry GenAI Semantic Conventions registry: https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
- OpenTelemetry blog, "Inside the LLM Call: GenAI Observability with OpenTelemetry" (2026): https://opentelemetry.io/blog/2026/genai-observability/
- Greptime, "How OpenTelemetry Traces LLM Calls, Agent Reasoning, and MCP Tools" (2026-05-09): https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions
- Uptrace, "OpenTelemetry for AI Systems: LLM and Agent Observability" (2026): https://uptrace.dev/blog/opentelemetry-ai-systems
- Cemri, Pan, Yang et al., "Why Do Multi-Agent LLM Systems Fail?" (MAST), arXiv:2503.13657: https://arxiv.org/abs/2503.13657 / full text https://arxiv.org/html/2503.13657v3
- Anthropic Engineering, "Demystifying evals for AI agents" (Jan 9, 2026): https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic, "How we built our multi-agent research system": referenced via https://lqdev.me/responses/anthropic-how-we-built-multi-agent-system/ and https://blog.bytebytego.com/p/how-anthropic-built-a-multi-agent (orchestrator-worker pattern, 90.2% improvement over single-agent, privacy-preserving structural monitoring)
- Claude/Anthropic, "When to use multi-agent systems (and when not to)": https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
- Langfuse docs, "LLM Observability & Application Tracing": https://langfuse.com/docs/observability/overview ; self-hosting: https://langfuse.com/self-hosting
- Arize AI, "Agent evaluation metrics: how to measure whether an agent works": https://arize.com/resource-hub/agent-evaluation-metrics/
- Arize Phoenix: https://arize.com/phoenix/ ; GitHub: https://github.com/arize-ai/phoenix
- LangSmith observability concepts: https://docs.langchain.com/langsmith/observability-concepts ; LangSmith platform: https://www.langchain.com/langsmith-platform
- LangGraph human-in-the-loop docs: https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- MachineLearningMastery, "Building a 'Human-in-the-Loop' Approval Gate for Autonomous Agents": https://machinelearningmastery.com/building-a-human-in-the-loop-approval-gate-for-autonomous-agents/
- Zylos Research, "Durable Execution for AI Agent Runtimes: Checkpointing, Replay, and Recovery" (2026-04-24): https://zylos.ai/research/2026-04-24-durable-execution-agent-runtimes/
- Mockingly.ai, "Distributed Task Scheduler System Design Interview Guide — Leader Election, Heartbeats & DAGs": https://www.mockingly.ai/blog/distributed-task-scheduler-system-design
- Singhajit, "Lease Pattern in Distributed Systems Explained": https://singhajit.com/distributed-systems/lease/
- Vinay Sharma (Medium), "Dead Letter Queues and Retry Queues: The Safety Net for Distributed Systems": https://medium.com/@vinay.georgiatech/dead-letter-queues-and-retry-queues-the-safety-net-for-distributed-systems-b961c718e6a0
- OpenAI, Agents SDK tracing docs: https://openai.github.io/openai-agents-python/tracing/ ; GitHub source: https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md
- Google, Agent Development Kit (ADK) observability/traces: https://adk.dev/observability/ ; https://adk.dev/observability/traces/ ; Google Cloud instrumentation docs: https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk
- Label Studio, "Ground truth in the age of AI agents": https://labelstud.io/learningcenter/ground-truth-in-the-age-of-ai-agents/
- "From Confident Closing to Silent Failure: Characterizing False Success in LLM Agents," arXiv:2606.09863: https://arxiv.org/pdf/2606.09863
- "Beyond Task Completion: Revealing Corrupt Success in LLM Agents through Procedure-Aware Evaluation," arXiv:2603.03116: https://arxiv.org/pdf/2603.03116
- LangChain blog, "From Token Streams to Agent Streams" (subagent lifecycle event pattern): https://www.langchain.com/blog/token-streams-to-agent-streams
- LangChain docs, deep-agents todo-list frontend pattern: https://docs.langchain.com/oss/python/deepagents/frontend/todo-list
- aimultiple, "15 AI Agent Observability Tools in 2026: AgentOps & Langfuse": https://aimultiple.com/agentic-monitoring
- Latitude, "Best AI Agent Observability Tools in 2026": https://latitude.so/blog/best-ai-agent-observability-tools-2026-comparison
- Braintrust, "Best Weights & Biases alternatives for LLM evaluation": https://www.braintrust.dev/articles/best-weights-and-biases-alternatives-2026
- getmaxim.ai, "Top 5 AI Evaluation Tools" / "Top 5 Arize AI Alternatives" (Maxim AI, Comet Opik comparisons): https://www.getmaxim.ai/articles/top-5-ai-evaluation-tools-in-2025-in-depth-comparison-for-robust-llm-agentic-systems/ ; https://www.getmaxim.ai/articles/top-5-arize-ai-alternatives-compared-2026/

**Uncertainty flags:** OTel GenAI semantic conventions were still marked "Development"/experimental as of mid-2026 per the registry page itself — attribute names may still shift before final stability; treat as directionally correct, not frozen. AgentOps' and W&B Weave's exact current self-hosting/OSS status should be re-verified against their live docs before committing infrastructure to either, since search-result summaries described them inconsistently (partial OSS claims). The MAST prevalence percentages (e.g., FM-2.6 at 13.2%) are from the original 1,642-trace analysis in the paper and may not generalize to Thunderbird's own task mix.
