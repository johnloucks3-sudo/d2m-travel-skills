# WING OVERSIGHT v2 — DESIGN DRAFT (for adversarial review)
**Author:** CC (Claude Opus 5) · 2026-07-29 · **Status:** DRAFT, not approved, not built

---

## 0. The governing constraint

The audit (`intel/oversight_infra_audit_20260729.md`) found **six** oversight
functions with zero callers. CLAUDE.md tells sessions to use all six. None do.
Lost-task detection is structurally incapable of firing because its only intake
(`dispatch_to_oc()`) is never called — yet the daily digest prints green.

**Therefore the design rule for v2:**

> Oversight must be structurally impossible to skip, not merely available to call.
> Enforcement lives in hooks and timers that fire regardless of what a session
> remembers. Any capability that depends on a future session *choosing* to invoke
> it is presumed dead on arrival.

Corollary: **we do not add a seventh honor-system function.** Every component
below must name its non-optional trigger (hook event, systemd timer, or an
existing load-bearing call path) or it does not get built.

Second corollary: **silence ≠ green.** Every rollup must distinguish
"checked and clean" from "nothing was checked." A zero with no denominator is a
lie of omission.

---

## 1. What the Commander asked for → component map

| # | Requirement | Component |
|---|---|---|
| 1 | Visibility into all phases | §2 Span ledger (trace/span/parent tree) |
| 2 | Artifacts of *planned* delegations | §3 Task spec artifact, written pre-dispatch |
| 3 | Interaction between agents/models | §4 Transcript capture (OC gap is the big one) |
| 4 | Assessment of results | §5 Grading stack, ground-truth-anchored |
| 5 | Problems | §6 MAST failure codes (fixed enum) |
| 6 | Lost taskings | §7 Heartbeat + lease + reaper |
| 7 | Exits not accomplished | §7 (same machinery — silent-exit class) |
| 8 | Successful taskings + outputs | §8 Artifact index |
| 9 | Progress bars, timers, todo lists | §9 Live status plane + operator surface |
| 10 | Accountability when an agent fails | §10 Seat scorecard, per-seat, MAST-coded |
| 11 | Brutal regular appraisal | §11 Weekly adversarial review |

---

## 2. Span ledger — the spine

Replace the flat 13-field `Outcome` with an OTel-GenAI-aligned span tree.
The current record cannot express: parent/child, elapsed, tokens, cost, phase,
artifacts, or the spec. All eleven requirements need at least one of those.

**Field names adopted from OTel GenAI semantic conventions** (`gen_ai.*`) so we
are portable to Langfuse/Phoenix later without a migration. *Caveat: the OTel
GenAI conventions are still Development-status and the doc page has moved —
we adopt the naming, not a dependency.*

```
trace_id          # one delegation lineage, root to leaf
span_id
parent_span_id    # THE missing field — makes phases and fan-out visible
seat              # CC | OC | AG
gen_ai.request.model
task_type
phase             # spec | dispatch | work | verify | certify | close
status            # RUNNING | OK | FAILED | LOST | ABANDONED | BLOCKED
mast_code         # fixed enum, §6 — never free text
started_at / ended_at / elapsed_s
heartbeat_at      # §7 — the field that makes LOST detectable
lease_expires_at
gen_ai.usage.input_tokens / output_tokens / cost_usd
spec_ref          # → §3 artifact
transcript_ref    # → §4
artifact_refs[]   # → §8, real paths/commits/URLs
verdict / verified_by / ground_truth_ref
todo[]            # {text, status} — live, §9
```

**Storage:** SQLite (`OpsCenter/wing_spans.db`), not JSONL. Justification: we
need indexed joins by `trace_id`/`ticket_id` across mission_board, silver_ledger,
routing_log — audit gap #6. JSONL cannot do that at 3k+ rows. Keep an append-only
JSONL mirror for the existing brief tooling so nothing that works today breaks.

**Non-optional trigger:** written by hooks (§9), not by voluntary calls.

---

