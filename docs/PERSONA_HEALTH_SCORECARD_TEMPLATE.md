# PERSONA HEALTH SCORECARD — Thunderbird Wing Monthly Audit
**Baldrige Operational Excellence Framework — Standing Order 2026-06-01**
*Authority: A7 Sterling | Audience: Sunday morning operational review (1st of month, 30 min)*

---

## OVERVIEW

Seven core operational personas drive Thunderbird Wing's execution. This scorecard quantifies their performance across domain-specific metrics so the wing can identify capability gaps, track improvement, and ensure no persona operates as a black box.

**Cadence:** Monthly, every 1st of the month (Sunday morning preferred). Reviews conducted by Sterling (A7); summary briefed to Commander by Hale.

**Scoring:** Each metric produces a single month-over-month data point. Green/Yellow/Red thresholds indicate health. Trends tracked quarterly.

**Output:** One scorecard per review cycle. Historical row appended to `hale_decisions.md` for continuity. Metric deltas surface in monthly Deliberate Review (1st of month).

---

## METRIC DEFINITIONS & THRESHOLDS

### 1. HALE — Ms. Victoria Hale, SES-6 (Chief of Staff)

**Metric 1a: Decision Velocity**
- **What counts:** Routing decisions (task assignments), autonomy calls (Execute vs. Gate), staff disputes resolved, priority resets
- **What doesn't:** Opinion statements, advisory notes, questions to Commander
- **Measurement:** Count weekly, report monthly average (decisions/week)
- **Success targets:**
  - 🟢 **GREEN:** 8–12 decisions/week
  - 🟡 **YELLOW:** 6–7 or 13–14 decisions/week
  - 🔴 **RED:** <6 or >14 decisions/week (underutilized or thrashing)
- **Note:** Decisions should cluster around M–W; weekend spikes indicate rework

**Metric 1b: Staff Capability Lift**
- **What counts:** New skills deployed (scripting, methodology, tool adoption), training hours logged, subordinate promotions/role shifts, documented lessons shared
- **What doesn't:** Tactical task completion, routine assignments
- **Measurement:** Quarterly count + monthly flavor (any training/lift event?)
- **Success targets:**
  - 🟢 **GREEN:** ≥1 new capability deployed per month
  - 🟡 **YELLOW:** New capability every 6–8 weeks
  - 🔴 **RED:** No new capability in >8 weeks (staff stagnation flag)

**Metric 1c: Autonomy Band**
- **What counts:** Work Hale executes and reports (vs. requests permission first). Scope: routing, task assignment, staff management, own outputs, scanner duties
- **What doesn't:** WF-17 gate holds (intentional), financial holds (intentional), strategy approvals (intentional)
- **Measurement:** Sample 4 weeks of Hale activity; classify each decision/action as Execute-Report vs. Request-Permission. % Execute-Report = autonomy band
- **Success targets:**
  - 🟢 **GREEN:** 90–95% Execute-Report (per SO-2026-05-04 charter)
  - 🟡 **YELLOW:** 80–89% Execute-Report
  - 🔴 **RED:** <80% Execute-Report (over-gating, compliance mode)
- **Note:** Below 90% triggers coaching; above 95% reviews for over-confidence

**Metric 1d: WF-17 Quality Gate**
- **What counts:** Drafts held at WF-17 due to errors, incomplete chain, facts unverified, tone drift, missing sig block
- **What doesn't:** Drafts passed (implicit pass = quality OK)
- **Measurement:** Count holds/month + reason code (creative, facts, process, tone, sig). % of total WF-17 inputs
- **Success targets:**
  - 🟢 **GREEN:** ≤5% hold rate (1–2 holds per 20 inputs)
  - 🟡 **YELLOW:** 5–10% hold rate
  - 🔴 **RED:** >10% hold rate (process breakdown, need escalation)
- **Note:** Track reason codes monthly; trending "facts" or "tone" flags staff training need

---

### 2. NAIA SOLBERG-VEGA (EXEC — Brand/Voice)

**Metric 2a: Brand-Pass Turnaround**
- **What counts:** Wall-clock time from Dani→Naia inbox receipt to Naia sign-off (or return with feedback)
- **What doesn't:** Drafts Naia doesn't receive (A3 responsibility)
- **Measurement:** Median hours, 4-week rolling window. Separate "first pass" vs. "rework pass"
- **Success targets:**
  - 🟢 **GREEN:** Median <4h first pass, <2h rework
  - 🟡 **YELLOW:** Median 4–6h first, 2–4h rework
  - 🔴 **RED:** Median >6h first, >4h rework (bottleneck)
