# Cross-Hale Delegation — Existing-Software Survey

**Date:** 2026-07-16 · **Author:** Research pass (CC/Hale) · **Commander directive 2026-07-16**
**Companion to:** `docs/CROSS_HALE_TASK_DELEGATION_DESIGN_20260716.md` (bespoke design — **did not exist at time of this survey**; see Reconciliation).
**Scope:** Survey off-the-shelf software (open-source or otherwise) that solves some/all of the CC↔OC↔AG headless task-delegation problem, so the bespoke design does not reinvent a solved wheel. **No implementation in this pass.**

---

## TL;DR — Recommendation

**Hybrid, build-light. Do NOT adopt a heavyweight orchestrator or distributed queue.**

1. **Transport:** Keep the existing file relay (`OpsCenter/relay_send.py` + `relay_queue.jsonl` + per-seat inbox `.md`), OR the equivalent `a2a_*` MCP tools — they are the same pattern. Pick one and retire the other; do not run two parallel transports.
2. **State + verification (the part nothing off-the-shelf gives you):** Add a single **SQLite `delegations` table** with an explicit lifecycle (`queued → claimed → running → self_reported → verified/failed`) and, critically, a **per-task verification predicate** that runs *after* the worker claims done and is asserted by something other than the worker (expected artifact exists and is non-empty? grep/check passes? commit landed? exit code 0 AND output file mtime advanced?).
3. **Skip:** Temporal, Airflow, Dagster, Prefect, Celery, dramatiq (all need a broker/server and buy nothing over SQLite on one laptop); LangGraph/CrewAI/AutoGen/Swarm/MetaGPT (they route across *model providers*, not across *different CLI agent tools* — you'd wrap the CLIs yourself anyway).

**The load-bearing insight:** No queue or orchestrator solves "fabricated SUCCESS." Every one of them marks a task `succeeded` when the worker returns without raising — that *is* the self-report you already cannot trust. The fabricated-SUCCESS pain lives at the ground-truth layer and can only be closed by a task-specific verification check you write yourself. This is the same critique that applies to the current relay/a2a, and it applies equally to Temporal. Adopting a heavy queue is therefore a *category error* against this specific directive: it moves the risk, it does not remove it. (Consistent with SO 2026-07-06 verify-vs-ground-truth and the credential-doomsday false-alarm doctrine.)

---

## 1. Ground truth — what already exists in this repo

Three overlapping transports already exist, all the **same shape** (append a message/task block to a file; a poller picks it up; status is a self-reported flag):

| Artifact | What it is | Verification? |
|---|---|---|
| `OpsCenter/relay_send.py` (301 ln) | `enqueue()` → `relay_queue.jsonl`, and fan-out writers `_write_oc_inbox` / `_write_cc_inbox` / `_write_ag_inbox`. **AG lane added tonight** (`antigravity_inbox.md`). | **None.** `mark_processed()` just flips `status: pending → processed`. |
| `OpsCenter/relay_queue.jsonl` (631 ln) | Message bus. Schema: `{id, from, to, ts, priority, message, status}`. `status ∈ {pending, processed}`. | **None.** No `result`, no `verified`, no artifact pointer. It is a *chat log*, not a *task ledger*. |
| `core/ai_infra/thunderbird_a2a_protocol.py` — `a2a_create_task` / `a2a_task_status` MCP tools | For `CLAUDE`/`OPENCODE` targets: appends a `## … A2A TASK` block (`status: UNREAD`) to the same inbox `.md` files and returns `state: submitted`. For other personas: runs `call_persona()` **in-process on the same model** (a persona prompt, not a different CLI). **No AG target exists.** Also carries a copy-paste bug: the `CLAUDE` branch header prints `## OPENCODE A2A TASK`. | **None** for the CLI relay path. The SQLite `a2a_tasks.db` tracks `submitted→working→completed/failed` for the *in-process persona* path only, and "completed" = "the executor coroutine returned" = self-report. |

**Both CLIs are installed and dispatchable:** `agy` (`~/.local/bin/agy`, 186 MB, installed Jul 15), `opencode` (`~/.opencode/bin/opencode`), `claude` (`~/.local/bin/claude`). So the "workers" are **three heterogeneous CLI processes**, not a homogeneous Python worker pool — this single fact disqualifies most of the queue libraries below (they assume you import task *functions* into their workers).

**Conclusion for §3 of the directive:** the `a2a_*` tools are **not** an under-utilized ready solution — they are *under-built*. They are the same inbox-file relay with a `submitted`/`UNREAD` flag, minus an AG lane. Use them (or the relay) as dumb transport; do not expect them to solve verification.

---

## 2. Multi-agent orchestration frameworks

**Directive question:** do any route tasks to *different underlying model backends/CLIs*, not just different prompts to one model?

**Short answer: No — none of them treat "a different CLI agent tool" as a first-class swappable worker.** They all abstract over **model providers** (an LLM client: OpenAI, Anthropic, Gemini, a local endpoint). To send work to CC vs OC vs AG you would write a custom tool/node that shells out to each CLI — i.e., you build the exact adapter you'd build anyway, and inherit a framework's runtime, state model, and version churn on top. For a 3-CLI home lab this is negative ROI.

| Framework | Routing model | Fit for "route to CC/OC/AG CLIs" | Verdict |
|---|---|---|---|
| **LangGraph** | Graph of nodes over LLM clients; durable checkpointer (SQLite/Postgres). | Nodes call *models*, not CLIs. You'd wrap each CLI as a node yourself. Its checkpointer is genuinely nice for resumable state — but that's the one piece we can replicate in ~30 lines of SQLite. | **Skip.** Closest to useful (checkpointer), still overkill; adopt the *idea* (durable state), not the dependency. |
| **CrewAI** | Role-playing "agents" = personas over one/few model clients. | Personas-on-a-model — exactly the pattern we already have with `call_persona`. No CLI-backend routing. | **Skip.** Duplicates existing persona layer. |
| **AutoGen / AG2** | Conversational multi-agent; `ModelClient` abstraction. Microsoft has been **converging AutoGen + Semantic Kernel into the "Microsoft Agent Framework."** | Abstraction is over model clients. Heavier conceptual surface; in flux due to the merge. | **Skip.** Provider-level, plus a moving target. |
| **Microsoft Semantic Kernel (agent orchestration)** | Enterprise .NET/Python agent + plugin orchestration; merging as above. | Enterprise-weight; provider-level routing. | **Skip.** Enterprise overkill. |
| **OpenAI Swarm** | Original lightweight handoff demo — **superseded by the OpenAI Agents SDK**; Swarm is effectively archived/educational. | Even the successor routes across OpenAI-style model clients, not foreign CLIs. | **Skip.** Deprecated; wrong abstraction anyway. |
| **MetaGPT** | Opinionated "software company" SOP multi-agent. | Fixed role SOP over model clients; not a general dispatch bus. | **Skip.** Wrong problem shape. |

**Net:** the requirement ("different CLI tools with different capabilities as workers") is *outside* the design center of every one of these. They solve "coordinate multiple personas/roles talking to model APIs." We already have that (personas + `call_persona`). None removes the verification gap.

---

## 3. General task-queue / workflow-orchestration systems

**Directive question:** could one be the backbone instead of hand-rolled `relay_queue.jsonl` polling? Assess realistically for a single-user home lab.

**The decisive point:** all of these mark a task **succeeded when the worker function returns without raising.** That is precisely the "SUCCESS theater" failure — the worker *reporting* success. They give you retries, backoff, dead-letter, and dashboards, which are real, but they do **not** give you *independent completion verification*. You still have to write the ground-truth check yourself, and once you've written it, the heavy runtime earns little.

| System | Weight on one laptop | Solves verification? | Verdict |
|---|---|---|---|
| **Temporal** | Server + persistence + workers; durable workflows are excellent. Heavy to stand up/operate solo. | No — a workflow "completes" when the activity returns. Determinism/replay ≠ ground-truth check. | **Skip.** Enterprise-grade durability for a problem whose hard part it doesn't touch. |
| **Airflow** | Scheduler + metadata DB + webserver; DAGs are batch/cron-shaped, not ad-hoc task handoff. | No. | **Skip.** Wrong shape (scheduled DAGs) and heavy. |
| **Dagster** | Asset-oriented, server + daemon. | No. | **Skip.** Data-pipeline framing; overkill. |
| **Prefect** | Lightest of the "real" orchestrators; can run local, nice retries/observability. | No — a flow succeeds on non-exception return. | **Closest of the heavies**, still more runtime than a 3-CLI laptop needs; verification still DIY. **Skip** unless a dashboard becomes a hard requirement. |
| **Celery** | Needs a broker (Redis/RabbitMQ) = real friction. Workers import Python task functions. | No. | **Skip.** Broker + homogeneous-worker assumption both wrong here. |
| **dramatiq** | Lighter than Celery but still wants a broker (Redis/RabbitMQ). Homogeneous workers. | No. | **Skip.** Same broker/worker mismatch. |

**Integration-cost reality:** every one of these still leaves dispatch as *your* subprocess wrapper around `claude -p` / `opencode` / `agy`, because the job is "shell out to a foreign CLI," not "run an imported Python function." So the library buys you queue+status+retry only — and SQLite + a systemd timer already give queue+status+retry at a fraction of the operational cost, with **zero** new daemons/brokers to keep alive (this repo already fights daemon flap; see restart_flap_detector).

---

## 4. Lightweight single-machine job queues

| Option | Notes | Verdict |
|---|---|---|
| **huey (SQLite backend)** | Can run broker-less on SQLite; simplest of the "real" libraries. Still imports task functions into its consumer; still marks success on return. | **Marginal.** If you insist on a library, this is the one — but it adds a consumer process and a decorator model for ~what a SQLite table + timer already does. **Prefer the table.** |
| **A `delegations` table in an existing SQLite DB** (e.g. alongside `a2a_tasks.db`) | Rows: `id, task_type, target_seat (CC/OC/AG), prompt, deliverable_path, verify_cmd, state, worker_pid, claimed_at, self_reported_at, verified_at, attempts, last_error`. Drained by a systemd timer that already exists in this fleet. | **RECOMMEND.** Purpose-built, no new runtime, and it is the natural home for the verification predicate the whole directive is about. |
| **RQ / arq / SAQ / TaskIQ** | All need Redis (or similar). | **Skip.** Broker friction, no verification win. |

---

## 5. CLI-specific interop / standards

- **Claude Code SDK / plugins / subagents:** the SDK gives you programmatic headless invocation of *Claude* (and this repo already has `headless_claude_spawn` + `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md`). It is a way to *dispatch to CC*, not a cross-vendor router. Subagents are Claude-internal.
- **Google A2A protocol:** this repo already implements the Google A2A spec server-side (`thunderbird_a2a_protocol.py`). A2A is a *discovery + task-message envelope* standard (agent cards, task states submitted→working→completed). It standardizes the *envelope*, not *verification* — "completed" is still whatever the callee asserts. Useful as the wire format if you want one; not a solution to the trust problem.
- **opencode a2a (`a2a_ask` / `a2a_broadcast` / `a2a_create_task`):** in *this* codebase these are the MCP tools backed by the two files above; for CC/OC they are the inbox-file relay (§1). Not an external standard that closes the gap.

**None of the CLI-vendor interop surfaces publishes a "verify the other agent actually did the work" mechanism.** That is inherently task-specific and stays on us.

---

## 6. Recommended architecture (build-light hybrid)

```
Hale (any seat) ──► delegate(task_type, prompt, target?, deliverable_path, verify_cmd)
       │
       ├─ router: task_type/complexity → seat (CC=judgment/client-safe, OC=ops/mechanical, AG=Gemini/long-context)
       │           (reuse existing keyword_router.py policy; add a seat-capability map)
       │
       ├─ INSERT row into SQLite `delegations` (state=queued)
       │
       ├─ TRANSPORT (reuse, don't rebuild): relay_send.enqueue()/inbox OR a2a_create_task
       │
       ▼
   Worker CLI (claude -p / opencode / agy) runs, writes deliverable, sets state=self_reported
       │
       ▼
   VERIFIER (systemd timer, runs as NOT-the-worker):
       run verify_cmd  →  artifact exists & non-empty? check passes? commit landed? exit 0?
       PASS → state=verified   FAIL → state=failed, attempts++, escalate at N (circuit breaker)
```

**What this buys that nothing off-the-shelf does:** the `verify_cmd` gate is the antidote to fabricated-SUCCESS logs. A row cannot reach `verified` on the worker's say-so; an independent check must pass. Circuit-breaker on `attempts` gives the missing "no silent infinite retry / no SUCCESS theater" behavior. All of it is ~a few hundred lines of Python + one systemd timer + one SQLite table — no broker, no server, no new daemon class to keep alive.

**Effort estimate:** ~1 focused session. The transport already exists; the router policy largely exists (`keyword_router.py`); the only genuinely new thing is the `delegations` table + verifier loop — which is also the only thing that actually solves the stated problem.

---

## 7. Reconciliation with the parallel bespoke design

At time of writing, `docs/CROSS_HALE_TASK_DELEGATION_DESIGN_20260716.md` **did not yet exist** on disk — the parallel design agent had not landed it. There was therefore nothing to agree or disagree with. This survey's stance for that design to check itself against:

- **Agree if the design says:** reuse existing transport (relay or a2a), add a SQLite task ledger, and make completion contingent on an independent verification check + circuit breaker.
- **Flag as a category error if the design proposes:** adopting Temporal/Airflow/Dagster/Prefect/Celery, or a multi-agent framework (LangGraph/CrewAI/AutoGen/Swarm/MetaGPT), as the *backbone* — because none of them close the verification gap, and all add operational weight this single-laptop system does not need.
- **Fix regardless:** wire an AG lane into `a2a_create_task` (today only CC/OC exist), and the `## OPENCODE A2A TASK` header copy-paste bug in the CLAUDE branch of `thunderbird_a2a_protocol.py`.

---

*Survey only — no code changed. Files referenced: `OpsCenter/relay_send.py`, `OpsCenter/relay_queue.jsonl`, `core/ai_infra/thunderbird_a2a_protocol.py`, `core/ai_infra/thunderbird_a2a.py`.*