## 3. Pre-dispatch spec artifact

Today the *plan* for a delegation is never durably captured — only AG's prompt,
incidentally, via `routing_log.md`. The Commander explicitly asked for
"artifacts of planned delegations."

Revive `task_templates.py` (currently dead) as the **only** way a dispatch can
be constructed, and have it write the spec to disk *before* work starts:
`OpsCenter/specs/<trace_id>.json` — task, acceptance criteria, ground-truth
source, model, budget, deadline.

Gate: `core.silver.gate.is_checkable()` already exists and already refuses
un-checkable acceptance criteria. Enforce it at dispatch for **all** seats, not
just Flash. No spec artifact → no dispatch.

---

## 4. Transcript capture

`contact_ag.py` already logs full prompt+stdout+stderr (26k lines, real, works).
**OC has no equivalent** — `oc_worker.py::_extract_result()` keeps 300 chars.
CC's own self-execution keeps 100-char excerpts in `posttooluse_audit.py`.

Fix: mirror the `contact_ag.py` append pattern for OC and for CC subagents.
Store under `OpsCenter/transcripts/<trace_id>/`. Cheapest high-value fix in the
whole audit.

---

## 5. Grading stack — three tiers by cost

Per research: LLM judges are 89–97% reliable on binary pass/fail but only ~58%
on categorizing *which* failure occurred.

1. **Deterministic** (free, 100% of outputs): does the claimed artifact exist?
   does the test pass? does the commit exist? did the URL 200? — this catches
   "false success / hallucinated completion" without a model in the loop.
2. **LLM-as-judge, binary only** — and **from a different model family than the
   worker** (the named fix for self-preference bias). CC's work is never graded
   by CC.
3. **Human (Commander)** — calibration only, not routine.

**Grade against ground-truth environment state, never the transcript.** This is
the whole lesson of 2026-07-18 and of this morning's AG-no-citations catch.

---

## 6. Failure taxonomy — adopt MAST wholesale

`arXiv:2503.13657` (UC Berkeley; Cemri, Pan, Yang, … Zaharia, Gonzalez, Stoica).
14 modes, 3 categories, κ=0.88, from 1600+ annotated traces.

- **Cat 1 — Specification & system design**
- **Cat 2 — Inter-agent misalignment**
- **Cat 3 — Task verification & termination**

Our two known incidents map onto Cat 3. Because judge agreement on *category* is
only ~58%, `mast_code` is a **fixed enum assigned by rule where possible**, and a
judge may only propose, never finalize, a code.

Do not invent a Thunderbird taxonomy. We have zero traces; Berkeley has 1600.

---

## 7. Lost / abandoned task detection — heartbeat + lease + reaper

The named production pattern. We currently have the absence-detection half and
none of the staleness half, fed by a dry pipe.

- Worker renews `heartbeat_at` on a cadence.
- Every span carries `lease_expires_at`.
- A **systemd timer** (not a session) reaps: `RUNNING` + stale heartbeat past
  lease → `LOST`, page Commander, record MAST code.
- Distinguish two classes the Commander named separately:
  - **LOST** — no heartbeat, no output, vanished.
  - **ABANDONED** — exited cleanly, work incomplete, no failure declared.
  - *(New third class observed live today: **SILENT_SUCCESS** — work completed,
    report dropped on exit. `infra-audit` did exactly this at 10:08. Currently
    indistinguishable from LOST.)*

**Critical:** the reaper must scan `mission_board.json` and SSS state directly,
NOT only `dispatch_to_oc()` output. Feeding it from one voluntary call site is
the exact bug that made the current detector inert.

---

## 8. Artifact index

`certify_mission_and_record()` already requires a real `verification_artifact`.
Nothing indexes them. Add `artifact_refs[]` on spans + a weekly "what shipped"
view. Low effort, directly answers "successful taskings and outputs."

---

## 9. Live progress — status plane + operator surface

- **CC status file** mirroring `oc_worker.py::write_status()` — CC's in-flight
  work is currently the only seat with no machine-readable state.
