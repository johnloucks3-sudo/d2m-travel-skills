# SUCCESSION PLAN ACTIVATION — Recruitment Phase
## Thunderbird Wing — Three Bottleneck Personas
*Activated: 2026-07-06 | Source brief: docs/SUCCESSION_PLANNING_BRIEF.md | Status: RECRUITMENT ONLY — no reassignment*

---

## SCOPE

Recruitment phase only. No persona is reassigned, no client-facing volume shifts, no send authority changes. This phase builds a documented, testable backup capability for three single-point-of-failure roles. Candidates diverge from the original brief where the brief would have created a *new* single point of failure (Luna as sole backup for both Dani and Naia) — see candidate rationale below.

## CANDIDATES

| Role (bottleneck) | Successor candidate | Rationale |
|---|---|---|
| **Dani (A3)** — client-facing voice | **Luna Voss (A6)** | Brief and task agree: closest voice/creative-chain fit, fastest path to readiness. |
| **Naia (EXEC)** — brand-pass authority | **Dani (A3, Moreau)** | Already has proven voice fidelity and client-facing judgment; picking Dani (not Luna) avoids double-loading Luna onto two successions at once. |
| **Sterling (A7)** — process/metrics | **Whetstone (A14)** | Already owns CI razor-sharp/currency rating — closest existing skill match to measurement discipline, waste-detection, and policy authorship. ELON was not selected: his mandate is adoption-biased, the functional opposite of Sterling's audit-and-gate posture. |

## TRAINING PROGRAMS

### 1. Dani successor — Luna Voss (A6)
**Timeline:** 60 days
| Step | Activity |
|---|---|
| (a) | Observe 5 client interactions — full thread, intent to intel-to-response chain |
| (b) | Shadow 2 proposals — Dani writes, Luna reviews and annotates decision points |
| (c) | Draft 1 proposal under Dani review |
| (d) | Handle 1 low-risk client check-in independently |
| (e) | Co-author 1 FPD reminder email with Dani |

**Readiness check:**
- Can Luna synthesize intel from A2 (Dembe)/A9 (Harlan)/COS (Hale)/A8 (Reyes)/A6 (her own narrative lane) into one coherent client voice?
- Can she recall and apply client-specific detail (dietary preferences, prior conversation threads) so the client feels known, not processed?
- Can she hit the 24-hour response SLA under real payment-deadline pressure, not just in low-stakes drafts?

### 2. Naia successor — Dani (A3, Moreau)
**Timeline:** 75 days
| Step | Activity |
|---|---|
| (a) | Audit 5 existing client drafts for voice/tone/brand consistency |
| (b) | Co-author brand-pass review with Naia on 3 drafts |
| (c) | Solo brand-pass review on 2 low-risk drafts, audited by Naia after the fact |
| (d) | Define brand-quality criteria in writing: tone, personalization, "no form-letter feel" |
| (e) | Build Naia's checklist into a repeatable, written rubric other personas can apply |

**Readiness check:**
- Does Dani carry the institutional knowledge of D2M voice needed to judge *other people's* copy, not just write her own?
- Can she kill a bad draft outright, without a softening apology, when the draft doesn't meet the bar?
- Read blind: does the output sound like Naia's gate, not like Dani's own client-voice register bleeding through?

### 3. Sterling successor — Whetstone (A14)
**Timeline:** 90 days
| Step | Activity |
|---|---|
| (a) | Observe 1 full monthly Baldrige sweep (30 min, real-time) |
| (b) | Audit 2 systems independently — one code/CI system, one dossier-sync system |
| (c) | Present findings to Sterling directly (not to Commander) — this is a training gate, not a reporting channel |
| (d) | Co-author 1 standing order with Sterling |
| (e) | Lead 1 deadwood review cycle end-to-end (candidate identification → Sterling audit → KEEP/REMOVE decision → commit) |

**Readiness check:**
- Does Whetstone show measurement discipline — baseline, target, what moves the needle — not just currency/freshness scoring?
- Can he see waste independent of the CI-razor-sharp lens he already owns?
- Can he author policy (a standing order) that holds up under Sterling's own review standard?

## MESSAGING
One-pager per role: `OpsCenter/SUCCESSION_PLAN_MESSAGING.md`

## TIMELINE

| Date | Milestone |
|---|---|
| **2026-07-15** | Recruitment messaging distributed to all three candidates (Luna, Dani, Whetstone) |
| **2026-07-22** | Training begins — all three tracks start in parallel |
| **2026-09-30** | First readiness review — Hale facilitates, domain owner (Dani/Naia/Sterling) + candidate + Commander assess progress against readiness checklist |

## TRACKING
Live status: `hale_state.json` → `succession_training` array (role, candidate_name, training_stage, target_completion_date, readiness_checklist_status). Updated at each milestone; not updated more frequently than that without a status change.

## GATES NOT CROSSED BY THIS PHASE
- No persona is given send authority they don't already have.
- No client-facing volume moves to a candidate before readiness sign-off by the current domain owner.
- No messaging goes out before 2026-07-15 — this activation creates the artifacts only.

---
*— V. Hale, VCS · 2026-07-06*