- **Note:** SLA is implicit; turnaround time signals availability and workload. If >6h, flag channel (Telegram vs. email) for routing optimization

**Metric 2b: Iteration Rate**
- **What counts:** How many pass cycles before Naia sign-off? (1 pass = first submission approved as-is; 2 passes = one rework; etc.)
- **What doesn't:** Commander/Hale final tweaks (post-Naia approval)
- **Measurement:** Average iterations per month (count total iterations ÷ total drafts)
- **Success targets:**
  - 🟢 **GREEN:** <1.2 iterations/draft (most approved first pass; occasional rework)
  - 🟡 **YELLOW:** 1.2–1.5 iterations/draft
  - 🔴 **RED:** >1.5 iterations/draft (Dani not meeting voice bar pre-Naia; process failing)
- **Note:** >1.5 triggers joint Naia-Dani coaching; indicates pre-gate gaps

**Metric 2c: Client Voice Consistency**
- **What counts:** Unsolicited client feedback on tone/voice (compliments, concerns, mismatch flags)
- **What doesn't:** Factual corrections, product feedback unrelated to voice
- **Measurement:** Monthly feedback tally. Calculate "positive" (feels right, warm, etc.) vs. "concern" (too formal, too casual, off-brand) ratio
- **Success targets:**
  - 🟢 **GREEN:** Ratio ≥3:1 positive:concern, net zero trend month-over-month
  - 🟡 **YELLOW:** Ratio 2:1–3:1 positive:concern, or 1+ concern trending up
  - 🔴 **RED:** Ratio <2:1 positive:concern, or 3+ concerns in month (voice drift, brand risk)
- **Note:** Concerns surface in post-send client replies, Dani feedback, or unsolicited messages. Flag pattern early

---

### 3. NAVARRO (A1 — Client Intake/Profile)

**Metric 3a: Profile Accuracy**
- **What counts:** Post-delivery client feedback on "feels understood" (closed-loop survey or unsolicited comment)
- **What doesn't:** Bookings completed (outcome), profile completeness (process), Navarro's self-assessment
- **Measurement:** % of delivered clients (within 30 days of cruise) who confirm "dossier captures who we are" (explicit or implicit)
- **Success targets:**
  - 🟢 **GREEN:** ≥85% feel understood (27+ of 32 recent clients)
  - 🟡 **YELLOW:** 70–84% feel understood
  - 🔴 **RED:** <70% feel understood (profile misses key signals, rework required)
- **Note:** Survey vehicle = follow-up check-in email post-cruise. If survey not conducted, estimate from unsolicited feedback volume

**Metric 3b: Confidence Calibration**
- **What counts:** Do HIGH-confidence profiles (Navarro marked "strong fit" or "locked archetype") fail delivery more often than MEDIUM-confidence?
- **What doesn't:** Client dissatisfaction unrelated to profile accuracy
- **Measurement:** Failure rate HIGH vs. MEDIUM (failure = post-delivery "doesn't match" feedback or Reyes experience rework). Compare as ratio
- **Success targets:**
  - 🟢 **GREEN:** HIGH failure rate ≤ MEDIUM failure rate (confidence is justified)
  - 🟡 **YELLOW:** HIGH failure rate 1.2–1.5x MEDIUM (slightly overconfident)
  - 🔴 **RED:** HIGH failure rate >1.5x MEDIUM (confidence not calibrated; risk)
- **Note:** Small sample size (4–6 profiles/month) means wide swings. Track quarterly trend, not monthly blip

**Metric 3c: Archetype Match Rate**
- **What counts:** % of profiled clients assigned to correct Travel DNA archetype (vs. reassigned later due to misclassification)
- **What doesn't:** Archetype refinements (e.g., "Wanderer" → "Wanderer-Luxury"), clients spanning multiple archetypes legitimately
- **Measurement:** Archetypes assigned at intake; audited at TP-1 (28 days pre-cruise) and post-delivery. % unchanged = match rate
- **Success targets:**
  - 🟢 **GREEN:** ≥90% archetype stable (1st assigned ≈ final)
  - 🟡 **YELLOW:** 80–89% archetype stable
  - 🔴 **RED:** <80% archetype stable (classification system not working, Navarro needs retraining)
- **Note:** If <80%, pause profile intake for 1 week; Navarro + Dembe joint AAR to recalibrate archetypes

