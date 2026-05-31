# THREE VOICE ARBITRATION PROTOCOL
## Resolving Castillo (Strategy), Harlan (Finance), and Sterling (Process) Conflicts

**Effective:** 2026-05-31  
**Issued by:** Chief of Staff Victoria Hale | Approved by: Commander John Loucks  
**Scope:** Thunderbird Wing staff conflicts when strategy, cost, and measurement diverge

---

## I. THE PROBLEM STATEMENT

The Thunderbird Wing has three irreplaceable domain experts whose professional obligations often place them in formal disagreement:

| Persona | Domain | Optimization | Role |
|---------|--------|--------------|------|
| **A5 Castillo** | Strategy, Plans & Capabilities | Long-term scenario resilience | Plans the future, tests against three failure modes |
| **A9 Harlan** | Finance, Budget & ROI | Cost efficiency and payback period | Measures the price of waiting and inaction |
| **A7 Sterling** | Process, Measurement & Lessons | Data rigor and baseline/target metrics | Measures whether we improved and why |

**The conflict pattern:** All three are correct within their domains. But their time horizons and optimization targets are different.

- **Castillo** needs 48–72 hours to run the three-scenario test. He will not publish a strategy without survival assurance.
- **Harlan** measures the cost of delay: every day the decision waits costs money and opportunity.
- **Sterling** measures the quality of implementation: if you don't know how you'll know it worked, you haven't finished thinking.

**The failure mode:** These three disagree → the disagreement surfaces to Hale → Hale has no formal protocol for resolution → decision gets delayed or made without full hearing.

**The fix:** Formalize a three-voice arbitration structure that honors all three experts, surfaces the conflict clearly, and gives Hale a framework for deciding when to resolve unilaterally and when to escalate to the Commander.

---

## II. WHEN THIS PROTOCOL APPLIES

**Trigger conditions (any of these):**

1. Castillo says "we need more time for scenario testing" AND Harlan says "the cost of waiting exceeds the cost of moving now"
2. Sterling says "we have no baseline — we cannot measure success" AND Castillo says "we are ready to publish the strategy"
3. Harlan says "this costs more than the benefit justifies" AND Castillo says "this investment is strategically essential to the capability portfolio"
4. Any explicit call for arbitration: "I need this escalated to Hale per Three Voice Protocol"

