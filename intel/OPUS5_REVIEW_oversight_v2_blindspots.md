# Wing Oversight v2 — Blind Spot Review
**Author:** Opus 5 (external review, not the model that drafted v2) · 2026-07-29

Scope note: I am not summarizing the design draft, the infra audit, or the two SOTA
scans. Everything below is what none of the four documents asked for. Where a
finding maps onto an existing file, I name it; where it doesn't exist yet, I say so.

---

## A. The human-organization analogy, taken seriously

The Commander's own framing — "work of 9 people... functions like humans do" —
is the design brief. Real 9-person orgs run oversight machinery this design has
none of. MAST's own headline finding (Cemri et al., arXiv:2503.13657) is that
multi-agent failures are **organizational-design failures**, not capability
failures — which means the fixes below are not nice-to-haves, they're the same
category of fix MAST is telling you to make. The v2 draft is almost entirely
*detection* machinery (spans, heartbeats, judges). It has no *design-time*
machinery — nothing that prevents FM-1.2 (role confusion) or FM-1.5 (unclear
termination) by construction, only things that notice after the fact.

**Onboarding / probation.** A new hire doesn't get full trust on day one. A
model version bump (Sonnet 4.6→5, Gemini 3.1→3.5, a provider swapping a
checkpoint under the same public name — flagged explicitly in the SOTA docs as
a root cause of "harmless-looking" regressions) is functionally a new employee
wearing the old employee's badge. Nothing in v2's span schema or
`seat_scorecard.jsonl` keys trust by **seat + model version**, only by seat
name. There is no probation window — N tasks at elevated verification before a
version reverts to steady-state trust. This is buildable today: capture
`gen_ai.response.model` (already in the v2 span schema, §2) and diff it against
the last-seen string per seat; a change triggers a probation counter.

**Performance improvement plan.** When a seat's scorecard degrades, what
happens? Today: nothing formal — it shows up in a digest line and is easy to
read past. A PIP translates directly: a scorecard threshold breach should
mechanically *reduce* that seat's autonomy ceiling (route more of its output
through tier-2/3 grading, shrink its trust-scoped task set) for a defined
window, with an explicit re-earn condition, not just a lower number in a
weekly report.

**Firing / retiring a seat.** Was Gemini Flash (implicated 7/28) ever formally
retired from any task class, or just "noted"? There's no decommission runbook:
what happens to in-flight work assigned to a seat being retired, what happens
to its accumulated scorecard history (does it get archived and stay queryable
— "why did we stop trusting Flash on X" — or does it just vanish when the
config changes), and who verifies nothing still silently routes to it. Right
now a model swap is a `.py` edit, not an event with a before/after audit trail.

**Promotion.** Directly = trust calibration, §B below.

**Skip-level 1:1.** Everything the Commander sees about subagent work is
currently mediated by CC's own summary of it (this very review is an example —
the "main" orchestrator reads my output, not the Commander directly, unless
forwarded). A real skip-level would be: a scheduled, *unedited* raw transcript
sample surfaced to the Commander bypassing CC's synthesis entirely — not
because CC is assumed dishonest, but because a summarizer grading its own
summarization has no built-in check, and the 2026-07-18 incident was
exactly a self-report failure. Cheap to build: pick one subagent transcript at
random per week, push it to the Commander unmodified.

**Postmortem culture.** §11's "name the worst failure" is a postmortem
*headline*, not a postmortem *process*. Real postmortems produce action items
with an owner and a due date, and — critically — a **follow-up verification
that the action item actually landed**, checked against ground truth, not
against someone saying "done." Nothing in v2 tracks action-item closure. Absent
that, "brutal weekly appraisal" restates the same problem every week with no
visible closure loop, which is worse for morale (such as it is) and trust than
not appraising at all.

**Handoff / vacation problem.** The Three Gates are Commander-only, full stop.
Real orgs have a designated backup approver for exactly this reason — the CEO
being on a plane doesn't pause payroll. This system has **no defined behavior**
for a Three-Gates item (a client send, a financial commitment with a hard FPD)
that arrives while the Commander is unreachable past some SLA. Silently waiting
risks a real missed deadline with real cash consequences (a lapsed deposit); an
undefined "someone decides to act anyway" risks a Three-Gates violation. This
needs an explicit, narrow answer — not full delegated signing authority, but
at minimum a defined **safe-default** (see §C) for the unreachable-operator case.