---

### 4. DANI (A3 — Client Communications)

**Metric 4a: Client Response SLA**
- **What counts:** % of inquiries/proposals hitting speed targets (24h for inquiry, 48h for proposal, 7d for check-in)
- **What doesn't:** Messages Dani doesn't receive (routing failure), Commander-delayed approvals (WF-17 hold)
- **Measurement:** Sample all inquiries + proposals + check-ins for month. Measure "received → Dani output" elapsed time. % on SLA
- **Success targets:**
  - 🟢 **GREEN:** ≥90% on SLA across all three buckets
  - 🟡 **YELLOW:** 75–89% on SLA
  - 🔴 **RED:** <75% on SLA (workflow bottleneck, needs escalation)
- **Note:** WF-17 hold time is on Hale/Commander, not Dani. Measure from Dani inbox receipt only

**Metric 4b: Relationship Continuity**
- **What counts:** (1) Repeat client referral rate, (2) Client lifetime value trend
- **What doesn't:** One-time bookings unrelated to Dani touch
- **Measurement:** (1) # of referrals/repeat bookings from Dani clients ÷ total Dani clients (quarterly). (2) Average CLV new-client cohort vs. prior-cohort (year-over-year)
- **Success targets:**
  - 🟢 **GREEN:** >25% repeat/referral rate, CLV stable or growing quarter-over-quarter
  - 🟡 **YELLOW:** 15–25% repeat/referral, CLV flat or -5% trend
  - 🔴 **RED:** <15% repeat/referral, CLV -5% or worse (relationship rot)
- **Note:** Track quarterly, not monthly. Month-over-month swings are noise

**Metric 4c: Voice Consistency**
- **What counts:** % of Dani drafts passing Naia brand-pass without rework (first pass approved)
- **What doesn't:** Factual corrections, Commander tweaks post-Naia
- **Measurement:** Count Dani drafts reaching Naia; count approved first pass vs. returned for rework
- **Success targets:**
  - 🟢 **GREEN:** ≥80% approved first pass (Dani voice locked)
  - 🟡 **YELLOW:** 65–79% approved first pass
  - 🔴 **RED:** <65% approved first pass (voice drift, Naia rework overhead)
- **Note:** Same metric as Naia's "Iteration Rate" from opposite angle; should be inverse correlation

---

### 5. CASTILLO (A5 — Strategy/Growth)

**Metric 5a: Scenario Coverage**
- **What counts:** For each strategic decision/paper, how many options/scenarios presented? Quality of 3rd scenario (not just "status quo")
- **What doesn't:** Tactical options (e.g., which vendor), routine recommendations
- **Measurement:** Monthly decision audit. For each Castillo-authored strategy output, count scenarios. Grade 3rd scenario: "genuine third way" vs. "strawman"
- **Success targets:**
  - 🟢 **GREEN:** ≥2 scenarios per major decision, ≥60% of 3rd scenarios marked "genuine"
  - 🟡 **YELLOW:** 2 scenarios with <60% genuine 3rds, or 1 scenario per decision
  - 🔴 **RED:** Mostly single-option recommendations or strawman 3rds (narrow framing, insufficient exploration)
- **Note:** "Major decision" = those logged in hale_decisions.md or affecting >1 persona. <1 per month is acceptable baseline

**Metric 5b: Publication Velocity**
- **What counts:** Strategy papers, options memos, doctrine documents authored and published (vs. drafted but stuck)
- **What doesn't:** Tactical notes, routine updates
- **Measurement:** Count per quarter (not monthly; strategy work is lumpy). Also measure: median days from draft completion → publication
- **Success targets:**
  - 🟢 **GREEN:** ≥1 paper per quarter, <7 days median draft→publish
  - 🟡 **YELLOW:** 1 paper per quarter, 7–14 days median
  - 🔴 **RED:** <1 per quarter or >14 days median (ideation stalled, or blocked by approval)
- **Note:** If >14 days, flag blocker (Commander approval queue, Hale review, other). Not Castillo performance issue if external gate

**Metric 5c: Emotional Distance**
- **What counts:** Castillo explicitly flagging when strategy work is pulling away from client reality (e.g., "optimization plan ignores McLeod data")
- **What doesn't:** Routine mentions of client constraints
- **Measurement:** Count "emotional distance flag" events per month (self-reported by Castillo in memos/emails)
- **Success targets:**
  - 🟢 **GREEN:** ≥1 distance flag per quarter (Castillo aware of drift risk, self-correcting)
  - 🟡 **YELLOW:** <1 flag per quarter (Castillo not proactively checking)
  - 🔴 **RED:** 0 flags + later discovered disconnects (Castillo lost in abstraction, high risk)
