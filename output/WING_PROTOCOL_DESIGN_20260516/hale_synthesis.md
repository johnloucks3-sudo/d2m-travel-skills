# HALE SYNTHESIS — Wing Engagement Protocol Design
## Gate 4 Commander Decision Brief
*2026-05-16 | Col Victoria "Iron Vic" Hale, COS*

---

## ISSUE

Commander directed redesign of Wing engagement to use a formal 7-step sequence modeled on joint force exercise planning doctrine. Five staff (A2, A5, A7, CH, A12) plus JEXS doctrine research. This brief synthesizes findings and presents 3 decisions for Commander approval.

---

## DISCUSSION

### What the Staff Found

**The SO-2026-05-04 conflict is real.** ELON and Sterling both named it independently. Universal per-prompt protocol reinserts a Commander decision gate (Step 4 of Commander's 7-step sequence) into tasks that SO-2026-05-04 explicitly grants Hale to run at 95% autonomy. Universal application doesn't add rigor — it breaks the autonomy architecture we built in May. This is the most important finding.

**Tiered protocol is the answer.** Castillo proposed 4 tiers. ELON proposed one weekly exercise window. They converge: the protocol must be selective, not ambient. The four-tier model preserves tempo on routine work while creating genuine exercise discipline on complex, high-stakes prompts.

**Dembe confirmed the doctrine.** JEXS/JELC has five phases: Design → Planning → Preparation → Execution → Evaluation/Analysis/Reports. Commander's 7-step sequence maps across all five phases accurately. One structural gap: no wargaming step between Staff Discussion and HALE Synthesis. Joint doctrine requires adversarial review before COA approval — the Wing doesn't have it.

**The anti-theater principle — all three said it.** Sterling named the metric (`lessons_implementation_rate_pct`). Dembe said "if no file changes, the lesson did not propagate." Washington said "close the loop visibly." The failure mode for this protocol is the same as every military AAR: documents that get filed and never cited. The design must structurally prevent this.

**Prompt Charter is the pre-commit gate.** Sterling proposed it. This is what Commander meant by "do better in structuring prompts." Five fields before any T2/T3 staff engages: success criteria, scope in/out, named staff with rationale, token/time budget, exit condition. Hale rejects incomplete charters. This catches bad prompts before they consume staff resources.

**Hotwash is two distinct tiers.** Dembe confirmed doctrinal distinction: immediate verbal hotwash (within 60 min of execution) vs formal AAR (within 24-72 hours). Washington added sequencing: senior speaks last, owns error first. The Wing should explicitly adopt both.

---

## KEY CONVERGENCES (Staff Agreement — No Decision Needed)

These points had cross-staff consensus. Hale will implement them as operational detail:

1. **Time-based exemption over category-based.** Washington's correction: "24-hour consequence" threshold (any prompt where inaction costs something in a day) catches more cases than "client-focused" category. Hale adopts this framing in implementation. Client queries still fall within it.

2. **HALE red-team scan as standing protocol.** Dembe Rec 4: 90-second adversarial review before HALE synthesis on T2/T3 prompts. Fills the doctrinal gap. Hale owns this without a gate.

3. **Classification authority to Castillo.** Castillo's ask: explicit authority to classify prompt tier before any staff engages. Hale grants this as COO — A5 is Operating Tempo Owner, this is his function. No Commander gate needed.

4. **Lessons propagation rate is the A7 metric.** Sterling owns `lessons_implementation_rate_pct`. Red threshold: below 50% at 60 days triggers halt and redesign. Hale tracks, Sterling reports weekly.

5. **DOTMLPF-P routing for hotwash findings.** Sterling's recommendation: classify each finding (Doctrine, Organization, Training, Materiel, Leadership, Personnel, Facilities, Policy) to route it to the right owner rather than leaving it as general observation.

---

## THE THREE DECISIONS

### Decision 1 — Protocol Tier Architecture

**Context:** SO-2026-05-04 prohibits reinserted Commander gates below the four gates. Universal protocol breaks this. Two viable options:

| | Option A | Option B | Option C (Hale rec) |
|---|---|---|---|
| **Model** | Castillo 4-tier | ELON weekly exercise window | Hybrid: 4-tier + T3 capped at 1/week |
| **Trigger** | Classification by A5 | ELON picks weekly from kill audit | A5 classifies; T3 fires at most once/week |
| **T0 (routine)** | No protocol | No protocol | No protocol |
| **T1 (tactical)** | 3 steps, 1 staff, async hotwash | No protocol | 3 steps, 1 staff, async hotwash |
| **T2 (operational)** | 5 steps, 2-3 staff, Hale aggregates | No protocol | 5 steps, 2-3 staff, Hale aggregates |
| **T3 (strategic/full)** | Full 7-step | Full 7-step on one weekly prompt | Full 7-step, ≤1/week |
| **SO-2026-05-04 compliance** | ✅ (tiers below T3 are autonomous) | ✅ | ✅ |
| **Kill threshold** | >1 T3/week = classification broken | — | Same |

**Hale recommends Option C.** Combines Castillo's rigor with ELON's tempo discipline. The weekly cap on T3 is a forcing function: if the Wing hits cap, it means something is being over-classified. It also gives ELON a structural role (he picks the weekly exercise candidate from the kill audit, which is already his function).

**→ Commander decision: A / B / C**

---

### Decision 2 — Prompt Charter as Pre-Commit Gate

**Context:** Sterling's finding: the Commander's desire to "do better in structuring prompts" requires a structural gate before staff engages. Otherwise the protocol improves execution discipline but not prompt quality.

**Sterling's Prompt Charter (5 fields, required for T2/T3):**
1. Success criteria — what does "done" look like?
2. Scope in/out — what is explicitly excluded?
3. Named staff with rationale — which personas, why each?
4. Token/time budget — what's acceptable?
5. Exit condition — at what point do we stop and reassess?

**Hale rejects incomplete charters before any staff is spun up.** This is the pre-commit equivalent.

| | Option A | Option B |
|---|---|---|
| **Model** | Charter required for T2/T3 | No charter requirement |
| **Overhead** | ~2 min additional for Commander or Hale to fill | Zero |
| **Benefit** | Stops badly-structured prompts before they cost tokens | — |
| **Downside** | Another step before execution on T2/T3 | Prompt quality problem persists |

**Hale recommends Option A.** For T3, Commander fills the charter (it's a Gate 4 event). For T2, Hale fills it from context (autonomous). T0/T1 no charter. The overhead is front-loaded and saves downstream cost.

**→ Commander decision: A / B**

---

### Decision 3 — Monthly Wing Deliberate Review

**Context:** Dembe Rec 5: a monthly Wing Deliberate Review — structured review of accumulated lessons, routing updates to doctrine, identifying patterns across exercises. Joint doctrine requires this; without it, the AAR loop never closes at the institutional level.

This is a Gate 4 item because it requires Commander time investment and ownership of the cadence.

| | Option A | Option B |
|---|---|---|
| **Model** | Monthly 30-min structured review | Skip; rely on weekly Sterling metrics report |
| **Format** | Hale facilitates, Sterling presents `lessons_implementation_rate_pct` data, Commander decides on any doctrine changes | No dedicated session |
| **Commander time** | ~30 min/month | None |
| **Institutional learning** | Closed loop — lessons become doctrine | Open loop — lessons are logged but may not propagate |
| **Risk** | Calendar hold required | Lessons accumulate without systemic integration |

**Hale recommends Option A.** The Sterling weekly metrics report covers operational health. The monthly review is different — it's where the Wing asks "are we a learning organization?" Dembe's most important finding: "if no file changes, the lesson did not propagate." The monthly review is the forcing function.

**→ Commander decision: A / B**

---

## HALE'S RECOMMENDATION (Full Position)

**Option C / Option A / Option A.**

Tiered protocol with weekly T3 cap. Prompt Charter required for T2/T3. Monthly Deliberate Review as a standing Commander cadence.

This is a fundamentally sound design. ELON's diagnosis of the SO conflict is correct, but the fix is classification — not abandoning the framework. The Commander's instinct to model on joint force doctrine is validated by Dembe's research. The gap the staff identified (no wargaming step) is fillable without a Commander gate. The anti-theater problem (AARs that don't propagate) is solvable with Sterling's metric and the monthly review.

Washington's framing is the right close: *"The design is fundamentally sound. Those three adjustments make it real rather than performed."*

---

## ACTIONS PENDING COMMANDER DECISION

| If Commander decides | Hale executes |
|---|---|
| Decision 1: Option C | Castillo writes classification schema; Hale publishes T0-T3 routing rules to CLAUDE.md |
| Decision 2: Option A | Hale writes Prompt Charter template; Sterling builds charter completeness check into pre-commit gate |
| Decision 3: Option A | Hale schedules first monthly review; Washington facilitates hotwash component |
| All three | Dembe's JEXS brief + this synthesis → Standing Order draft within 48h |

---

*Col Victoria "Iron Vic" Hale | Thunderbird Wing | 2026-05-16*
*Staff inputs: Castillo, Washington, ELON, Sterling, Dembe | All five files in output/WING_PROTOCOL_DESIGN_20260516/*
