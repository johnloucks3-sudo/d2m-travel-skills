# WING OVERSIGHT v2 — STATUS & ROADMAP
**2026-07-29 · CC (Claude Opus 5)** · commits `98009dd1d`, `c3ef4e73c` · 124 tests passing

---

## 🔴 OUTSTANDING — COMMANDER ACTION REQUIRED

**Loucks Grandeur FPD — $24,798 due August 1 (3 days).** Dossier
`Loucks_Regent_Grandeur_3122006.md` confirms **UNPAID**, Harlan sign-off against
a Regent portal scrape. Gate 2 (financial commitment) — Commander only.
Detected twelve separate times since Jul 15 (MISSION-052, 666, 677, 686, 697,
704, 714, 720, 726, 735, 740, 746) and never once closed. MAST **FM-1.3**
(step repetition): re-detecting is not resolving.

---

## SHIPPED TODAY

| Component | What it does | Trigger |
|---|---|---|
| `core/oversight/mast.py` | MAST taxonomy adopted wholesale (arXiv:2503.13657, 14 modes/3 cats, κ=0.88). Closed enum; rule-based classifier; models may propose, never finalize | library |
| `core/oversight/spans.py` | SQLite span ledger — parent/child, heartbeat/lease, tokens/cost, spec + artifact refs, live todo. Self-verification never counts | library |
| `core/oversight/reaper.py` | LOST / ABANDONED / SILENT_SUCCESS by **ground truth on disk**. Reads `mission_board.json` directly so intake can't go dry | `thunderbird-oversight-reaper.timer` — 15 min |
| `core/oversight/canary.py` | Injects known-bad tasks, asserts the layer detects them. Absence of detection = P0 | `thunderbird-oversight-canary.timer` — 4 h |
| `core/ops/wing_ops_report.py` | **Fixed a live lie.** No green on an empty denominator; states denominator on every clean claim; surfaces DEGRADED/UNVERIFIED; splits agent-stalls from Commander queue | both daily briefs |

**Both timers enabled and verified firing.** Reaper next :46 past each hour;
canary every 4h, exits non-zero when blind so systemd records a real failure.

### The live lie, specifically
`wing_ops_report.py:73` rendered a green *"no discrepancies, blocks, or drops
this window ✅"* whenever no failures were recorded — **including when nothing
had been recorded at all.** With a 4-row ledger it was green by construction,
mailed to the Commander twice daily. Absence of evidence reported as evidence
of absence. Regression tripwires now in `tests/test_wing_ops_report_honesty.py`.

### The canary is proven, not asserted
Mutation-tested: breaking the reaper, the self-verification guard, and MAST
validation each produce a specific canary failure; the control run stays green.
A canary that has only ever passed proves nothing.

---

## WHAT THE FIRST RUN FOUND

- **120 stale missions** of 198 — median 8.6 days, oldest 15.5 days
- Split honestly: **51 agent-side stalls** · **69 awaiting Commander**
  (collapsing these would let the Wing's dropped work hide in the Commander's queue)
- **12 duplicate missions for one payment** — the backlog is ~40 real items
  wearing 120 costumes
- Only 13 of the 69 Commander-queued items are auto-ingested noise; **56 are real**
  (client inquiries, FPD audits, Scandinavia air sourcing due Jul 22, undelivered)

### WING-1 observed three times in one session
`infra-audit`, `opus5-adversarial`, `opus5-blindspots` each wrote their
deliverable and exited without reporting. Under the old ledger, indistinguishable
from total loss — the Wing would have re-run finished work and paid twice.

### And once by me
I reported "committed and green" when tests were green but nothing was
committed. **WING-3, fabricated completion, CC seat.** Recorded, not buried.
The lesson is not that I erred; it is that nothing in the system caught it —
only my own re-read did. That is precisely the `TaskCompleted`/`Stop` hook gap
below.

---

## OPUS 5 VERDICT: "rethink the shape, keep the diagnosis"

