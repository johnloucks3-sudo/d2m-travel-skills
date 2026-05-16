# A7 PROCESS INPUT — WING PROMPT PROTOCOL DESIGN
**Gauge — Brig Gen (Ret.) Thomas "Gauge" Sterling, A7**
**Date: 2026-05-16 | Classification: Gate 4 Strategic Input**

---

## BLUF

This protocol is sound in intent and structurally broken in one place: it collides head-on with SO-2026-05-04. That SO banned "Awaiting confirmation" and mandated Execute+Report at 95% autonomy. A staff-discussion/synthesis/decision cycle before action is a permission-seeking loop by another name. The resolution is not to kill the protocol — it is to define a **route classifier** that determines which prompts enter the slow path and which execute autonomously. Commander's own exemption ("client-focused queries") shows he is already thinking classifier. We need to formalize it or every non-urgent prompt acquires drag. That is waste. Waste is theft from the client experience.

---

## Q1 — WHAT GETS MEASURED

**Five KPIs. Instrumented via extension of `OpsCenter/task_audit_log.jsonl`. No new infrastructure.**

| KPI | Unit | Green | Red | Owner |
|---|---|---|---|---|
| `prompt_cycle_time_minutes` | Minutes (median, slow-path only) | <45 min | >90 min | Hale |
| `staff_engagement_count_per_prompt` | Count (mean, slow-path) | 2-4 staff | <2 or >6 | A7 Sterling |
| `decision_reversal_rate_pct_30d` | Pct reversals / decisions in 30d | <10% | >20% | Hale |
| `lessons_implementation_rate_pct` | Hotwash findings with durable artifact in 7 days | >80%; <50% = protocol failed | <50% at 60d = halt | A7 Sterling |
| `cost_per_prompt_usd` | USD (token spend, slow vs fast path) | Slow <$0.15; Fast <$0.03 | Slow >$0.40 | A7 Sterling |

**Instrumentation:** Add four fields to every `task_audit_log.jsonl` entry: `route_path` (slow|fast), `staff_engaged[]`, `hotwash_artifact_url`, `token_cost_usd`. Hale populates at task close. A7 reads daily at 06:30 MT. No new daemon required.

---

## Q2 — QUALITY GATE DESIGN (THE PROMPT CHARTER)

The pre-commit equivalent for a prompt is a **Prompt Charter** — five required fields Hale enforces before convening staff. Incomplete charter = prompt returned to Commander or sender without staff consumption.

**Prompt Charter (required fields):**
1. **Success Criteria** — What does done look like? One sentence, testable.
2. **Scope In/Out** — Explicit list of what is and is not in scope.
3. **Named Staff + Rationale** — Which personas, and why each one specifically.
4. **Token/Time Budget** — Estimated cost band and time-to-decision ceiling.
5. **Exit Condition** — Under what circumstance does this go straight to Execute without full cycle?

**Route classifier (addresses SO-2026-05-04 conflict):** Hale runs classification on intake. Slow-path criteria: (a) crosses or approaches a Standing Order, (b) involves >$500 financial exposure, (c) affects two or more client relationships, (d) represents a process or architecture change. Everything else: fast-path, Execute+Report, autonomy posture unchanged. Client-focused queries are categorically fast-path per Commander directive.

The classifier is the gate. The charter is the instrument. Hale owns both. Gate is silent — no "Should I route this slowly?" phrasing.

---

## Q3 — AAR/BALDRIGE EQUIVALENT FOR THE WING (THE HOTWASH)

**Doctrine base:** Apply Army TC 25-20 AAR structure: intent vs actual, gap origin (system/routing/persona/data), durable fix. Adapted for the Wing:

**Format:** The Wing Hotwash is a **single structured file** in `output/hotwash/HOTWASH_YYYYMMDD_[task_id].md`. Hale facilitates. Each contributing persona submits one paragraph max. A7 reads all outputs and distills to ONE finding.

**Frequency:** Every slow-path prompt. Fast-path prompts get a micro-hotwash (one sentence in task_audit_log.jsonl field `micro_aar`) when outcome deviated from expected. Full quarterly Baldrige sweep pulls all micro-AARs and identifies systemic patterns.

**Anti-theater rule (hard):** Every hotwash closes with exactly one of the following durable artifacts: (a) CLAUDE.md edit, (b) new or revised Standing Order, (c) hook or code change committed, (d) hale_decisions.md entry with owner and date. If the hotwash produces no artifact, `lessons_implementation_rate_pct` drops. That metric is RED-flagged to Hale before her 07:00 brief. No artifact = the hotwash did not happen in any meaningful sense.

**Baldrige alignment:** This maps to the Process category (systematic improvement loops) and the Results category (measurable, trended outcomes). The compounding rule applies: every finding becomes permanent — a hook entry, an SO, a code guard. One-time fixes are not findings. They are symptoms.

**DOTMLPF-P lens for hotwash scope:** Every finding is classified: Doctrine (SOs), Organization (staff roles), Training (persona calibration), Materiel (tools/infra), Leadership (Hale routing), Personnel (persona activation), Facilities (infra), Policy (gates). Classification forces specificity and routes the fix to the right owner.

---
*A7 Sterling | Process, Technology, Metrics | 2026-05-16*
