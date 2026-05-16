# WING EXERCISE PROTOCOL — FULL REFERENCE
## Standing Order 16 MAY 2026 | Thunderbird Wing, Dreams2Memories Travel, LLC

**Binding summary:** `CLAUDE.md` (⚠️ HARD RULE section)
**Decision record + staff inputs:** `standing_orders/SO_WING_EXERCISE_PROTOCOL_20260516.md`

---

## DOCTRINE BASIS

Adapted from JELC (Joint Exercise Life Cycle, CJCSM 3500.03F) five-phase model:
Design → Planning → Preparation → Execution → Evaluation/Analysis/Reports

Wing adaptation compresses 12-24 month military exercise cycle to minutes-to-hours. Three elements translated directly; observer/controller bureaucracy discarded entirely.

**Key doctrinal principle (Dembe):** Every AAR must feed the next exercise's design phase. Every formal AAR must produce at least one committed change to an operational file. If no file changes, the lesson did not propagate.

---

## CLASSIFICATION SCHEMA (A5 Castillo — authority owner)

### How to Classify

Castillo calls the tier **before any staff engages on T1+**. Classification happens at prompt intake.

**Exemption check first:**
> Does inaction on this prompt cost something in the next 24 hours?
> → YES: Exempt. T0 execute-then-report. No protocol.
> → NO: Continue to tier check.

**Tier determination:**

