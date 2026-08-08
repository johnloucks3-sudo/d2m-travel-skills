BLUF: Commander found a real gap live-testing tonight — tickets sit `open`
forever. `kaizen_runner.py` exists but is CC-seat-only and still `--dry-run`
(deliberately held back); there is no OC-seat (or AG-seat) executor at all.
He wants this designed via RT: how does a ticket actually get approved and
worked, end to end, on a real schedule, for CC/OC/AG.

## Ground truth already on disk — build on this, don't re-derive

- `scripts/kaizen_runner.py` (built earlier tonight): scans
  `read_open_tickets()`, filters `seat=="CC"` only, **hard safety gate**: any
  ticket with non-empty `gates` is SKIPPED (left `open` for Commander review)
  — only empty-gates tickets are eligible for unattended execution. Dispatches
  via `run_local_claude()` (the proven headless pattern). On success sets
  `status="done"` + `result`; on failure/timeout `status="blocked"` + `result`.
  `--dry-run` default, `--live` does the real thing. **This is the existing
  approval model**: approval already happened at ticket-creation time — an
  empty-`gates` ticket IS pre-approved for autonomous execution by design;
  only a gated ticket needs a human to look at it. If that model is wrong or
  incomplete, say so explicitly — don't just assume it and build past it.
- `core/email/kaizen_email_loop.py` (built + live tonight): the OTHER half —
  once a ticket has `status in (done, blocked)` and a `result`, this answers
  it by email (draft-only unless `verified_reply`). Already live, already
  correct, not in scope to redesign — just note it as the downstream consumer
  any new executor needs to feed correctly (same `result` field name, same
  `status` values).
- OC's real dispatch mechanics (used successfully many times tonight):
  `opencode run --model opencode/deepseek-v4-flash-free <prompt>` directly
  (NOT the `dispatch_to_oc`/`oc_worker.py` queue — that path wraps every task
  in a generic "write your summary" prompt that competes with a real one).
  Gate every dispatch through `core.relay.oc_hygiene.before_dispatch()`
  (concurrency cap, MAX_CONCURRENT=2). OC's sandbox blocks all read/write
  outside this repo without `--auto` — never relevant here since tickets and
  results are all in-repo (`OpsCenter/tickets/`).
- The tickets submitted live tonight during testing are human-typed, `seat`
  varying (CC/OC/AG all offered on the form), `verify_step` often soft
  ("A position paper", "An email with all details available") because
  `require_checkable=False` applies to the Commander-facing form (a HARD
  gate for machine-to-machine tickets, deliberately relaxed for a human
  typing into a form). **This matters for design**: an auto-executor can't
  mechanically verify a human ticket's "done" the hard way — it has to trust
  the executing model's own self-report more than the CC↔OC ticket flow does.
  Flag this tension, don't paper over it.

## Real questions for the design — answer explicitly

1. **Is "empty gates = pre-approved, gated = needs a human" still the right
   approval model**, now that real humans (not just OC/AG) are submitting
   real tickets through a form, sometimes with soft/unverifiable asks? Or
   does a human-submitted ticket need a different bar than a machine-to-
   machine one? Say what you'd change, if anything, and why.
2. **OC-seat executor — design it.** Mirror `kaizen_runner.py`'s shape
   (scan → filter by seat → gate-check → dispatch → write back `status`/
   `result`) but using the real direct-OC-dispatch pattern above, not the
   `oc_worker.py` queue. Name the file. What differs from the CC version
   and why (timeout, dispatch mechanics, anything else)?
3. **AG-seat executor — needed or not?** The form offers AG as a seat option
   but nothing executes AG tickets either. Is this in scope now, or a
   deliberate v1 gap to flag and defer? Give your reasoning either way.
4. **Scheduling.** Should either executor become a real systemd timer (like
   `kaizen-email-loop.timer`) so tickets get worked without a live human
   session, or should execution stay manually-triggered for now given tonight
   already surfaced one real gap (auto-verification weakness on human
   tickets)? If a timer: what cadence, and what happens if a ticket is
   mid-flight when the next tick fires (re-entrancy)?
5. **Content/quality guardrail before auto-execution.** Some of tonight's own
   test tickets carried loaded political framing in the task text. Should an
   auto-executor have any pre-dispatch content check (separate from
   `kaizen_email_loop.py`'s existing post-answer guardrail, which only
   blocks credential/path leaks, not content quality/appropriateness)? Or is
   that out of scope — the model doing the work already exercises judgment,
   and a bad answer is a bad answer, not a security problem?

Write your own position-paper card. CC will synthesize all three (cross-
checked against real files/commits, same discipline as tonight's other two
RT syntheses) into one document, plus a build plan shown on screen — no
execution starts until the Commander approves it.
