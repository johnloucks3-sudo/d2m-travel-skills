# POSITION PAPER — KAIZEN Ticket Approve & Execute
## RT-KAIZEN-APPROVE-EXECUTE · CC synthesis of CC + AG + OC

**BLUF:** The gap the Commander found live-testing tonight is real: tickets
sit `open` forever because nothing works them — `kaizen_runner.py` only
handles CC-seat tickets and is still `--dry-run`; there is no OC or AG
executor at all. AG and OC converge on 4 of 5 design questions; one real
refinement adopted from OC over AG. Plan follows separately, on screen, for
approval — nothing executes yet.

---

## Q1 — Is "empty gates = pre-approved" still the right model?

**Yes, unchanged — the gap is verification, not approval.** Both AG and OC
independently reached the same conclusion: the approval decision already
happens at ticket-creation time (an empty-`gates` ticket IS pre-approved for
unattended execution; a gated one needs a human, no exceptions). Tonight's
failure was never "wrongly approved" — it was "approved, then never worked."

**One real refinement, adopted from OC over AG's alternative:** human-
submitted tickets (via the Commander-facing form, `require_checkable=False`)
carry soft, unverifiable `verify_step` text ("A position paper"). AG's
proposal was to accept "exit code 0 + >50 characters" as a done-heuristic.
CC's call: **reject that — it's an arbitrary threshold that could pass
garbage.** OC's alternative is cleaner and matches this wing's own standing
rule (never upgrade an unverified claim to "done"): tag the ticket
`verification: "hard"` (real checkable verify_step) or `"soft"` (human-form
ticket) at writeback. The executor still runs soft tickets — no stalling —
but the `result` it writes is honest about what kind of "done" it is. The
email loop's contract doesn't change.

## Q2 — OC-seat executor

**Build `scripts/kaizen_runner_oc.py`**, mirroring `kaizen_runner.py`'s
shape exactly: scan → filter `seat=="OC"` → hard-skip non-empty `gates` →
dispatch → write back `status`/`result`. AG and OC agree closely on
mechanics; OC's version adopted as primary since it verified the real
dispatch code live:
- Dispatch via the proven direct pattern: `opencode run --model
  opencode/deepseek-v4-flash-free "<task>"` — never the `oc_worker.py`/
  `dispatch_to_oc` queue (wraps every task in a generic prompt that fights
  the real deliverable — confirmed failure mode from earlier tonight).
- Gated through `core.relay.oc_hygiene.before_dispatch()`
  (`MAX_CONCURRENT=2`), run sequential — one ticket at a time.
- Timeout: 300s (AG's figure — DeepSeek is fast; a hang past that isn't
  real work).
- `verification: "soft"` tagged per Q1 on every ticket this runner touches
  (all form-submitted OC tickets are soft by definition).

## Q3 — AG-seat executor

**Defer to v2 — both AG and OC independently agree.** Unattended AG
dispatch is a different integration than OC's proven clone-and-run:
`contact_ag.py` is built for peer-to-peer interactive use, never validated
for a timer-driven, no-human-watching run. Building it blind risks a worse
failure than the current gap.

**Not a silent gap, though:** any AG-seat ticket routes into the same
"left open for human review" bucket as a gated ticket — visible and
flagged, not orphaned. v2 scope: validate a real headless AG path first,
then clone the same executor shape.

## Q4 — Scheduling & re-entrancy

**One systemd timer per seat** (`kaizen-runner-cc.timer`,
`kaizen-runner-oc.timer`), 5-minute cadence, matching the existing
`kaizen-email-loop.timer` family. Since each runner only ever touches its
own seat's tickets, CC and OC runners never contend with each other —
staggering between seats isn't needed.

**Re-entrancy — synthesized from both papers, this is the actual
requirement, the timer is just what triggers it:**
- A single non-blocking process lock per script (`fcntl.flock` on a
  dedicated lock file, AG's proposal) at startup — if a prior invocation of
  the *same* script is still running, the new tick exits immediately. This
  is the real double-dispatch prevention.
- An `in_progress` status + `claimed_at` timestamp written to the ticket
  file before dispatch starts (OC's proposal) — a visible signal, and the
  safety net if a run ever crashes without releasing its lock cleanly.
- **Orphan reclaim:** any ticket stuck `in_progress` longer than 2x the
  runner's own timeout gets reset to `blocked` with a
  `"timeout — orphaned claim reclaimed"` result — never left stuck forever.
- Design bias: fail toward *late*, never toward *double*.

## Q5 — Content guardrail before auto-dispatch

**Unanimous, adopted as-is: no content or political/editorial filtering.**
Both AG and OC independently and strongly rejected this — a ticket's
subjective or politically-framed content is not a security event; the
executing model exercises the same judgment it would in a live chat.
Filtering tone here is decoration that degrades trust for zero real
protection — matches this wing's existing posture on client-facing work.

**What IS worth a pre-dispatch check:** the same technical leak-pattern
list `kaizen_email_loop.py` already uses (credential patterns, absolute
home paths) — reused, not reinvented — as a **skip-not-block**: if a
ticket's own spec text pattern-matches, leave it `open` and route to a
human rather than either silently running it or hard-rejecting it.

---

*Full unedited seat cards: `ag_hale_input.md`, `oc_hale_input.md`,
`cc_hale_input.md` in this same RT session directory.*