| Question | T1 if... | T2 if... | T3 if... |
|---|---|---|---|
| How novel? | First time, similar to documented pattern | First time, no close precedent | Sets new Wing doctrine or changes operational baseline |
| How many domains? | Single domain (one persona's expertise) | 2-3 domains, requires synthesis | Wing-wide or strategy-level |
| Consequence if wrong? | Recoverable easily | Moderate — takes time to fix | Hard to reverse, affects clients or standing commitments |
| Repeat factor? | 3+ documented runs → T0 | — | — |

**Kill threshold for T3:** If T3 fires more than once per week, classification is broken. Castillo reviews and tightens criteria. ELON nominates the one weekly T3 candidate from the kill audit.

---

## T0 — ROUTINE (No Protocol)

**Trigger:** Repeat pattern (3+ documented runs), <30 min estimated execution, single domain.

**Execution:** Execute-then-report. Hale operates inside SO-2026-05-04 autonomy band.

**Hotwash:** None.

---

## T1 — TACTICAL (Lightweight Protocol)

**Trigger:** Novel task, single-domain, single staff member, <2h estimated.

**Steps:**
1. Prompt (exemption check → T1 classified by Castillo)
2. Single named staff member provides input
3. Action (Hale executes)

**Hotwash:** 3-bullet async within 60 min of completion. Staff member completes.

**Prompt Charter:** Not required.

---

## T2 — OPERATIONAL (Standard Protocol)

**Trigger:** Multi-domain, 2-3 staff required, moderate consequence.

**Steps:**
1. Prompt + Prompt Charter (Hale fills autonomously)
2. 2-3 named staff provide independent input (no synthesis first — staff speaks before Hale frames)
3. Hale Red-Team Scan (90-second adversarial review — standing protocol, no gate)
4. Hale Synthesis (integrates staff inputs)
5. Action (Hale executes — within 95% autonomy band unless hits a gate)

**Hotwash:**
- Immediate verbal (within 60 min): What happened? What worked? What didn't?
- Formal AAR (within 24h if warranted): DOTMLPF-P classified findings → routed to owners

**Durable artifact required within 7 days.**

**Prompt Charter — Hale completes before staff engages:**
```
PROMPT CHARTER — T2
-------------------
1. SUCCESS CRITERIA: [specific, verifiable — what does "done" look like?]
2. SCOPE IN/OUT: [what is explicitly excluded?]
3. NAMED STAFF: [persona 1 — why] / [persona 2 — why] / [persona 3 — why if applicable]
4. BUDGET: [token target] / [time target]
5. EXIT CONDITION: [at what point do we stop and reassess?]
```

---

## T3 — STRATEGIC/FULL (Full 7-Step)

**Trigger:** Strategy direction, Wing doctrine change, new operational pattern, high consequence or hard to reverse. ≤ 1/week cap.

**Steps:**
1. **Prompt** — Charter-complete, classified T3 by Castillo, ELON nominates weekly candidate
2. **Staff Discussion** — Named staff provide independent input. Hale does NOT synthesize first. Staff speaks before the frame is set.
3. **Hale Red-Team Scan** — 90-second adversarial review before synthesis. Fills JEXS wargaming gap.
4. **Hale Synthesis** — Integrates staff inputs, identifies key decisions, presents options
5. **Commander Decision** — Gate 4. Commander approves, redirects, or returns for more staff input
6. **Action** — Hale executes within SO-2026-05-04 authority
7. **Hotwash** — Two tiers:
   - Immediate verbal (<60 min of completion): quick debrief
   - Formal AAR (<24h): structured, written, DOTMLPF-P classified

**Prompt Charter — Commander fills (Gate 4 event):**
```
PROMPT CHARTER — T3
-------------------
1. SUCCESS CRITERIA: [specific, verifiable — what does "done" look like?]
2. SCOPE IN/OUT: [what is explicitly excluded?]
3. NAMED STAFF: [persona + rationale for each]
4. BUDGET: [token target] / [time target] / [calendar deadline]
5. EXIT CONDITION: [at what point do we stop and reassess?]
```

**T3 hotwash sequencing (Washington):**
- Executing staff speaks first
- Supporting staff speaks second
- Hale speaks third
- Commander speaks last and owns error first if applicable
- No senior person frames the debrief before junior staff speaks — or it becomes theater

---

## HOTWASH → DOCTRINE UPDATE PIPELINE

### Two-Tier Hotwash Structure

**Tier 1 — Immediate Verbal (within 60 min):**
- What happened?
- What worked as expected?
- What didn't work?
- What should change next time?
- No documentation required — this is the fast flush.

**Tier 2 — Formal AAR (within 24h, required for T3, optional for T2):**
- Structured written document
- DOTMLPF-P classification of each finding
- Assigned owner per finding
- Committed change target within 7 days

### DOTMLPF-P Routing (Sterling)

| Category | What it means | Owner |
|---|---|---|
| D — Doctrine | How we decide and operate | Hale → CLAUDE.md |
| O — Organization | Staff structure and roles | Hale → hale_decisions.md |
| T — Training | How staff learns and develops | Castillo → staff briefs |
| M — Materiel | Tools, systems, infrastructure | ELON → kill audit |
| L — Leadership | Decision authority and escalation | Hale + Commander |
| P — Personnel | Persona assignments and capabilities | Hale → hale_state.json |
| F — Facilities | Infrastructure (servers, tunnels, etc.) | Hale → OpsCenter |
| P — Policy | Standing Orders, rules, gates | Hale → SO drafts |

### Durable Artifact Requirement

Every formal AAR produces at least one committed change within 7 days:
- ✅ CLAUDE.md edit (committed to git)
- ✅ New or updated Standing Order
- ✅ Code commit (new tool, gate, or process)
- ✅ `hale_decisions.md` entry with action assigned
- ❌ "Discussion noted" — does NOT count
- ❌ Entry in a file nobody reads — does NOT count

**Sterling tracks:** If no artifact within 7 days, hotwash is marked INCOMPLETE. `lessons_implementation_rate_pct` drops. Red threshold at <50% triggers halt and redesign.

---

## METRICS (Sterling owns — weekly dashboard)

| Metric | Target | Red Threshold | Source |
|---|---|---|---|
| `lessons_implementation_rate_pct` | ≥ 80% | < 50% at 60 days | AAR tracking |
| `t3_per_week` | ≤ 1 | > 1 = classification broken | exercise log |
| `prompt_charter_completion_rate` | 100% on T2/T3 | Any T2/T3 without charter | gate log |
| `approved_model_utilization_pct` | ≥ 95% | < 80% | `a7_model_audit_gate.py` |
| `or_cost_7d` | < $0.50 | > $2.00 | Sterling dashboard |

Dashboard: `output/STERLING_METRICS_DASHBOARD.md` (weekly update by Sterling)

---

## MONTHLY WING DELIBERATE REVIEW

**Cadence:** First of each month  
**Duration:** 30 minutes  
**Facilitator:** Hale  
**Presenter:** Sterling (`lessons_implementation_rate_pct`, open findings)  
**Decision authority:** Commander (doctrine changes only — operational items are Hale's)

**Agenda:**
1. Sterling presents: rate, open findings, DOTMLPF-P routing status (10 min)
2. Hale presents: patterns from the month's T2/T3 exercises (10 min)
3. Commander decides: which findings become doctrine changes (10 min)

**First review:** 2026-06-01

---

## WHAT DOES NOT CHANGE

- SO-2026-05-04 (Real Autonomy Charter) — fully in effect
- Four gates — unchanged (client send, financial, new client, strategy)
- WF-17 — unchanged
- T0/T1/T2 operate inside Hale's 95% autonomy band
- Only T3 is a Commander gate — because T3 is already a Gate 4 strategy event by definition

---

*Wing Exercise Protocol — Full Reference | v1.0 | 2026-05-16*
*SO binding summary in CLAUDE.md | Decision record in standing_orders/SO_WING_EXERCISE_PROTOCOL_20260516.md*