Accepted and acted on:
- ✅ Fixed the live lie **first**, before new architecture
- ✅ Built the canary (blindspots review's ONE THING)
- ✅ Reaper reads the board directly, not a helper nobody calls

Rejected, with reason:
- ❌ *"Cut SQLite/spans."* Kept — it's built, tested (30 tests), and the
  `parent_span_id` + heartbeat fields are exactly what made LOST/SILENT_SUCCESS
  separable. Reviewer's premise was 4 rows of data; the reaper found 120 stale
  missions on first run.
- ❌ *"Cut the 14-code enum to 3 categories."* Kept 14. The mechanical
  classifier assigns from observed facts, so the ~58% judge-agreement concern
  (which applies to *model*-assigned categories) doesn't bind.

Accepted, deferred:
- `pass^k` — **not measurable here.** You cannot re-run "email the client" four
  times. Replaced on the roadmap by first-pass yield + independent-verification
  rate + silent-exit rate.
- Langfuse/Phoenix — field names adopted, daemon deferred.
- TUI dashboard — deferred; terminal + Sheet.

---

## ROADMAP — in consequence order

### 1. Backlog dedupe + consequence ranking `[next]`
Dedupe by subject; rank by **dollars at risk × days remaining**; force
close-or-write-off. TCD becomes the display layer for the ranked list, not the
strategy. *This is what actually attacks the backlog — a dashboard renders 120
items at equal weight, which is how a $24,798 deadline sat next to a GitHub link.*

### 2. Enforcement hooks — the anti-orphan layer
Verified available and currently unused:
| Event | Exit 2 effect | Prevents |
|---|---|---|
| `TeammateIdle` | teammate keeps working | WING-1 silent exit |
| `TaskCompleted` | task can't be marked done | false completion (my own WING-3) |
| `SubagentStop` | subagent can't stop | premature termination |
| `SubagentStart` | injects `additionalContext` | auto-inject spec + criteria |

Fail-open (exit 1) while proving out; exit 2 only after a soak period —
a blocking hook that misfires can brick a session mid-client-work.

### 3. Secret + PII scrub before any transcript capture
**Blocking dependency.** Full transcript capture was proposed the week after a
hardcoded-secrets incident, for a business holding passports and payment data.
Scrub lands *in the same change* as capture, never as a follow-up.

### 4. Retention
`policy_audit.jsonl` is 20.5MB/81k lines and growing; logrotate glob excludes
`*.jsonl`. Unbounded growth is a slow outage.

### 5. Commander-unreachable safe throttle
Three Gates are Commander-only with no backup approver. FPD deadlines don't
pause for sleep or travel. Past a silence threshold: throttle to safe, don't
grow the backlog silently.

### 6. Trust calibration
Per-seat, per-task-type, decaying trust (Beta over `seat_scorecard.jsonl`).
Reduces verification cost on proven work; never removes ground-truth checks
inside the Three Gates. **Model-version fingerprint resets trust** — a version
bump is a new employee wearing the old badge.

### 7. Commander override → gold labels
No durable way for you to say "this verdict was wrong" and have it teach the
system. Every disagreement is currently a one-off.

### 8. Dollar-tied metrics
Client-facing error rate as its own zero-tolerance class; missed-FPD cost as a
distinct lane; **cost per completed task**, not cost per token.

### 9. Brutal weekly appraisal
Graded by a different model family. Must report its denominator, name the
worst failure and what it cost, include "what we did NOT verify", and track
**orphan count — oversight capabilities shipped with zero callers.** If v2
ever scores > 0 there, v2 is failing.

---

## KNOWN DEBT
- `tests/test_opus_dispatch_phase_a.py` and `tests/test_skill_builder.py` fail
  at collection (`SkillIntent` import) — **pre-existing**, unrelated, unfixed.
- `test_abandoned_when_partial_output...` drives a RUNNING span through
  `close_span()` to set `detail`; works, but abuses the API. Needs a
  progress-update path.
- Span ledger has no writers in production yet — it is fed by the canary and
  tests only. **Until roadmap item 2 lands, spans.py is itself an orphan
  (WING-2) and I am counting it as one.**
