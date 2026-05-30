# Standing Order: Quality Management Integration into WING EXERCISE Protocol
## 16 MAY 2026 | JET → Commander (OpenCode)

**Authority:** Commander directive: "Research Quality Air Force Process Improvement and suggest adding to the exercise protocol AFTER you build this. But keep track of A7 metrics."

**Source:** AF CPI/CI² (AFI 38-401, AFSO21 lineage), DMAIC methodology, 8-Step Problem Solving, AFIT KPI-baseline-target framework.

---

## Proposal: Add Quality Management (QM) Lens to WING EXERCISE Protocol

### What Changes

#### 1. Every T2/T3 exercise requires pre-delegation QM fields

Before any T2/T3 task is dispatched (before staff are invoked), the Prompt Charter MUST include four additional fields:

```
6. DESIRED END STATE: [what does success look like when this is finished?]
7. DEFINITION OF SUCCESS: [specific, measurable — how will we know?]
8. METRICS: [baseline value → target value — what are we moving?]
9. ETC: [estimated time to complete based on current trajectory]
```

**Rationale (AF CPI):** The Air Force 8-Step Problem Solving model requires Step 3 (Set Improvement Target) before Step 4 (Determine Root Causes). Without a measurable target and a baseline, there is no way to verify improvement. DMAIC's Define phase demands the same: problem statement → goal → scope → metrics before Measure begins.

**Enforcement:** Hale fills these in the T2 Prompt Charter (autonomously). Commander fills them in the T3 Prompt Charter (Gate 4 event). If any field is missing, Sterling may hold the exercise at the gate.

#### 2. Quality Review Gate (new Gate 5, T3 only)

A quality review is added after Step 7 (Hotwash) in the T3 sequence:

```
8. Quality Review (Sterling) — Gate 5
   - Were the pre-defined success criteria met? (Y/N/PARTIAL)
   - Were the metrics tracked from baseline to completion?
   - Was ETC accurate? If not, by how much variance?
   - Quality score recorded in exercise log
   - If PARTIAL or NO: DOTMLPF-P finding auto-generated
```

**Rationale (AF CPI):** DMAIC's Control phase requires sustained measurement after improvement. Gateway QA gates are standard in Air Force CPI deployment cycles to prevent "improvement theater" — changes that look good at delivery but don't hold.

#### 3. New Quality Metrics (Sterling dashboard)

| Metric | Target | Red Threshold | Source |
|--------|--------|---------------|--------|
| `exercise_quality_score_pct` | ≥ 85% | < 60% | Quality Review Gate |
| `pre_task_qm_completion_rate` | 100% on T2/T3 | Any missing QM fields | gate log |

These join the existing metrics table (replacing `prompt_charter_completion_rate` since QM fields are part of the charter).

#### 4. QM Training for Staff (Castillo)

Staff should be briefed on the four QM fields and how to evaluate them. Specifically:
- **Every persona** must be able to state, when asked by Sterling: "The end state is X. Success looks like Y. We're tracking Z. ETC is N."
- **Castillo** trains this as part of the T2/T3 classification brief (30-second inline note, not a separate session).

#### 5. Sterling's Expanded Role (already mapped — now explicit)

Sterling's existing authority over `lessons_implementation_rate_pct` is already a QM function. The QM lens formalizes what he was already doing: ensuring exercises produce artifacts, metrics are tracked, and improvement is measured.

---

### Non-Changes (Preserved)

- Castillo still classifies tiers (QM does not change who decides T0-T3)
- Hale still fills the T2 Prompt Charter (QM fields are added to the existing template)
- Commander still fills the T3 Prompt Charter at Gate 4
- Washington's hotwash sequencing is unchanged
- Durable artifact requirement is unchanged
- Monthly deliberate review unchanged (Sterling already presents metrics)

---

### Implementation

1. Update `docs/WING_EXERCISE_PROTOCOL.md` — add QM section, update Prompt Charter templates, add Gate 5
2. Sterling begins tracking `exercise_quality_score_pct` and `pre_task_qm_completion_rate`
3. Castillo adds QM briefing note to T2/T3 classification
4. First Quality Review Gate at first T3 exercise after this SO is committed

---

### Decision

- [x] **Commander approves (full integration)** — 2026-05-16
- [ ] Commander approves with modifications
- [ ] Commander defers / tables

*Standing Order prepared by JET | OpenCode | 2026-05-16*