- **`todo[]` on the span** — live checklist per delegation.
- **Timers** — `started_at` + `lease_expires_at` gives elapsed vs. budget; that
  is an honest progress bar for non-deterministic work. Do **not** fake a
  percentage; show phase (spec→dispatch→work→verify→certify→close), elapsed,
  and todo burn-down.
- **Surface:** terminal-first (`EXEC: wing` one-screen view). Research shows
  tmux/TUI fleet dashboards are a far smaller lift than a web app — and we
  already decommissioned one web app on 2026-07-18. Google Sheet mirror via the
  retained `tcd` data plane for phone/away access.

**Non-optional triggers — this is what makes v2 different from v1:**
Claude Code hook events already fire on every session, no memory required:
`SubagentStart` / `SubagentStop` → open/close child spans automatically;
`Stop` → refuse to let a "done" claim close a span with no ground-truth check
(this is how `verify_and_record()` finally gets a caller); `PreToolUse`/
`PostToolUse` → already writing 81k lines to `policy_audit.jsonl`, just needs
routing into the span ledger; `UserPromptSubmit` → `directive_ledger.capture()`
gets its missing caller for free.

---

## 10. Accountability — per-seat scorecard

`core/silver/scorecard.py` + `seat_scorecard.jsonl` (87 rows) already exist and
are already called. Extend rather than replace.

Metrics, per seat, MAST-coded:
- **pass^k, not pass@1** (τ²-Bench, arXiv:2506.07982) — same task k times, all k
  must succeed. Real systems score 15–25 pts lower on pass^4. This is the honest
  reliability number.
- **cost per *completed* task** — total spend including retries, judges, and
  escalations, over successful resolutions. Not cost per token.
- First-pass yield · rework rate · escalation rate · verification-pass rate
- Silent-exit rate (LOST + ABANDONED + SILENT_SUCCESS ÷ dispatched)
- Estimate accuracy (elapsed vs. declared budget)

Compounding-failure note for chain design: at 95%/step, 5 steps = 77%,
10 steps = 60%. Short verified chains beat long unverified ones.

---

## 11. Brutal appraisal

Weekly, automated, adversarial by construction:
- Graded by a **different model family** than the seat under review.
- Anchored to ground truth (spans, artifacts, test runs), never self-report.
- Must report the **denominator**: "0 discrepancies / 0 checked" is flagged as
  a failure of the oversight system itself, not as a clean week.
- Includes an explicit **"what did we not verify"** section.
- Names the worst single failure of the week and what it cost.
- Tracks the six-orphans metric: *how many oversight capabilities shipped this
  week have zero callers?* If v2 ever scores > 0 here, v2 is failing.

---

## 12. Explicitly NOT doing

- Not adopting Temporal/DBOS/Restate yet — new infra dependency, and SQLite +
  systemd covers heartbeat/lease/reaper for a 3-seat fleet. Revisit if fan-out grows.
- Not self-hosting Langfuse/Phoenix yet — adopt the *field names* now, defer the
  daemon. (Flagged for Opus: is this the right call, or are we rebuilding a
  worse Langfuse by hand?)
- Not rebuilding a web app. Decommissioned one on 2026-07-18; terminal + Sheet.
- Not inventing a failure taxonomy.

---

## 13. Open questions for adversarial review

1. Is SQLite + systemd genuinely sufficient, or is this NIH vs. Langfuse/DBOS?
2. What breaks when hooks are the enforcement layer — hook failures, recursion,
   latency on every tool call, a hook that blocks legitimate work?
3. Is `pass^k` measurable at our volume (a few tasks/day), or does it need more
   traffic than we will ever have to be meaningful?
4. What is the migration path for `delegation_outcomes.jsonl` (4 rows) and
   `silver_ledger.jsonl` (3,114 rows) without breaking the two live brief engines?
5. What did the Commander *not* ask for that this system will still need?
6. Where will v2 itself become orphan #7?
