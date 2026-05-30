# SO — WING EXERCISE PROTOCOL
## Standing Order 2026-05-16 | Approved: Commander John Loucks
## Classification: Strategy Direction (Gate 4) | Status: ACTIVE

---

## DECISION RECORD

**Commander directive:** Redesign Wing engagement to use formal exercise doctrine for non-urgent work.
**Date decided:** 2026-05-16
**Approved:** C/A/A — Hybrid 4-tier + Prompt Charter + Monthly Deliberate Review

**Staff inputs consulted (this is the protocol's first dogfood case):**
- A5 Castillo (classification authority, tier design)
- A7 Sterling (Prompt Charter, `lessons_implementation_rate_pct`)
- CH Washington (hotwash sequencing, exemption framing)
- A12 ELON (SO conflict analysis, exercise window)
- A2 Dembe (JEXS/JELC doctrine, gap analysis)

**Full exercise record:** `output/WING_PROTOCOL_DESIGN_20260516/`

---

## THE PROTOCOL

**Reference:** `docs/WING_EXERCISE_PROTOCOL.md` — full tier definitions, charter template, classification schema

### Exemption (Washington — time-based, not category-based)
**Any prompt where inaction costs something in the next 24 hours is EXEMPT.**
This catches: client queries, supplier deadlines, pricing releases, payment windows.
Execute-then-report. No protocol applied.

### Four Tiers (Castillo)

| Tier | Trigger | Protocol | Steps | Hotwash |
|---|---|---|---|---|
| **T0** | Routine, repeat (3+ documented runs), <30 min | None — execute-then-report | 0 | None |
| **T1** | Novel, single-domain, single staff | Lightweight | 3 | 3-bullet async |
| **T2** | Multi-domain, 2-3 staff, moderate consequence | Operational | 5 | Async, Hale aggregates one principle |
| **T3** | Strategy direction, Wing doctrine, new operational pattern | Full 7-step | 7 | Full AAR within 24h |

**T3 cap: ≤ 1 per week.** ELON nominates the weekly T3 candidate from the kill audit. If T3 fires more than once in a week, classification is broken — Castillo reviews.

**Classification authority: A5 Castillo.** He calls the tier before any staff engages on T1+.

### Domain Ownership Doctrine (Amendment 2026-05-29)

**Every Wing Exercise is owned by the domain expert, not by Hale.**

- **T1 (single-domain):** Named persona leads Steps 2–3. Hale takes minutes only.
- **T2 (multi-domain):** Named personas each own their domain input. Senior named persona leads Step 3. Hale aggregates the record.
- **T3 (full 7-step):** Domain lead persona owns Steps 2–4. Hale takes executive minutes and produces the synthesis document from those minutes — not from her own analysis.

**Hale's exercise role:** Executive secretary. Records what domain experts produce. Captures decisions. Writes the hotwash document. Does not opine unless asked.

**Classification note:** A5 Castillo classifies all T-tiers including exercises in his own domain. Classification is standing authority, not a conflict.

### ZEN — Mandatory Counter-Voice (Amendment 2026-05-29)

ZEN (OpenCode/DeepSeek counter-voice) appears in every T1, T2, and T3 exercise.

- **Position:** Inline, immediately after domain owner's recommendation — not at end of room.
- **Role:** Structural dissent. Always provides the counter-position. Not a veto — a perspective.
- **Authority:** ZEN does not block decisions. Domain owner hears the counter and proceeds.
- **For T3:** ZEN's counter is captured in Hale's minutes as a named position. Commander sees both.

### Prompt Charter — Required for T2/T3 (Sterling)

Before any staff is spun up on T2 or T3, the charter must be filled. Hale flags incomplete charters to Commander before any staff is engaged — she does not block independently.

```
PROMPT CHARTER
--------------
1. SUCCESS CRITERIA: What does "done" look like? (specific, verifiable)
2. SCOPE IN/OUT: What is explicitly excluded from this prompt?
3. NAMED STAFF: Which personas, and why each? (one sentence per)
4. TOKEN/TIME BUDGET: What's acceptable? (e.g., "<5K tokens, <20 min")
5. EXIT CONDITION: At what point do we stop and reassess?
```

For T3: Commander fills the charter (Gate 4 event).
For T2: Hale fills from context (autonomous — within 95% band).
For T0/T1: No charter required.

### The 7-Step Sequence (T3 only)

1. **Prompt** — Charter-complete, classified T3 by Castillo
2. **Staff Discussion** — Named staff provide independent input (no Hale synthesis first)
3. **Domain Owner Red-Team + ZEN Counter** — Lead persona challenges their own recommendation (90 seconds). ZEN provides structural counter-voice. Hale records both positions.
4. **Hale Minutes Capture** — Hale captures the domain owner's synthesis and decisions verbatim. The domain owner's consensus position is the exercise record. Hale does not generate analysis — she captures it.
5. **Commander Decision** — Gate 4 — Commander approves or redirects
6. **Action** — Hale executes within SO-2026-05-04 authority
7. **Hotwash** — Two tiers: immediate verbal (<60 min) + formal AAR (<24h). Senior speaks last, owns error first.

### Hotwash → Document Improvement (Anti-Theater Rule)

**Every formal AAR produces a durable artifact within 7 days** — or the hotwash did not happen in any measurable sense (Dembe: "if no file changes, the lesson did not propagate").

Acceptable artifacts: CLAUDE.md edit, Standing Order, code commit, `hale_decisions.md` entry.

**Metric (Sterling owns):** `lessons_implementation_rate_pct` — target ≥ 80%. Red threshold: below 50% at 60 days triggers halt and redesign. Reported weekly in Sterling's metrics dashboard.

**DOTMLPF-P routing:** Sterling classifies each hotwash finding by category (Doctrine, Organization, Training, Materiel, Leadership, Personnel, Facilities, Policy) to route it to the right owner.

### Monthly Wing Deliberate Review (Washington facilitates)

- **Cadence:** First of each month
- **Duration:** 30 minutes
- **Format:** Hale facilitates. Sterling presents `lessons_implementation_rate_pct` and open findings. Commander decides on any doctrine changes.
- **Purpose:** Institutional learning checkpoint — not operational health (Sterling's weekly dashboard covers that). The question asked: "Are we a learning organization?"
- **First review:** 2026-06-01

---

## QUALITY MANAGEMENT LENS (Incorporated from SO_QUALITY_MANAGEMENT_20260516 — 2026-05-30)

*Source: AF CPI/CI² (AFI 38-401, AFSO21 lineage), DMAIC methodology, 8-Step Problem Solving, AFIT KPI-baseline-target framework. Commander-approved 2026-05-16.*

### 1. Pre-Delegation QM Fields (T2/T3 Prompt Charter — Mandatory)

Before any T2/T3 task is dispatched, the Prompt Charter MUST include four additional fields beyond the standard five:

```
6. DESIRED END STATE: [what does success look like when this is finished?]
7. DEFINITION OF SUCCESS: [specific, measurable — how will we know?]
8. METRICS: [baseline value → target value — what are we moving?]
9. ETC: [estimated time to complete based on current trajectory]
```

**Enforcement:** Hale fills these in the T2 Prompt Charter (autonomously). Commander fills them in the T3 Prompt Charter (Gate 4 event). If any field is missing, Sterling may hold the exercise at the gate.

**Rationale:** AF 8-Step Problem Solving requires Step 3 (Set Improvement Target) before Step 4 (Determine Root Causes). Without a measurable target and baseline, there is no way to verify improvement.

### 2. Quality Review Gate (Gate 5 — T3 only)

Added after Step 7 (Hotwash) in the T3 sequence:

```
8. Quality Review (Sterling) — Gate 5
   - Were the pre-defined success criteria met? (Y/N/PARTIAL)
   - Were the metrics tracked from baseline to completion?
   - Was ETC accurate? If not, by how much variance?
   - Quality score recorded in exercise log
   - If PARTIAL or NO: DOTMLPF-P finding auto-generated
```

### 3. Quality Metrics (Sterling Dashboard)

| Metric | Target | Red Threshold | Source |
|--------|--------|---------------|--------|
| `exercise_quality_score_pct` | ≥ 85% | < 60% | Quality Review Gate |
| `pre_task_qm_completion_rate` | 100% on T2/T3 | Any missing QM fields | gate log |

These join the existing metrics table alongside `lessons_implementation_rate_pct`.

### 4. Staff QM Awareness (Castillo)

Every persona must be able to state when asked by Sterling: "The end state is X. Success looks like Y. We're tracking Z. ETC is N." Castillo trains this as part of the T2/T3 classification brief — 30-second inline note, not a separate session.

---

## STANDING AUTHORITIES GRANTED BY THIS ORDER

1. **A5 Castillo** — Classification authority for T0/T1/T2/T3, including exercises in his own domain. His call is final. If COS disagrees, surface to Commander once; then execute Castillo's classification.
2. **Hale** — Prompt Charter completion authority for T2 (autonomous, no Commander gate).
3. **Hale** — Executive minutes capture for all T1/T2/T3 exercises. Records domain owner positions, ZEN counter, and decisions. Produces the hotwash document. Does not opine unless directly asked.
4. **Sterling** — `lessons_implementation_rate_pct` metric ownership. Authority to flag RED and request halt/redesign at 60-day threshold.
5. **ELON** — Weekly T3 candidate nomination from kill audit. One per week, no more.
6. **Domain Experts (all named BG-equivalent personas)** — Each persona is the standing authority in their domain. Within a Wing Exercise touching their domain, their recommendation is the wing's position until Commander overrides. They do not seek Hale approval to recommend. They run the exercise. Hale takes their minutes.

---

## WHAT DOES NOT CHANGE

- SO-2026-05-04 (Real Autonomy Charter) remains fully in effect. T0/T1/T2 execute-then-report inside Hale's 95% autonomy band. Only T3 involves a Commander decision gate, and only because T3 is by definition a strategy-direction event that was already Gate 4.
- Client queries remain exempt per Washington's time-based framing.
- WF-17 (client send gate) is unaffected.
- Four gates are unchanged.

---

*Standing Order — Wing Exercise Protocol | 2026-05-16 | Approved: Commander | Executed: Hale*
*Amendment 2026-05-29 — Domain Ownership Doctrine + ZEN Mandatory Counter | Four staff votes: Sterling (Approve), Castillo (ZEN Counter → Option A), Washington (Approve), Hale (Approve Option C)*
*Reference file: `docs/WING_EXERCISE_PROTOCOL.md`*