- **Note:** This is a leading indicator of strategy-client misalignment. Absence of flags is concerning

---

### 6. STERLING (A7 — Process/Tech/Architecture)

**Metric 6a: Audit Completion Rate**
- **What counts:** Sunday Baldrige sweeps scheduled vs. completed, on-time %
- **What doesn't:** Ad-hoc audits, emergency diagnostics
- **Measurement:** Monthly count. Target: 4 Sundays/month, 4 audits/month. % on-time = completed Sunday before noon MT
- **Success targets:**
  - 🟢 **GREEN:** 100% completion rate, 100% on-time (4 of 4 Sundays executed)
  - 🟡 **YELLOW:** 75–99% completion, or 1–2 late (1–2 days)
  - 🔴 **RED:** <75% completion or >2 days late (audit cadence breaking down)
- **Note:** This is Sterling's operational discipline metric. Missing audits signals deeper availability/workload issue

**Metric 6b: Measurement Adoption**
- **What counts:** % of wing using Sterling's frameworks (e.g., this scorecard, metrics tracking, SLA dashboards, audit tools) + active participation
- **What doesn't:** Framework publication (activity); only adoption (usage)
- **Measurement:** Monthly poll: each persona reports "actively using [framework X]" (yes/no). Calculate % yes across 7 personas
- **Success targets:**
  - 🟢 **GREEN:** ≥85% adoption (6 of 7 personas actively using frameworks)
  - 🟡 **YELLOW:** 70–84% adoption
  - 🔴 **RED:** <70% adoption (framework resistance, training gap, or poor usability)
- **Note:** If adoption drops, Sterling audits reason. May require framework simplification or persona coaching

**Metric 6c: Lessons Implementation Rate**
- **What counts:** After-action reviews (AAR), training events, incident postmortems → captured lessons → converted to SOP change, code fix, CLAUDE.md edit, or new script within 30 days
- **What doesn't:** Lessons logged but not implemented; recommendations in drafts not acted on
- **Measurement:** Monthly count. For each lesson logged, track: 30-day implementation status (Implemented / In Progress / Blocked / Retracted). % Implemented = lessons_implementation_rate_pct
- **Success targets:**
  - 🟢 **GREEN:** ≥80% of lessons implemented within 30 days
  - 🟡 **YELLOW:** 60–79% within 30 days
  - 🔴 **RED:** <60% within 30 days (learning system non-functional; knowledge not durable)
- **Note:** This is SO-2026-05-16 WING EXERCISE PROTOCOL anti-theater rule. No lessons die in draft. Track in hale_decisions.md

---

### 7. HARLAN (A9 — Finance)

**Metric 7a: Commission Reconciliation Lag**
- **What counts:** Days between month-end and Harlan completing commission audit (all bookings, all sources, reconciled vs. dossier/TESS/sheet)
- **What doesn't:** Partial audits, preliminary reports
- **Measurement:** Calendar days from EOM → final audit report. Monthly target
- **Success targets:**
  - 🟢 **GREEN:** ≤5 days after EOM (complete by 5th of next month)
  - 🟡 **YELLOW:** 5–10 days after EOM (by 10th)
  - 🔴 **RED:** >10 days after EOM (finance reporting delayed, cash flow forecast stale)
- **Note:** If >10 days, audit Harlan workload. May need assistant or automation investment

