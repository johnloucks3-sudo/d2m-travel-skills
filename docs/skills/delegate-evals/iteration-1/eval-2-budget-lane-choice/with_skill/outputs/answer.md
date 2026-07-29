# Routing: refactor + auth security review, 70% weekly limit / 30h left

## Bottom line

Neither job runs on the CC/MAX bucket as a self-execute. Budget is the binding
constraint (70% burned, 30h left), so both go to free lanes, with CC narrowed to
spec-writing and verification only.

- **Refactor → OC** (DeepSeek Zen, free tier) — mechanical work, explicit boundaries.
- **Auth security review → AG** (Talon), forced to `"Claude Sonnet 4.6 (Thinking)"` —
  needs Claude-grade judgment but not CC's own hub context, so it's billed on
  Google's side, off the MAX meter entirely (per the Commander's 2026-07-29
  directive on Sonnet-off-the-meter routing).
- **CC keeps:** writing both acceptance-criteria specs, verifying both deliverables
  against ground truth, and any judgment call neither lane can make alone.

This is the routing instinct the skill calls out directly: a security review is
exactly the thing you'd feel exposed sending with no second opinion — that's the
signal to hand it to an independent engine, not keep it on the engine that (likely)
wrote or will touch the code.

## Why not self-execute either one

At 70% with 30h left, every self-executed CC task spends down a bucket that
doesn't refill until the week rolls. A "big refactor" is large and mechanical
enough that most of it doesn't need Claude-grade judgment — paying MAX-bucket
rates for mechanical work is the expensive way to do it. The security review
does need real reasoning, but reasoning is available off-meter through AG's
Sonnet fallback, so there's no reason to spend MAX on it either.

If either job turns out to need CC's own accumulated context (this repo's history,
prior decisions already in this session) rather than just capability, that's the
one case for pulling it back to CC — see "Escalation" below.

## Refactor → OC

**Spec requirements before dispatch (per `core/relay/task_templates.py:build_oc_task`,
checked against `core.silver.gate.is_checkable()`):**

- **Include:** exact file/module paths in scope for the refactor — list them, don't
  say "the codebase."
- **Exclude by name:** `node_modules`, `.venv`, `archive`, generated/build output,
  test fixtures, anything where the pattern being refactored appears as *data*
  rather than *code*.
- **Starting directory:** open the ticket with the `cd` into the actual repo root —
  don't assume OC lands where CC is standing.
- **Mechanically checkable acceptance criteria** — not "refactor thoroughly":
  - `python3 -m py_compile <each touched file>` exits 0 (or the language-appropriate
    equivalent — lint/typecheck/build)
  - existing test suite passes: exact command, e.g. `pytest -q` exit 0
  - a diff-scope check: touched files are a subset of the Include list, nothing in
    Exclude was touched
  - if the refactor has a target shape (e.g., "eliminate direct `X()` calls"),
    `grep -rc` for the old pattern outside the exclude paths returns 0 — this is
    the "value that can only be right if the work was really done," not just a
    schema match.

**Dispatch:** `core.relay.dispatch_oc.dispatch_to_oc()` (async, ticket + SLA) —
never the raw worker. Before trusting the "free" label, confirm what
`scripts/oc_worker.py` actually invokes for this ticket — if it shells out to
`claude -p` under the hood for this task type, it's silently spending the MAX
bucket and the whole point of routing here is gone. Check the model, not the
name on the service.

**Verification (CC does this, not OC's self-report):** run the acceptance
commands above directly against the resulting branch/diff. A report of
"refactor complete, tests green" is a claim; `pytest` actually exiting 0 in this
session is the fact. Follow `core.staffing.integrity_check.verify_and_record()`
if it needs to be logged as a certified deliverable, not the raw verify function.

## Auth security review → AG

**Why AG and not OC:** DeepSeek/Zen is the mechanical lane; a security review of
an auth module is judgment-heavy and adversarial by nature — exactly AG's
assignment ("independent review, verification, adversarial critique"). It also
should not be reviewed by whichever engine wrote or is refactoring the auth code
in parallel — an independent engine catches what the author's blind spots miss.

**Model:** force `"Claude Sonnet 4.6 (Thinking)"` explicitly via `contact_ag`
(not the default Gemini 3.1 Pro, not the agy default GPT-OSS 120B — GPT-OSS
hallucinates and this is the last domain to accept that risk). This gets
Claude-grade security reasoning while billing Google's side of the ledger, not
Anthropic's — the exact use case the Commander's Sonnet-off-the-meter guidance
describes.

**Spec requirements:**

- **Include:** exact path(s) to the auth module (files, not "auth-related code").
- **Exclude:** anything outside auth scope creep — don't let the review wander
  into the refactor's touched files unless auth code overlaps; if it does
  overlap, say explicitly whether AG should review pre- or post-refactor state
  (avoid reviewing a moving target — sequence this after the refactor's diff is
  final, or pin to a commit SHA).
- **Deliverable:** absolute path for the write-up (`--deliverable` flag — AG's
  relative paths land in her brain sandbox, not the repo).
- **Checkable acceptance criteria for the review itself:** every finding must
  cite a concrete file:line; a finding with no line reference doesn't count.
  Require a severity tag per finding (critical/high/med/low) and, for anything
  tagged critical/high, a minimal reproduction or exploit sketch — this keeps
  the review from being prose-only ("looks fine") the way a TCD close comment
  without a concrete reference gets bounced.
- **Command:** `--print-prompt-only` first to check tone/scope before firing.

**Verification (CC does this):** don't accept the findings list as ground truth.
Spot-check at least the critical/high findings directly — read the cited
file:line, confirm the vulnerability class is real, not a hallucinated pattern
match. If AG reports zero findings, that is the "perfect record is a warning"
case in the skill: a clean auth module and an unchecked review both produce that
report, so re-run one adversarial pass with a different framing (auth bypass,
token replay, session fixation) before accepting zero as the answer.

## What CC does directly (not delegated)

- Write both specs above before dispatch — this is CC's job, not something to
  hand off, since a weak/independent model won't infer scope boundaries you
  didn't write down.
- Verify both deliverables against ground truth commands, not self-reports.
- Any single judgment call that needs this session's accumulated context (e.g.,
  "does this refactor conflict with a decision made earlier this week") stays
  with CC — that's the one legitimate reason to spend MAX bucket here.

## Recording

Log both dispatches through the recording wrappers, not the raw calls:
- `core.relay.dispatch_oc.dispatch_to_oc()` for the refactor ticket.
- `core.staffing.delegation_outcomes.record_outcome()` for both outcomes —
  PASS/DISCREPANCY/UNVERIFIED, logged even (especially) if either comes back
  wrong. If OC's SLA lapses or the ticket goes unclaimed,
  `core.relay.reconcile_oc.reconcile_due()` should catch it as DROPPED/STALLED
  rather than letting it silently re-queue.
- If self-executing any slice of either job on CC despite this routing (e.g.,
  the judgment call above), log `self_execute_rationale` via
  `delegation_outcomes.record_outcome(action="self_executed", ...)` so it
  doesn't show up as `self_execute_unjustified` in the daily rollup.

## Escalation trigger (route back to CC)

If OC's refactor keeps failing the mechanical checks after 2-3 rounds, or AG's
review keeps producing ungrounded findings, that's the "suspect configuration
first" case — check the timeout given (mechanical refactors need real wall-clock,
not a 4-minute window) and confirm which model actually answered, before
concluding either lane can't do the work and pulling it onto the MAX bucket.
