# RT·KAIZEN-APPROVE-EXECUTE — Seat Card: HALE-OC (DeepSeek v4)

**Position:** Approval model is right but needs a provenance amendment. Build
`kaizen_runner_oc.py` now with atomic claim. Defer AG executor (flagged gap).
Timer yes. Reject pre-dispatch *content/editorial* gates, keep a technical
leak-pattern pre-check only.

---

## Q1 — Approval model: is "empty gates = pre-approved" still right?

**Verdict: Yes for machine tickets; mostly yes for human tickets — one amendment.**

The underlying model is sound: the approval decision happens at creation,
and `gates` is the Commander's own machine-checkable choke point. Empty
`gates` = nothing requires a human hand before execution. That is not broken
by human submitters showing up.

The real delta is verification, not approval. Tonight's form tickets have
soft `verify_step` values ("A position paper") because the Commander-facing
form runs `require_checkable=False`. A machine-to-machine ticket's
`verify_step` is a real gate; a human's is not. Tonight's failure mode was
"open forever," not "wrong done" — approval already happened; nothing ever
worked the ticket.

**Amendment:** tag each ticket at writeback with `verification: "hard"` (had
a real checkable verify_step) or `"soft"` (human-form ticket). The executor
still dispatches soft tickets — don't stall on them — but the `result` it
writes back is honest about what kind of "done" it is (self-report, not a
mechanically-verified pass). The email loop's contract (`status`, `result`)
doesn't change; this is metadata only. A soft `done` must never be presented
as a verified `done`.

## Q2 — OC-seat executor

**File: `scripts/kaizen_runner_oc.py`** — mirror `kaizen_runner.py`'s shape:
scan `read_open_tickets()` → filter `seat == "OC"` → hard-skip non-empty
`gates` (leave `open`) → atomic claim (`open` → `in_progress` + `claimed_at`,
under a file lock) → dispatch → write back `status`/`result`.

**Dispatch — use the proven pattern, not the wrapped one:**
- Use: `opencode run --model opencode/deepseek-v4-flash-free "<task>"` — the
  raw pattern proven repeatedly tonight. Prompt = the ticket's own task text,
  no generic wrapper competing with the real deliverable.
- Do NOT use `oc_worker.py`/`dispatch_to_oc` — that queue wraps every task in
  a generic "write your summary" prompt that fights the real one.
- Gate every dispatch through `core.relay.oc_hygiene.before_dispatch()`
  (`MAX_CONCURRENT=2`) — run strictly sequential, one ticket at a time, to
  respect that shared cap.
- Sandbox: OC blocks read/write outside the repo without `--auto` — not
  relevant here since tickets/results are in-repo. Stay in-repo only, no
  `--auto`.

**Diffs from the CC runner:**

| Aspect | CC runner | OC runner | Why |
|---|---|---|---|
| Dispatch | `run_local_claude()` | raw `opencode run --model deepseek-v4-flash-free` | the working, minimal path |
| Concurrency | n/a | `before_dispatch()`, strictly sequential | keeps `MAX_CONCURRENT=2` for the whole lane, avoids re-entrancy |
| Timeout | 600s | ~180-300s | flash model is quick; a hang isn't real work |
| Self-report trust | higher (CC↔OC loop) | lower on soft tickets — tag `verification: soft` per Q1 | human-form provenance |
| `result` writeback | same shape | identical shape | the email loop is the contract, don't change it |

## Q3 — AG-seat executor: now or defer?

**Verdict: deliberate v1 gap — defer, but flag loudly, don't leave it silent.**

Unattended AG dispatch is a different integration from the OC clone-and-run:
OC's direct-command pattern is proven; CC has a local headless path with MAX
discipline; AG's `contact_ag.py` is built for peer-to-peer, interactive use
and has never been validated for a timer-driven, no-human-watching run.

Cheap correct move for v1: route any AG-seat ticket into the same "left
open for human review" bucket as a gated ticket — every AG ticket gets a
clear disposition (surfaced, not silently orphaned), even though nothing
executes it yet. Flag explicitly in the synthesis: "AG-automation gap,
scoped for v2 once a real headless AG path is validated."

## Q4 — Scheduling and re-entrancy

**Verdict: yes, one systemd timer per seat — but atomic claiming is the
actual requirement, the timer is just what triggers it.**

**Cadence:** stagger CC and OC runners (e.g. offset by 15 min within a
30-min tick) so they never contend for the same tickets directory at once.

**Re-entrancy — non-negotiable:**
1. **Atomic claim:** transition `open` → `in_progress` (+ `claimed_at`,
   `claimed_by`) under a file lock, written BEFORE dispatch starts. The scan
   only ever selects `status == "open"` — a mid-flight ticket is invisible
   to the next tick, never double-dispatched.
2. **Orphan reclaim:** any ticket stuck `in_progress` longer than ~2x the
   runner's own timeout (a crashed/OOM'd run) gets reset to `blocked` with a
   `"timeout — orphaned claim reclaimed"` result, not left stuck forever.

If the runner sits idle for a week doing nothing, that's a lateness problem,
never a double-dispatch problem — the design should fail toward "late," not
toward "run twice."

## Q5 — Content guardrail on auto-dispatch

**Verdict: no content/editorial pre-check. One technical pre-check, reusing
what already exists, not a new one.**

A ticket's political or subjective framing is not a security event — the
executing model exercises normal judgment on subjective asks the same way
it would in a live chat. A tone/content filter here is decoration that
degrades trust for zero real protection.

What IS worth a pre-dispatch technical check: the same leak-pattern list
`kaizen_email_loop.py` already uses (credential patterns, absolute home
paths) — but as a *skip, not block*: if a ticket's own spec text already
contains something that pattern-matches, leave it `open` and route it to a
human rather than silently either running it or hard-rejecting it.

## Summary

| Decision | Position |
|---|---|
| Q1 approval model | Keep 2-tier; add `verification: hard/soft` tag |
| Q2 OC executor | `scripts/kaizen_runner_oc.py`, raw `opencode run`, sequential, atomic claim |
| Q3 AG | Defer, flag loudly, route to human-review bucket like a gated ticket |
| Q4 scheduling | Per-seat timer, staggered; atomic claim + orphan reclaim is the real requirement |
| Q5 guardrail | No content/political filtering; reuse the existing leak-pattern check as skip-not-block |

— HALE-OC (DeepSeek lane)