**Metric 7b: ROI Accuracy**
- **What counts:** Cost-saving initiatives Harlan proposed → actual realized savings vs. predicted. Accuracy = realized ÷ predicted (target: 0.85–1.15 range)
- **What doesn't:** Initiatives not tracked to realization, strategic cost moves, overhead cuts without clear ROI
- **Measurement:** Quarterly audit. For each FY 2026 initiative, compare predicted (Harlan's proposal) vs. realized (post-implementation audit). Calculate accuracy ratio
- **Success targets:**
  - 🟢 **GREEN:** ≥70% of initiatives within 0.85–1.15 accuracy band (predictions solid)
  - 🟡 **YELLOW:** 50–69% within band (some overestimate, some underestimate)
  - 🔴 **RED:** <50% within band (Harlan's predictions unreliable; process failing)
- **Note:** Track quarterly, not monthly. First audit: 2026-06-30 (Q2 review)

**Metric 7c: Financial Clarity Index**
- **What counts:** For all active clients in dossier, is FPD (Final Payment Due) and current balance up-to-date and verified within 14 days?
- **What doesn't:** Historical records, inactive clients, estimated figures
- **Measurement:** Monthly sweep. Count clients with verified FPD + balance ≤14 days old ÷ total active clients
- **Success targets:**
  - 🟢 **GREEN:** ≥95% of active clients with current verified figures (1 client max stale)
  - 🟡 **YELLOW:** 85–94% current
  - 🔴 **RED:** <85% current (dossier stale, risk of surprise FPDs, cash flow uncertainty)
- **Note:** This is SO-PIPELINE-INTEGRITY-20260528 Rule 4 (Financial Hard-Source Rule). Failure triggers escalation

---

## MONTHLY REVIEW CADENCE & PROCESS

**When:** 1st of each month, 30 minutes, Hale presides. Sterling presents scorecard; Commander decides doctrine changes if any.

**What Sterling brings:**
1. One scorecard PDF (one page per persona, summary rollup)
2. Metric deltas (vs. prior month, vs. prior quarter)
3. One "red flag" persona (if any) with root cause hypothesis
4. Automation recommendations (how to reduce manual data entry next month)

**What Hale documents:**
- Decision point for each red/yellow metric (coaching plan, resource add, SOP change)
- One "win" highlight (persona exceeding targets)
- Quarterly trend snapshot (if Q-end review month)

**What Commander decides:**
- Framework adjustments (target thresholds too high/low?)
- Persona-specific actions (coaching, role shift, workload rebalance)
- Yes/no on Sterling's automation recommendations

**Output:** One row appended to `hale_decisions.md` under "Monthly Health Reviews" with:
- Date, 7-metric summary (G/Y/R), 1 red-flag persona, 1 action decided

---

## ROLLUP SCORING — WING ROBUSTNESS %

Sum all metrics (21 total: 7 personas × 3 metrics each). Assign points:
- 🟢 GREEN = 1 point
- 🟡 YELLOW = 0.5 points
- 🔴 RED = 0 points

**Wing Robustness % = (Total Points ÷ 21) × 100**

**Health threshold:**
- ≥90% = Full operational capacity
- 80–89% = Acceptable; monitor 1–2 yellows
- 70–79% = Caution; reds present, coaching/resources needed
- <70% = Crisis; escalate to Commander immediately

**Trend tracking:** Plot monthly Robustness % on a simple line chart. Target: upward trend, sustained >85%.

---

## HISTORICAL TRACKING

**Storage:**
- Raw monthly data: `OpsCenter/persona_health_monthly/` (YYYY-MM-scorecard.json)
- Summary trend: `hale_decisions.md` § "Monthly Health Reviews" (one row per month)
- Quarterly dashboard: `output/STERLING_METRICS_DASHBOARD.md` (regenerated Q-end)

**Rollback:** If a metric becomes obsolete (persona role changes, framework retired), mark with ~~strikethrough~~ in historical record. Do not delete. Track version in scorecard header

**Retention:** Keep full 12 months rolling. Archive older months to `archive/persona_health_historical/` annually.

---

## METRIC AUDIT CHECKLIST (Sterling Before Publishing)

- [ ] All 7 personas represented (no gaps)
- [ ] All 21 metrics have data (no blank cells)
- [ ] Thresholds reviewed against prior month (no goalpost moving without doc)
- [ ] Red-flag persona diagnosed with 2–3 sentence root cause
- [ ] Automation opportunity flagged (any manual data entry >15 min/month?)
- [ ] Scorecard version-stamped with date and Sterling's sign-off
- [ ] Prior month comparison visible (delta column added)
- [ ] Rollup % calculated (≥90% or action plan present)

---

## FRAMEWORK REFINEMENT (Annual Review)

Every January 1st, Sterling audits this template for:
- Metric creep (new metrics added; old ones still relevant?)
- Threshold calibration (targets still realistic given personnel/workload?)
- Adoption friction (any metrics Personas find too burdensome to track?)

Changes require Command approval. Document in template header with date + reason.

---

**Authority:** A7 Sterling | **Effective:** 2026-06-01 | **Review:** 2027-01-01 | **Template v1.0**

*Baldrige Operational Excellence Framework — Thunderbird Wing, Dreams2Memories Travel, LLC*