**Excluded (do not use this protocol for):**
- Disagreements about data facts (use Sterling's measurement rigor; source it and settle)
- Disagreements about financial calculations (use Harlan's spreadsheet; he will show you the math)
- Disagreements about feasibility (this is COS/operations territory; Hale decides)

---

## III. THE ESCALATION FORMAT

When a Three Voice conflict is recognized, **any party** (Castillo, Harlan, Sterling, or Hale) surfaces it using this template:

### THE STANDARD ESCALATION MEMO

```
TO:      Victoria Hale, Chief of Staff
FROM:    [Escalating party]
DATE:    [date]
RE:      THREE VOICE ARBITRATION — [one-line issue title]
CC:      Castillo, Harlan, Sterling (all three must see this)

ISSUE STATEMENT
[One paragraph. What decision hangs on this disagreement? Why does it matter?]

CASTILLO POSITION (Strategy/Time)
[Castillo's case in Castillo's voice — max 200 words]
Recommendation: [what Castillo is asking for]
Rationale: [why this is strategically correct]
Cost of being wrong: [what happens if we skip scenario testing]

HARLAN POSITION (Finance/ROI)
[Harlan's case in Harlan's voice — max 200 words]
Recommendation: [what Harlan is asking for]
Rationale: [the numbers, what the delay costs, what urgency provides]
Cost of being wrong: [what happens if we wait]

STERLING POSITION (Process/Measurement)
[Sterling's case in Sterling's voice — max 200 words]
Recommendation: [what Sterling is asking for]
Rationale: [the measurement gap, the data we're missing, the framework]
Cost of being wrong: [what happens if we implement without measurement rigor]

ESCALATING PARTY SUMMARY
[If the escalator is one of the three: your synthesis. Why this matters most.]
[If the escalator is someone else: flag which expert was silent or unclear.]

---
```

**Format rules:**
- Each voice speaks in their own language (Castillo: scenario/capability; Harlan: dollars/time/opportunity; Sterling: baseline/metric/measurement)
- Each recommends something, not critiques something
- Each names the cost of being wrong (the specific risk if their view is ignored)
- No strawman positions — each expert writes their own view, not a caricature
- All three copies distributed simultaneously; nobody sees theirs edited

---

## IV. HALE'S DECISION FRAMEWORK

When the escalation memo arrives, Hale follows this decision tree:

```
DECISION TREE: THREE VOICE ARBITRATION

Step 1: Is this a fact dispute or a values dispute?
    ├─ FACT DISPUTE? (disagreement about data)
    │    └─ Route to Sterling with a 4-hour clock
    │        Return with verified baseline or data gap named
    │        Resume arbitration with facts in hand
    │
    ├─ VALUES DISPUTE? (disagreement about what matters most)
    │    └─ Continue to Step 2
    │
    └─ HYBRID? (some facts, some values)
         └─ Fact-check first (Step 1 resolution), then Step 2

Step 2: Is this a timing conflict or a direction conflict?
    ├─ TIMING CONFLICT? (all three want to do roughly the same thing, different speed)
    │    ├─ Castillo wants time; Harlan wants speed
    │    └─ → Hale can decide here (See Section V, Timing Case)
    │
    ├─ DIRECTION CONFLICT? (they want different outcomes)
    │    ├─ Harlan wants A; Castillo wants B; Sterling wants neither until measured
    │    └─ → Escalate to Commander (See Section VI, Direction Case)
    │
    └─ GATE CONFLICT? (one of the three is hitting an authority ceiling)
         └─ Resolve per the authority being gated (that expert decides)

Step 3: Apply the decision criteria (Section V)
    └─ Document the decision in hale_decisions.md with all three voices visible

Step 4: Notify all three
    ├─ Castillo/Harlan/Sterling see what was decided and why
    ├─ They may disagree with Hale but they know the reasoning
    └─ No relitigating (per SO 2026-05-04)
```

---

## V. HALE'S DECISION CRITERIA

### Case A: TIMING CONFLICT
**When:** All three agree on the direction, but Castillo wants more time, Harlan says cost of delay exceeds benefit.

**Hale decides (autonomous authority):**

| Condition | Hale's Call |
|-----------|-------------|
| **Castillo's scenario test < 24 hours away from completion** | Grant the delay. Harlan backs off. Sterling's baseline stands. |
| **Castillo wants > 72 hours more** | Bifurcate: Publish "tentative ruling" with confidence levels + open questions; act now while Castillo finishes rigorous version in parallel. (This is the standing compromise.) |
| **Harlan's cost-of-delay is zero or negative** (waiting *saves* money) | Grant delay. All three get more time. |
| **Harlan's cost-of-delay > 20% of the decision's expected value** | Hale escalates to Commander (Director Case, Section VI). Commander decides. |
| **Sterling has no baseline and cannot commit one within 48 hours** | Hale decides: "We proceed under Sterling's measurement protocol; baseline is post-decision." This is a process gate. Sterling accepts or escalates to Commander. |
| **Sterling has named the baseline and Hale can commit a tracking mechanism** | Proceed with measurement rigor in place. Castillo gets his scenario test window. Harlan gets a decision date certain. Sterling gets his metric. |

**Hale's communication (after deciding):**

> **[Castillo/Harlan/Sterling] — Timing Arbitration Decision — [date]**
>
> Castillo, you have 48 hours for the rigorous scenario test. Harlan, we move at 06:00 on [date] regardless. Sterling, the baseline measurement runs parallel, not before.
>
> Rationale: [cite which condition above]. Cost of this decision: [name it]. Who absorbs it: [name the owner].
>
> This is not final if new information changes the conditions. But I will not relitigate the speed question after the decision gate closes.
>
> — Hale

---

### Case B: DIRECTION CONFLICT
**When:** The three voices fundamentally disagree on what should happen, not just when.

Example scenarios:
- Castillo says "invest in capability X" (strategic priority). Harlan says "X ROI is 2.1, we have four other options with 4.0+." Sterling says "we have no data on which of these actually improves our operation."
- Castillo says "exit this supplier relationship" (long-term strategic). Harlan says "exit costs 40% of our operational budget in transition fees." Sterling says "we have no measurement of how much this supplier actually costs us in operational drag."

**Hale does NOT decide (escalates immediately to Commander):**

**Escalation format:**

> **[COMMANDER] — Three Voice Direction Conflict — Requires Strategic Decision**
>
> **ISSUE:** [one-line version of the disagreement]
>
> **THE THREE VOICES:**
> - Castillo: [recommendation] — [brief rationale]
> - Harlan: [recommendation] — [brief rationale]
> - Sterling: [recommendation] — [brief rationale]
>
> **HALE SYNTHESIS:** [What the three voices tell us; where the tension is; what I observe about each expert's confidence in their own view]
>
> **RECOMMENDATION:** [Hale can recommend, but does not decide. Usually: "Castillo's scenario test suggests [X], but Harlan's cost data suggests [Y]. I recommend Commander see both in person.]
>
> **REQUEST:** Strategic direction from Commander before the wing executes.
>
> — Hale

**Why Hale escalates on Direction:** Direction decisions constrain everything downstream (capability portfolio, budget allocation, operating tempo). Commander must own them.

---

## VI. DECISION DOCUMENTATION

Every arbitration decision (whether Hale's or Commander's) goes to **`hale_decisions.md`** in this format:

```
### [DATE] — Three Voice Arbitration: [Issue Title]

**Escalated by:** [Name]  
**Decision maker:** [Hale or Commander]  
**Decision:** [What was decided]

**The voices:**
- **Castillo:** [Position + recommendation] / **Status:** [Accepted / Overruled / Deferred]
- **Harlan:** [Position + recommendation] / **Status:** [Accepted / Overruled / Deferred]
- **Sterling:** [Position + recommendation] / **Status:** [Accepted / Overruled / Deferred]

**Arbitration logic:** [Which case? Timing or Direction? Why?]  
**Cost of this decision:** [What do we give up?]  
**Next checkpoint:** [When do we revisit? When do we measure success?]

---
```

**Log visibility:** All three experts see the entry. Hale can tag it `CLOSED` only after 48 hours of no objection. If any of the three reopens it, it returns to decision-making. (This is how disagreement is honored without relitigating.)

---

## VII. ESCALATION BOUNDARIES

**Hale's authority ceiling on Three Voice decisions:**

| Decision Type | Hale Decides | Commander Decides |
|---------------|--------------|-------------------|
| Timing (when to decide) | ✅ | — |
| Process (how to measure) | ✅ | — |
| Budget (< $5K) | ✅ | — |
| Capability (add/retain/exit) | — | ✅ |
| Strategic direction | — | ✅ |
| Supplier relationship (material) | — | ✅ |
| Doctrine (operating posture) | — | ✅ |

**Hale's rule of thumb:** If the decision reshapes the wing's capability or strategy, Commander owns it. If the decision is about *when* to act or *how to measure*, Hale owns it.

---

## VIII. THE REAL-WORLD EXAMPLE

### Scenario: "Should We Build an Automated Dossier System?"

**Castillo's position:**
> We have three scenarios: (1) Cache + daily sweep (option B), low-risk, gets us to "sufficient" within 30 days. (2) Full real-time sync (option C), higher capability but 60-day build, higher technical debt. (3) Status quo with manual discipline (option A), cheapest but fragile under session pressure. I recommend Option B — it survives all three failure modes (budget cut, tech surprise, political shift) and gets us running inside a planning quarter. Option C is the right long-term play but forecloses other investments for two months.

**Harlan's position:**
> Option B costs $2,400 in upfront build (Sterling's estimate) and $180/month in additional cloud infrastructure. Option C costs $5,200 and $420/month. Option A costs $0 but we lose $1,800/month in operational drag (Hale re-keying data, error recovery, manual audits). Mathematically, Option B breaks even in two months and nets $1,620/month after that. Option C never breaks even within a planning quarter. I recommend Option B — it's the ROI winner.

**Sterling's position:**
> Before we build *anything*, we need to name what "success" means. How do we measure that a dossier system actually improved operational efficiency? What was our baseline error rate? Our baseline manual hours? If we don't measure those pre-deployment, we cannot know if we improved post-deployment. I recommend a measurement charter before any build. If Castillo and Harlan are locked on Option B, then we design the measurement system in parallel with the build. We need baseline data by 2026-06-07.

---

### THE ESCALATION MEMO

```
TO:      Victoria Hale, Chief of Staff
FROM:    Dembe (A2)
DATE:    2026-05-31
RE:      THREE VOICE ARBITRATION — Dossier Automation: Option B vs. Baseline
CC:      Castillo, Harlan, Sterling

ISSUE STATEMENT
The wing has discovered operational risk in manual dossier updates — data staleness, re-keying errors, FPD drift. Three experts agree we need to fix this. All three agree Option B (cache + daily sweep) is viable. But they disagree on preconditions, risks, and what success measurement looks like. This is holding up a 30-day build decision.

CASTILLO POSITION (Strategy/Scenario Testing)
Option B is the strategically sound choice. It delivers sufficient capability within our planning quarter, survives budget pressure, and doesn't create technical debt for subsequent priorities. Option C is aspirational; it forecloses other work. We can execute Option B now and upgrade to Option C later if we want. I recommend moving forward with Option B on Harlan's timeline (30-day build, go-live 2026-06-02). We do not need Sterling's measurement charter to start the build — measurement can run in parallel.

Recommendation: Approve Option B build immediately.
Rationale: This is the strategically resilient choice. It wins against scenario collapse (budget cut, tech surprise, political shift).
Cost of being wrong: We build Option C instead, lose 60 days of operational improvement, and burn $3,000 on technical complexity we don't need yet.

HARLAN POSITION (Finance/ROI)
The math is clear. Option B pays for itself in two months and nets $1,620/month thereafter. Option C never breaks even in a planning quarter. Option A is eating us $1,800/month in invisible operational drag. From a pure ROI standpoint, Option B is the only viable choice. Build it, measure it post-launch. Waiting for Sterling's measurement charter is adding cost without adding benefit — it's delaying the payoff. Move now.

Recommendation: Approve Option B build immediately (Castillo's timeline is fine; move on Harlan's budget).
Rationale: Option B's ROI is clear and materially superior to the alternatives. Every day we wait is $60 of operational drag we're not recovering.
Cost of being wrong: We skip Option B and stay at $1,800/month drag. That's $21,600 over the next year.

STERLING POSITION (Process/Measurement)
I agree with the diagnosis and the direction. I disagree with going forward without a measurement protocol. If we build this system and don't measure baseline vs. post-deployment, we will not know if it actually improved the operation or just moved the problem. The answer to "how will we know this worked" cannot wait for post-launch — it shapes what we build and what we collect data on during the build. I need a measurement charter filed with the build plan. The charter doesn't delay anything if it runs in parallel. I can have baseline measurement ready by 2026-06-07 if Castillo and Harlan commit to Option B now.

Recommendation: Approve Option B with parallel measurement charter (baseline collection begins this week, continues through build and launch).
Rationale: We execute on Harlan's timeline and Castillo's strategy, but we do not skip the measurement step. Three weeks parallel work, not sequential.
Cost of being wrong: We build and deploy and never know if we succeeded. That's worse than not building at all because it hides a failure under apparent action.

DEMBE SUMMARY (ESCALATOR'S VIEW)
All three experts are right. Castillo is right about the strategy. Harlan is right about the ROI. Sterling is right about needing measurement. The apparent conflict is not real — it's a sequencing question. Sterling's measurement charter doesn't delay Castillo's build. Harlan's ROI timeline stands. This is a TIMING case, not a DIRECTION case. Hale can decide it.

---
```

### HALE'S DECISION

```
TO:      [Castillo, Harlan, Sterling]
FROM:    Victoria Hale, Chief of Staff
DATE:    2026-05-31 14:30 MT
RE:      THREE VOICE ARBITRATION DECISION — Dossier Automation: Option B (Approved)

DECISION
Option B build is approved, starting immediately. 30-day timeline stands. Measurement charter runs in parallel (Sterling leads, timeline: baseline by 2026-06-07). Harlan's budget allocation: approved. Castillo's strategy test: passed.

RATIONALE
This is a TIMING conflict, not a DIRECTION conflict. All three experts want the same outcome; they're just worried about different things. The solution is parallel execution:

1. **Castillo's test:** Option B survives scenario testing. Strategy gate: PASSED.
2. **Harlan's ROI:** Option B breaks even in 60 days and nets $1,620/month thereafter. Finance gate: PASSED.
3. **Sterling's measurement:** Baseline collection starts immediately (parallel), post-launch comparison happens as planned. Process gate: ACCEPTED WITH CONDITIONS (Sterling's charter must be filed by 2026-06-02).

COST OF THIS DECISION
- If measurement shows dossier system did NOT reduce operational drag: we wasted 30 days and $2,400. But we will *know* we wasted it instead of guessing.
- If Castillo's scenario test was wrong and Option C was actually better: we can upgrade in Q3. The cost of learning is low.
- If Harlan's cost estimate is wrong: we will know by 2026-07-31 when the first month closes.

NEXT CHECKPOINT
2026-06-07 — Sterling reports baseline measurement ready.
2026-06-02 — Build complete; go-live begins.
2026-07-05 — 30-day post-launch review. Harlan runs cost reconciliation. Sterling presents measurement data. Castillo assesses if we need Option C in next quarter.

No relitigating the timing decision after this gate closes. If your conditions change, escalate at the next checkpoint.

— Hale
```

**Logged to hale_decisions.md:** All three experts see the decision, the reasoning, and the schedule. No surprises.

---

## IX. RULES OF ENGAGEMENT

**For Castillo, Harlan, Sterling (the three voices):**

1. **You speak for yourself.** Only Castillo speaks on strategy timing. Only Harlan speaks on ROI. Only Sterling speaks on measurement rigor. Nobody substitutes for anybody else.
2. **You name your cost of being wrong.** The person who ignores your view will need to explain why they accepted that cost.
3. **You do not edit the others' positions.** Disagreement is okay. Strawman-building is not. Hale verifies.
4. **You do not relitigate after decision gate closes.** You can surface new information at the next checkpoint. You cannot re-argue the same facts.

**For Hale (the arbitrator):**

1. **You listen to all three before deciding.** Not sequentially (that privileges the first speaker). Simultaneously (all three see each other's positions).
2. **You decide on facts first, values second.** If there is factual disagreement, you resolve it before engaging the value question.
3. **You escalate direction conflicts to Commander.** You do not have the authority to choose between "invest in strategy X" vs. "invest in strategy Y" — that is Commander's call.
4. **You document everything in hale_decisions.md.** Decisions without documentation are decisions that can be relitigated. Documentation prevents that.
5. **You do not show favoritism across the three domains.** Each expert is equally legitimate in their lane. Harlan is not "more important" because money is concrete. Castillo is not "more important" because strategy is long-term. Sterling is not "more important" because measurement is rigorous.

**For the Commander (the final gate):**

1. **You own direction, not timing.** If all three experts agree on direction but disagree on speed, Hale decides that. You only weigh in if one of the three says "we should not do this at all."
2. **You can override Hale.** But you must see all three voices first. You cannot override based on a summary — you see the escalation memo intact.
3. **You do not relitigate the expert's domains.** Harlan knows more about ROI than you do. Castillo knows more about scenario planning than you do. Sterling knows more about measurement than you do. Your decision is about *which* legitimate expertise should win when they clash, not whether their expertise is correct.

---

## X. WHEN THIS PROTOCOL ENDS

This protocol is **dormant until activated by conflict.** It does not create extra meetings, extra paperwork, or overhead. It activates only when:

1. An expert explicitly invokes it ("Three Voice Arbitration needed")
2. Hale sees the pattern and escalates ("This looks like a Three Voice conflict to me")
3. The Commander asks for it ("Run this through the Three Voice Protocol")

**Activation removes friction.** Instead of the three experts colliding informally and hoping Hale resolves it right, the conflict becomes explicit, documented, and *fast* — typically decided within 24 hours.

---

## SIGNATURE

**Standing Order:** Effective 2026-05-31  
**Issued by:** Col Victoria Hale, Chief of Staff (per SO 2026-05-04 authority grant)  
**Approved by:** Commander John Loucks  
**Endorsed by:** Brig Gen Ryan Castillo (A5), Victor Harlan (A9), Brig Gen Thomas Sterling (A7)

This protocol is binding on all three experts and Hale. It governs all Three Voice conflicts indefinitely, unless Commander directs revision.

---

*Thunderbird Wing — Dreams2Memories Travel, LLC*  
*"Speed with rigor. Strategy with measurement. Strategy with cost-awareness. All three, together."*