**Institutional memory when a worker leaves.** Same as retiring a seat above —
there is no archive format for "what we learned about this model" that
survives a swap.

**What does NOT translate.** Severance/notice-period mechanics, career
motivation, interpersonal/political dynamics — none of this applies, and
trying to simulate it (beyond the persona voice work already in
`Personas/`) would be theater, not oversight. The one HR-shaped thing worth
keeping is exactly what's already in memory as `equal_performance_standard` —
same bar for CC/OC/AG — which is correct and should stay, but is orthogonal to
trust *calibration* (§B), which is about verification intensity, not standard.

---

## B. Trust calibration as a first-class object

v2 treats every seat as equally suspect forever — every dispatch pays the same
verification cost regardless of track record. This is safe but not how any
functioning org allocates review effort, and at a few tasks/day with a halved
budget, review effort is exactly the scarce resource.

**Concrete shape:**
```
trust[seat][task_type] = time-decayed Beta(alpha=successes, beta=failures)
```
computed from `seat_scorecard.jsonl` (already exists, 87 rows, already live).
High trust + low-stakes task_type → tier-1 (deterministic) grading only. Low
trust, new task_type, or a task_type the seat hasn't touched recently → full
3-tier stack plus a higher chance of Commander spot-check.

**Decay and re-trigger conditions (the part v2 doesn't have at all):**
- Time decay (e.g. 30-day half-life) so "reliable three months ago" doesn't
  silently become "assumed reliable now" without recent evidence.
- **Any** model-version change on that seat resets to probation (§A).
- Any FAILED/DISCREPANCY verdict in the trailing window forces a hard reset,
  not a gradual score decrement — one bad outcome should cost more trust than
  one good outcome earns, because the downside (a bad client send) is
  asymmetric with the upside (one saved review cycle).
- A long gap since last use of that task_type forces re-probation on next use.

**The real risk, stated plainly: a seat trusted on easy work gets applied to
hard work under the same nominal `task_type` label.** This is the single
biggest danger of an earned-autonomy system and the reason task_type buckets
must be joined with a **stakes/complexity tier**, not just a category string —
"research" on a destination fact and "research" feeding a client-facing price
commitment cannot share a trust bucket. Two structural guards:
1. Trust can reduce verification *frequency/cost*, but for anything inside the
   Three Gates it must never fully remove tier-1 ground-truth checks — trust
   buys back tier-3 human review, never tier-1.
2. The stakes tag should be assigned by the spec artifact at dispatch time
   (§3 of the design doc — a field that doesn't exist yet), not inferred after
   the fact, so a seat can't shape its own review burden by how it phrases the
   task.

Also worth naming: gaming/trust-laundering is easiest exactly where acceptance
criteria are self-authored. `is_checkable()` already exists as a guard — it
needs to be enforced by a party other than whoever is requesting the trust
benefit.

---

## C. The operator is the bottleneck — theory of attention

Requirement #9 ("progress bars, timers, todo lists... visibility into
everything") is, taken literally, a recipe for drowning a single human in
dashboards. None of the four documents state an explicit *attention budget* —
what the system is allowed to spend of the Commander's limited attention, and
under what conditions it earns the right to spend more of it.

**A three-tier answer, concretely:**
- **Never reaches him:** passing tier-1/tier-2 verifications, in-flight status
  of anything inside current trust bounds, routine tool calls (already the
  right call per `feedback_telegram_channel_discipline`).
- **Within the hour (page):** an actual Three-Gates decision point, any
  DISCREPANCY/UNVERIFIED/DROPPED attached to real money or a client-facing
  artifact, a LOST task on a hard external deadline (FPD, embarkation) inside
  some threshold window.
- **Digest only:** scorecard trend, cost-per-task, six-orphans count, anything
  already auto-remediated.

**The right to escalate must itself be earned, not assumed.** Track
page-precision — of the last N pages on a given alert class, what fraction
were true positives — and auto-demote a chronically-noisy alert class to
digest-only, re-promoting only after a real miss. Without this, v2's own new
alert surfaces (LOST/ABANDONED/SILENT_SUCCESS — three *new* page-worthy
categories that didn't exist before this design) are the most likely source of
the next alert-fatigue episode, in a system whose own memory
(`feedback_overnight_message_volume`) already flags volume as a solved-once
problem that regresses easily.

**3am:** page only for genuinely irreversible-and-time-critical (money already
moving, a deadline expiring within the hour, a client-facing error already
sent). Everything else queues, even if it "feels" urgent to the system that
generated it.

**Degradation if ignored for a week.** This is the sharpest gap: nothing in
any of the four documents defines what the system does if the Commander simply
doesn't look for a week. The unsafe default is "backlog grows silently,
nothing changes behavior." The correct default is a **safe throttle, not a
silent loosening**: past a defined no-contact threshold, the system should
auto-restrict — refuse to accumulate new financial commitments, refuse new
client sends without a defined secondary reviewer, and flag the no-contact
state itself in the very next channel that does reach him (a text, not just
another email digest that's part of the backlog he's already ignoring). This
also directly answers the vacation/handoff problem in §A: the safe default
*is* the backup approver, and it is "hold," not "proceed."

---

## D. Failure modes of the oversight system itself

Section 11 of the design already asks "who watches the watchmen" for *new*
capabilities (the six-orphans metric). It has no answer for **decay of
existing, already-wired** capabilities — a hook that silently stops firing, a
systemd timer that's quietly disabled, a reaper that's running but querying a
table that changed shape. The audit itself is proof this class of failure is
real and currently invisible: `directive_ledger.capture()` was flagged as a
4th zero-caller function *not previously counted* by the session's own earlier
audit ticket (`OPUS-REVIEW-20260729`, which found only 3). If the auditors
missed a 4th orphan on the same day they were explicitly hunting for orphans,
a passive "does the digest look green" check will miss silent decay in
production, indefinitely.

**The concrete fix — a canary, not a bigger dashboard:** inject a synthetic
task on a schedule with a *known* correct outcome (e.g., a fake dispatch
tagged `synthetic=true` so it never pollutes real scorecards, deliberately
designed to fail verification). If the expected FAILED verdict + page doesn't
arrive within a defined window, that absence is itself the P0 alert — "the
oversight pipeline is dark," escalated harder than any single task failure
would be, because it means every other alert in the system is currently
unverified. This is the literal implementation of this repo's own documented
doctrine (`feedback_silent_sensor_efficacy_monitoring`: monitor efficacy, not
presence) applied to the oversight layer itself, which none of the four
documents do.

**Disagreement that sticks and teaches.** There is no schema field anywhere
(`delegation_outcomes.py`, `silver_ledger.jsonl`) for "the Commander reviewed
this verdict and overruled it." Without one: (a) a wrong verdict has no
durable correction — the record just says what the automated judge said,
forever; (b) the system has no accumulating gold-label set to recalibrate
judges against, which the SOTA docs name explicitly as the fix for
"calibration drift," one of the five named LLM-judge biases. Add a
`commander_override` verdict type that wins permanently in the record and
feeds the periodic judge-calibration pass (Cohen's kappa against accumulated
overrides) — this turns every disagreement into training signal for free,
instead of a one-off correction that the system forgets.

**False accusation vs. false clean bill.** Both need to be tracked as their
own rates on the oversight layer, and neither can be computed without the
override mechanism above providing ground truth to measure against. Right now
there is no way to answer "how often is the grading stack wrong," only "how
often did it flag something."

---

## E. What the business actually needs

This is a travel agency, not a research lab, and none of the four documents
connect telemetry to dollars.

- **Client-facing error rate** deserves its own zero-tolerance metric class,
  distinct from internal rework — an error that reaches a client's inbox is a
  different order of consequence than an error caught internally, and should
  never be folded into a generic "discrepancy rate."
- **Missed hard-deadline rate** (FPD, embarkation, booking windows) needs its
  own detection lane, separate from generic lost-tasking detection, because
  the cost model is different — a missed FPD can mean a lost deposit or a
  cancelled booking, not just "redo the work." Tag deadline-bearing tasks at
  dispatch time with the actual $ and date at risk.
- **Revenue per operator-hour.** The Commander's own stated goal — "the work
  of 9 people" — implies this is the actual north star the whole oversight
  system exists to serve, and nothing in any of the four documents measures
  it. Without it, the system can be internally "green" (good scorecards, no
  discrepancies) while never actually proving the core business claim it was
  built to support.
- **What a failure actually costs.** A blast-radius field (dollars at risk,
  reputational tier — internal / client-visible / public) should be attached
  to the spec artifact **at dispatch**, not inferred after a failure. This is
  also what should drive grading tier and paging threshold, not task_type
  alone — a "research" task with $8K of client commitment riding on it is not
  the same stakes class as a "research" task that's purely internal curiosity.
- **What an insurer/professional-liability standard would demand:** an
  immutable, tamper-evident audit trail for anything touching client payment
  data or PII — not just append-only JSONL (which is good but not
  tamper-evident on its own), but hash-chained so a silent edit or deletion is
  mechanically detectable, plus retention and a four-eyes requirement on
  anything moving client money.
- **A genuine never-automate class**, finer-grained than the existing Three
  Gates: entering a client's payment card or passport data into an external
  system, or the literal final submission of a charge, should require a human
  hand on the actual keystroke — "Commander approved the plan" is not the same
  guarantee as "Commander's own input executed the step," and for this one
  narrow class of action the gap between those two matters more than anywhere
  else in the system.

---

## F. Ten ideas not in the design, ranked value ÷ effort

1. **Oversight canary/heartbeat** (§D). Cron-injected synthetic failing task,
   confirms the whole dispatch→verify→record→page pipe round-trips on a
   schedule; absence of the expected page is itself the alert. *Low effort,
   highest value in this review* — it's the only mechanism that catches the
   next orphan before a human stumbles onto it by accident, which is how all
   4 known orphans were found so far.
2. **Model-version fingerprint + auto-probation.** Diff `gen_ai.response.model`
   against last-seen per seat; mismatch triggers an N-task elevated-scrutiny
   window before trust resumes steady-state. *Low effort* — the field is
   already planned in the v2 span schema, this just adds a comparison.
3. **Blast-radius/stakes tag on the pre-dispatch spec artifact** (§3), driving
   both grading tier and paging threshold. *Low effort* (one field + a lookup
   table), directly wires oversight cost to actual dollar risk (§E).
4. **Page-precision tracking / alert-fatigue governor.** Trailing true-positive
   rate per alert class; auto-demote chronically noisy classes to digest-only.
   *Low effort*, prevents v2's three new alert classes from becoming the next
   volume problem.
5. **Commander-override verdict type**, durable and permanently authoritative,
   feeding periodic judge kappa-recalibration. *Medium effort*, closes the
   biggest gap in §D and gives the LLM-judge bias-mitigation literature
   (already cited in the SOTA docs) an actual gold-label source for free.
6. **Cost-per-completed-task field on every delegation_outcomes row.** *Low
   effort* (SOTA docs already flagged this as the #1 missing metric) — turns
   the halved-budget self-execute-vs-delegate question into a number instead
   of a heuristic.
7. **Safe-default throttle on Commander no-contact** (§C). Past a defined
   silence threshold: block new financial commitments and client sends
   pending a secondary check, and surface the no-contact state itself through
   whatever channel still reaches him. *Medium effort* (a state machine +
   one new gate condition), closes the vacation/handoff gap in §A with real
   dollar exposure if left open.
8. **Monthly pass^k replay** — same 5 canonical mission types, 3x each, across
   CC/OC/AG, score variance. *Medium effort*, the only mechanism in this
   review that catches a seat quietly getting worse rather than catching a
   single bad task — nothing else in v2 re-runs anything, it only grades what
   already happened once.
9. **Postmortem action-item tracker with ground-truth close verification.**
   *Medium effort*, converts "brutal weekly appraisal" from a restated
   problem list into a visible closure loop (§A).
10. **Weekly unedited subagent-transcript sample to the Commander**,
    bypassing CC's own summarization. *Low effort*, cheapest possible
    skip-level mechanism (§A) and a standing calibration check on whether
    CC's reporting layer itself can be trusted over time.

---

## G. The one thing

Build the **oversight canary** (F.1) first, before any of the rest of v2.

The entire design rests on a stated premise — "oversight must be structurally
impossible to skip... enforcement lives in hooks and timers that fire
regardless of what a session remembers." That premise has already failed once,
silently, in this exact repo: six named oversight functions shipped, wired in
docstrings and CLAUDE.md, zero real callers, and the daily digest printed green
the entire time. Nothing caught it until a human-directed audit went looking —
and even that audit missed a fourth orphan the first time through. Building
more spans, more grading tiers, more scorecards on top of an unverified
assumption that the plumbing keeps working is exactly how you get a more
sophisticated version of the same failure — v2 becoming orphan #7, the exact
risk the design doc's own final open question names and doesn't answer. A
canary that proves the whole pipe end-to-end on a schedule, and escalates
harder than any single task failure when it goes dark, is the one piece of
infrastructure that makes every other promise in v2 actually verifiable rather
than merely plausible.
