# THUNDERBIRD WING — METRICS FRAMEWORK
## Version: 1.0 | Adopted: 2026-05-29 | Authority: Issue 5 Commander Vote
## Domain Owner: A7 Sterling | Framework: SMART+O/S

---

## THE FRAMEWORK — SMART+O/S

Every wing metric must satisfy all 7 attributes before adoption.

| Attribute | Definition | Failure mode if missing |
|---|---|---|
| **S**pecific | Measures exactly one thing, unambiguously defined | Metric drifts, means different things to different personas |
| **M**easurable | A number can be produced from a known data source on a known cadence | Cannot determine if target is met |
| **A**chievable | Target is realistic given wing capacity and current data availability | Permanent red = demoralization, not improvement |
| **R**elevant | Directly tied to a D2M mission outcome: revenue, client experience, or operational integrity | Measurement theater — activity with no behavioral impact |
| **T**ime-bound | Explicit review cadence (daily/weekly/monthly) + target review date | Metrics accumulate; no one acts; no one retires stale ones |
| **O**wned | Named persona carries the metric — accountable for data quality and target |  Orphaned metrics decay silently |
| **S**ourced | Named primary data source (TESS, dossier, lifecycle engine, Git, decision_ledger) | Fabrication risk — same risk as client email Rule 4 |

**Guiding principle:** *"If it does not get measured, it cannot be improved."*

Sterling's office receives all metric nominations. Nominations that fail any SMART+O/S attribute are returned before wing exercise. No exceptions.

---

## ADOPTED WING-WIDE METRICS (Issue 5, 2026-05-29)

### Metric 1 — `lifecycle_adherence_pct`
| Field | Value |
|---|---|
| **Definition** | TPs delivered on or before scheduled date ÷ TPs due in period × 100 |
| **Target** | ≥ 85% |
| **Source** | Lifecycle engine + dossiers |
| **Cadence** | Weekly (Monday morning brief) |
| **Owner** | Hale |
| **Agent** | AGT-009 (decision_ledger_scan includes TP sweep) |
| **Status** | ADOPTED |

### Metric 2 — `domain_autonomy_rate_pct`
| Field | Value |
|---|---|
| **Definition** | BG-level decisions in decision_ledger.jsonl ÷ total logged decisions × 100 |
| **Target** | ≥ 88% (authority matrix design target) |
| **Source** | data/decision_ledger.jsonl |
| **Cadence** | Weekly |
| **Owner** | Sterling |
| **Agent** | AGT-010 |
| **Status** | ADOPTED — ledger build required first |

### Metric 3 — `wf17_first_pass_rate`
| Field | Value |
|---|---|
| **Definition** | Client drafts approved by Commander at first WF-17 review ÷ total WF-17 reviews × 100 |
| **Target** | ≥ 90% |
| **Source** | hale_decisions.md (WF-17 log) |
| **Cadence** | Monthly |
| **Owner** | Hale |
| **Status** | ADOPTED — manual tracking until log automation |

### Metric 4 — `revenue_pipeline_usd`
| Field | Value |
|---|---|
| **Definition** | Sum of D2M commission share across all upcoming voyages (within 12 months) |
| **Target** | ≥ $25,000 (Q3 floor — baseline to be validated at first 3 months) |
| **Source** | TESS + commission sheet (Harlan primary) |
| **Cadence** | Weekly (already in morning brief) |
| **Owner** | Harlan |
| **Agent** | AGT-006 (weekly financial pulse) |
| **Status** | ADOPTED — already live, formally named |
| **Note** | Target is provisional — Harlan flags if baseline data shows $25K is not achievable |

### Metric 5 — `lessons_implementation_rate_pct` *(pre-existing, formally adopted)*
| Field | Value |
|---|---|
| **Definition** | Hotwash findings with durable artifacts produced ÷ total formal AAR findings × 100 |
| **Target** | ≥ 80%. Red threshold: < 50% at 60 days triggers halt and redesign |
| **Source** | Wing Exercise hotwash records + Git commits |
| **Cadence** | Weekly |
| **Owner** | Sterling |
| **Agent** | AGT-008 |
| **Status** | ADOPTED (pre-existing + formally registered) |
| **Reference** | output/STERLING_METRICS_DASHBOARD.md |

### Metric 6 — `client_win_rate_pct` *(PENDING — intake funnel dependency)*
| Field | Value |
|---|---|
| **Definition** | Booked clients ÷ qualified inquiries received × 100 |
| **Target** | TBD at activation |
| **Source** | Navarro Gmail thread scraper (AGT-018) — NOT LIVE |
| **Cadence** | Monthly |
| **Owner** | Castillo |
| **Status** | PENDING — tracked but not reported until Navarro intake funnel is operational (2026-06-15 target) |
| **Note** | Commander approved with flag. Castillo owns. Activates when denominator is clean. |

---

## DOMAIN-SPECIFIC METRICS — NOMINATION CYCLE

### Process
1. Sterling issues **Metric Identification Brief** to each BG persona (template below)
2. Each BG submits one domain metric nomination within 14 days using SMART+O/S spec
3. Sterling gates each submission — returns anything incomplete
4. Approved nominations go to Wing Exercise (T2) for cross-domain review
5. Commander adoption vote at 2026-06-15 Monthly Deliberate Review

### Deadline
**BG submissions due: 2026-06-12** (3 days before Monthly Review)

### Submissions tracker
| Persona | Domain | Status | Metric Submitted |
|---|---|---|---|
| A2 Dembe | Intel | Pending | — |
| A3 Dani | Client comms | Pending | — |
| A5 Castillo | Strategy | Pending | — |
| A7 Sterling | Process/tech | Auto-adopted (`lessons_implementation_rate_pct`) | ✅ |
| A8 Reyes | Experience | Pending | — |
| A9 Harlan | Finance | Pending | — |
| A12 ELON | Automation | Pending | — |

### Submission Template (SMART+O/S)
```
METRIC NOMINATION — [Persona] ([Domain])
Submitted: [date]

Metric name: [snake_case_name]
Definition: [exactly one thing measured, no ambiguity]
Formula: [how the number is calculated]
Target: [specific number or range]
Source: [named data source — file path or system]
Cadence: [daily / weekly / monthly]
Owner: [persona name]
Achievability note: [why this target is realistic now]
Relevance: [which D2M mission outcome this drives]
```

---

## STERLING'S METRICS GOVERNANCE RULES

1. **No metric adopted without all 7 SMART+O/S attributes** — returned before wing exercise, no exceptions.
2. **No target set without a baseline** — new metrics launch with 90-day observation window before target is formalized.
3. **Red threshold is mandatory** — every metric defines the number at which Sterling escalates to Commander.
4. **Metrics are retired** — ELON kill audit reviews all metrics quarterly. Any metric with < 3 months of clean data and no behavioral change evidence is nominated for retirement.
5. **Financial metrics require Harlan source verification** — same Rule 5 logic as client emails. Portal figure authoritative.
6. **Maximum 12 wing-wide metrics** — same cap discipline as Standing Orders. Metric debt is real.

---

*Wing Metrics Framework v1.0 | Issue 5 approved 2026-05-29 | Sterling domain authority*
*Next review: 2026-06-15 Monthly Deliberate Review — domain metric nominations due 2026-06-12*
