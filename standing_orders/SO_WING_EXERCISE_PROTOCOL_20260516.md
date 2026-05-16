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

### Prompt Charter — Required for T2/T3 (Sterling)

Before any staff is spun up on T2 or T3, the charter must be filled. Hale rejects incomplete charters.

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
3. **HALE Red-Team Scan** — 90-second adversarial review before synthesis (Dembe gap, filled as standing protocol)
4. **HALE Synthesis** — Integrates staff inputs, identifies decisions
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

## STANDING AUTHORITIES GRANTED BY THIS ORDER

1. **A5 Castillo** — Classification authority for T0/T1/T2/T3. His call is final. If COS disagrees, surface to Commander once; then execute Castillo's classification.
2. **Hale** — Prompt Charter completion authority for T2 (autonomous, no Commander gate).
3. **Hale** — 90-second red-team scan as standing protocol before any T2/T3 synthesis.
4. **Sterling** — `lessons_implementation_rate_pct` metric ownership. Authority to flag RED and request halt/redesign at 60-day threshold.
5. **ELON** — Weekly T3 candidate nomination from kill audit. One per week, no more.

---

## WHAT DOES NOT CHANGE

- SO-2026-05-04 (Real Autonomy Charter) remains fully in effect. T0/T1/T2 execute-then-report inside Hale's 95% autonomy band. Only T3 involves a Commander decision gate, and only because T3 is by definition a strategy-direction event that was already Gate 4.
- Client queries remain exempt per Washington's time-based framing.
- WF-17 (client send gate) is unaffected.
- Four gates are unchanged.

---

*Standing Order — Wing Exercise Protocol | 2026-05-16 | Approved: Commander | Executed: Hale*
*Reference file: `docs/WING_EXERCISE_PROTOCOL.md`*
