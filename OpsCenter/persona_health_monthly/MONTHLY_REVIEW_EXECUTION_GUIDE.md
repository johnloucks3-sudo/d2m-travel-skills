# Persona Health Scorecard — Monthly Review Execution Guide
**Authority:** A7 Sterling | **Effective:** 2026-06-01 | **Last Updated:** 2026-06-18

---

## PURPOSE

This guide operationalizes the Persona Health Scorecard template (`docs/PERSONA_HEALTH_SCORECARD_TEMPLATE.md`) by providing Sterling with a repeatable data-collection checklist and execution workflow for each monthly review.

**Key principle:** Every metric must have real data. If data is unavailable, that is a signal—either a process is not logging correctly, or the metric definition needs refinement.

---

## MONTHLY REVIEW CADENCE

- **When:** 1st of each month, 30 minutes (Sunday preferred)
- **Who:** Sterling (A7) conducts; Hale documents; Commander decides
- **Output:** One scorecard PDF + summary row in `hale_decisions.md`

---

## DATA COLLECTION CHECKLIST — 3 Weeks Prior

**Week -3 (8th–14th of prior month):** Sterling begins data gathering

### HALE (Ms. Victoria Hale, SES-6)

**Metric 1a: Decision Velocity**
- [ ] Source: `hale_decisions.md` last 4 weeks
- [ ] Count entries classified as "routing decision," "autonomy call," "staff dispute," "priority reset"
- [ ] Exclude: "opinion statement," "advisory note," "question to Commander"
- [ ] Calculate: total decisions ÷ 4 weeks = decisions/week average
- [ ] **Data entry:** Spreadsheet row with week-by-week count + monthly average

**Metric 1b: Staff Capability Lift**
- [ ] Source: `hale_decisions.md`, email threads, Telegram D2MC2C log
- [ ] Count: "new skills deployed," "training hours," "subordinate role shift," "documented lesson shared"
- [ ] Exclude: tactical task completion, routine assignments
- [ ] **Data entry:** List each capability lift event + date + brief description

**Metric 1c: Autonomy Band**
- [ ] Source: Last 4 weeks of activity (Telegram, email, hale_decisions.md)
- [ ] Sample 20 Hale decisions/actions. Classify each as:
  - **Execute-Report:** Hale acts, then tells Commander
  - **Request-Permission:** Hale asks first, waits for approval
- [ ] Calculate: % Execute-Report ÷ 20 samples
- [ ] **Data entry:** Count of Execute-Report, count of Request-Permission, % band

**Metric 1d: WF-17 Quality Gate**
- [ ] Source: WF-17 activity log (drafts held, reasons, dates)
- [ ] Count: total drafts held at WF-17 this month
- [ ] Classify each hold by reason: "creative," "facts," "process," "tone," "sig block"
- [ ] Count: total WF-17 inputs (held + passed)
- [ ] Calculate: (holds ÷ total inputs) × 100 = hold rate %
- [ ] **Data entry:** Total hold count, hold rate %, reason breakdown

---

### NAIA SOLBERG-VEGA (EXEC — Brand/Voice)

**Metric 2a: Brand-Pass Turnaround**
- [ ] Source: Email thread timestamps (Dani → Naia inbox → Naia response)
- [ ] Measure: Wall-clock hours from Dani submission to Naia sign-off
- [ ] Separate: "first pass" (approved as-is) vs. "rework pass" (returned + resubmitted + approved)
- [ ] Calculate: Median hours for each category (4-week rolling window)
- [ ] **Data entry:** Median hours (first), Median hours (rework), sample size

**Metric 2b: Iteration Rate**
- [ ] Source: WF-17 draft history (Dani→Naia→back to Dani or approved)
- [ ] Count: For each Dani draft in month, how many pass cycles before Naia sign-off?
- [ ] Calculate: Total pass cycles ÷ total drafts = iterations/draft
- [ ] **Data entry:** Total drafts reviewed, total pass cycles, iterations/draft average

**Metric 2c: Client Voice Consistency**
- [ ] Source: Client post-send replies, Dani feedback notes, unsolicited messages about tone
- [ ] Classify each feedback as: "positive" (warm, feels right, compliment) or "concern" (too formal, too casual, off-brand)
- [ ] Calculate: Positive ÷ Concern ratio
- [ ] Compare to prior month: ratio stable, trending up, or trending down?
- [ ] **Data entry:** Positive count, concern count, ratio, trend vs. prior month

---

### NAVARRO (A1 — Client Intake/Profile)

**Metric 3a: Profile Accuracy**
- [ ] Source: Post-delivery client feedback (30 days after cruise)
- [ ] Survey/unsolicited feedback: "dossier captures who we are" (yes/no/neutral)
- [ ] Calculate: # yes + neutral ÷ total clients surveyed = % feel understood
- [ ] **Data entry:** Clients surveyed, % who feel understood, any pattern notes

**Metric 3b: Confidence Calibration**
- [ ] Source: Dossier confidence markings vs. later experience rework
- [ ] Compare: HIGH-confidence profiles → failure rate (post-delivery rework) vs. MEDIUM-confidence → failure rate
- [ ] Failure = "doesn't match" feedback or Reyes experience rework required
- [ ] Calculate: HIGH failure rate ÷ MEDIUM failure rate = ratio
- [ ] **Data entry:** HIGH-conf profiles, HIGH failures, MEDIUM-conf profiles, MEDIUM failures, ratio

**Metric 3c: Archetype Match Rate**
- [ ] Source: Dossier archetype assignment at intake, vs. archetype at TP-1, vs. archetype at post-delivery
- [ ] Count: Archetypes unchanged = match ÷ total profiled clients = % match
- [ ] **Data entry:** Total profiled clients, unchanged count, % match rate

---

### DANI (A3 — Client Communications)

**Metric 4a: Client Response SLA**
- [ ] Source: Email timestamps (client inquiry → Dani response, proposal request → Dani draft, check-in send → Dani response)
- [ ] Measure: Elapsed time from receipt to output
- [ ] Separate buckets: inquiries (24h target), proposals (48h target), check-ins (7d target)
- [ ] Count: # on SLA ÷ total in month = % on SLA per bucket
- [ ] Calculate: Average % across three buckets
- [ ] **Note:** Exclude WF-17 hold time (Hale/Commander responsibility)
- [ ] **Data entry:** Inquiries (%), proposals (%), check-ins (%), overall %

**Metric 4b: Relationship Continuity**
- [ ] Source: Client history, referral tracking, CLV sheet
- [ ] Count: # of repeat bookings or referrals from Dani clients ÷ total Dani clients (quarterly)
- [ ] Compare: This quarter's CLV (avg $ per client) vs. prior quarter
- [ ] Calculate: Repeat/referral rate %, CLV trend (% change)
- [ ] **Data entry:** Total Dani clients, repeat/referral count, rate %, CLV $/client, trend %
- [ ] **Note:** Track quarterly; monthly data point is informational only

**Metric 4c: Voice Consistency**
- [ ] Source: WF-17 Dani drafts → Naia review (same as Naia's Iteration Rate metric)
- [ ] Count: Dani drafts reaching Naia, count approved first pass
- [ ] Calculate: # approved first pass ÷ total = % approved first pass
- [ ] **Data entry:** Total Dani drafts to Naia, approved first pass count, %

---

### CASTILLO (A5 — Strategy/Growth)

**Metric 5a: Scenario Coverage**
- [ ] Source: Strategy papers, options memos, doctrine documents authored (hale_decisions.md, Google Drive)
- [ ] For each major decision: count scenarios presented
- [ ] Grade 3rd scenario: "genuine third way" (Y/N) vs. "strawman"
- [ ] Calculate: Avg scenarios/decision, % of 3rd scenarios marked "genuine"
- [ ] **Data entry:** Total decisions audited, avg scenarios/decision, % genuine 3rds
- [ ] **Note:** "Major decision" = in hale_decisions.md or affects >1 persona

**Metric 5b: Publication Velocity**
- [ ] Source: Strategy papers, options memos, doctrine docs (quarterly count)
- [ ] Count: Papers authored and published ÷ quarter
- [ ] Measure: Days from draft complete → published
- [ ] Calculate: Median days draft→publish
- [ ] **Data entry:** Papers published (quarterly), median days draft→publish
- [ ] **Note:** Track quarterly; use month-to-date for monthly snapshot

**Metric 5c: Emotional Distance**
- [ ] Source: Castillo's own flagging (in memos/emails: "client reality vs. strategy drift")
- [ ] Count: "Emotional distance flag" events (Castillo explicitly noting misalignment)
- [ ] **Data entry:** Count of distance flags, examples/month
- [ ] **Note:** Absence of flags is concerning (leading indicator of drift)

---

### STERLING (A7 — Process/Tech/Architecture)

**Metric 6a: Audit Completion Rate**
- [ ] Source: Sterling's own schedule (Baldrige Sunday sweeps)
- [ ] Count: # of Sundays in month (target: 4)
- [ ] Count: # of audits completed on-time (Sunday before noon MT)
- [ ] Calculate: Completed ÷ scheduled = % completion, on-time count
- [ ] **Data entry:** Sundays in month, audits completed, on-time count, %

**Metric 6b: Measurement Adoption**
- [ ] Source: Monthly poll of all 7 personas
- [ ] Ask each: "Actively using [framework X]?" (yes/no) — where framework = this scorecard, SLA dashboards, audit tools, etc.
- [ ] Calculate: # yes ÷ 7 = adoption %
- [ ] **Data entry:** Poll results (yes/no per persona), adoption %

**Metric 6c: Lessons Implementation Rate**
- [ ] Source: `hale_decisions.md` "Lessons" section or after-action reviews
- [ ] For each lesson logged in month: track 30-day status (Implemented / In Progress / Blocked / Retracted)
- [ ] Calculate: # Implemented ÷ total logged = lessons_implementation_rate_pct
- [ ] **Data entry:** Total lessons logged, implemented count, in progress, blocked, %

---

### HARLAN (A9 — Finance)

**Metric 7a: Commission Reconciliation Lag**
- [ ] Source: Harlan's commission audit report (end-of-month)
- [ ] Measure: Calendar days from EOM → audit complete
- [ ] Target: ≤5 days after EOM (by 5th of next month)
- [ ] **Data entry:** Days after EOM when audit completed

**Metric 7b: ROI Accuracy**
- [ ] Source: FY 2026 cost-saving initiatives (quarterly audit)
- [ ] For each initiative: compare predicted savings (Harlan's proposal) vs. realized (post-implementation)
- [ ] Calculate: Realized ÷ predicted = accuracy ratio (target: 0.85–1.15)
- [ ] % within range = metric
- [ ] **Data entry:** Initiatives audited, % within 0.85–1.15 band
- [ ] **Note:** Track quarterly; first audit due 2026-06-30 (Q2)

**Metric 7c: Financial Clarity Index**
- [ ] Source: Active client dossiers (check FPD + balance currency)
- [ ] For each active client: is FPD and current balance verified ≤14 days old?
- [ ] Calculate: # current ÷ total active = clarity %
- [ ] **Data entry:** Total active clients, current count, clarity %

---

## SCORECARD COMPLETION — Week -1 (25th–30th of prior month)

**Sterling creates scorecard PDF:**
1. One page per persona (7 pages total)
2. Metric summary with status (🟢 / 🟡 / 🔴) + data
3. Metric deltas (vs. prior month, vs. prior quarter if available)
4. Red-flag persona (if any) with root cause hypothesis
5. Rollup scoring: Wing Robustness % = (Total Points ÷ 21) × 100
   - 🟢 GREEN = 1 point, 🟡 YELLOW = 0.5, 🔴 RED = 0

**Output files:**
- `OpsCenter/persona_health_monthly/2026-06-scorecard.json` (raw data)
- `output/STERLING_METRICS_DASHBOARD.md` (summary for Commander briefing)

---

## REVIEW MEETING — 1st of Month, 30 Minutes

**Attendees:** Sterling (presenter), Hale (minutes), Commander (decision-maker)

**Agenda:**
1. **Scorecard Overview** (5 min): Wing Robustness %, rollup status, any reds or yellows
2. **Red-Flag Persona Deep Dive** (10 min): Root cause hypothesis, 2–3 sentence explanation
3. **Metric Deltas** (5 min): Trending up/down? Any surprises?
4. **Automation Opportunities** (5 min): How to reduce manual data entry next month?
5. **Decisions** (5 min):
   - Coaching plan for reds?
   - Resource adds?
   - Framework adjustments?
   - Approval for automation recommendations?

**Hale documents:**
- Outcome in `hale_decisions.md` under "Monthly Health Reviews" section:
  - Date, 7-metric summary (G/Y/R), red-flag persona, action decided

---

## DATA SOURCES — Quick Reference

| Persona | Metric 1 | Metric 2 | Metric 3 |
|---------|----------|----------|----------|
| **Hale** | hale_decisions.md | Telegram + email | Telegram + hale_decisions.md sample | WF-17 activity log |
| **Naia** | Email timestamps (Dani→Naia) | WF-17 draft history | Client post-send replies | (same as above) |
| **Navarro** | Client survey (30d post-cruise) | Dossier markings + rework log | Dossier archetype field | (tracked at intake) |
| **Dani** | Email timestamps (client→Dani→output) | Client history + CLV sheet | Repeat booking count | WF-17 Dani drafts + Naia review |
| **Castillo** | hale_decisions.md + Drive | Strategy papers published | Days draft→publish | Castillo's own flagging |
| **Sterling** | Sunday Baldrige audit schedule | Persona poll (all 7) | hale_decisions.md "Lessons" section | (audit tracking) |
| **Harlan** | Commission audit report (EOM) | FY 2026 initiatives (quarterly) | Dossier FPD + balance scan | (monthly) |

---

## FAILURE MODES & RECOVERY

### Scenario: Data is Unavailable for a Metric

**Action:**
1. Flag the metric as "DATA UNAVAILABLE" in the scorecard
2. Root-cause: Is the process not logging? Is the person not doing the activity?
3. If process gap: Sterling files a fix recommendation (e.g., "add WF-17 hold reason logging")
4. If activity gap: That's the actual data point—metric goes RED/YELLOW
5. Do NOT estimate or substitute data. Missing data is a valid signal.

### Scenario: Metric Definition is Unclear or Unworkable

**Action:**
1. Sterling flags in scorecard: "METRIC UNCLEAR — requires refinement"
2. Propose concrete fix (e.g., "change threshold," "redefine 'major decision'")
3. Commander approves change at next month's review
4. Scorecard template updated + version bumped (`v1.0` → `v1.1`)

### Scenario: June Review Missed (2026-06-18 — Still No June Scorecard)

**Action (Retroactive):**
1. Sterling pulls June data (hale_decisions.md 6/1–6/30, emails, etc.)
2. Scorecard dated "June 2026 (Conducted 2026-06-18)" in header
3. Note deviation: "Review conducted 18 days late due to [reason]"
4. July review (2026-07-01) happens on schedule
5. Hale documents both June and July in hale_decisions.md

---

## TEMPLATE JSON — Monthly Scorecard Raw Data

```json
{
  "month": "2026-06",
  "review_date": "2026-06-01",
  "conducted_date": "2026-06-01",
  "sterling_sign_off": "A7 Sterling",
  "hale_documented": true,
  "personas": {
    "hale": {
      "decision_velocity_decisions_per_week": 9.5,
      "decision_velocity_status": "green",
      "staff_capability_lift_new_capabilities": 1,
      "staff_capability_lift_status": "green",
      "autonomy_band_pct": 92,
      "autonomy_band_status": "green",
      "wf17_quality_gate_hold_rate_pct": 3.5,
      "wf17_quality_gate_status": "green"
    },
    "naia": {
      "brand_pass_turnaround_first_pass_hours": 3.2,
      "brand_pass_turnaround_rework_hours": 1.8,
      "brand_pass_turnaround_status": "green",
      "iteration_rate_iterations_per_draft": 1.1,
      "iteration_rate_status": "green",
      "voice_consistency_positive_concern_ratio": 3.5,
      "voice_consistency_status": "green"
    },
    "navarro": {
      "profile_accuracy_feel_understood_pct": 88,
      "profile_accuracy_status": "green",
      "confidence_calibration_high_to_medium_ratio": 1.0,
      "confidence_calibration_status": "green",
      "archetype_match_rate_pct": 92,
      "archetype_match_status": "green"
    },
    "dani": {
      "client_response_sla_pct": 89,
      "client_response_sla_status": "green",
      "relationship_continuity_repeat_referral_pct": 22,
      "relationship_continuity_status": "yellow",
      "voice_consistency_first_pass_approval_pct": 78,
      "voice_consistency_status": "green"
    },
    "castillo": {
      "scenario_coverage_avg_scenarios_per_decision": 2.1,
      "scenario_coverage_genuine_3rd_pct": 65,
      "scenario_coverage_status": "green",
      "publication_velocity_papers_per_quarter": 1,
      "publication_velocity_median_days_draft_to_publish": 6,
      "publication_velocity_status": "green",
      "emotional_distance_flags_per_month": 1,
      "emotional_distance_status": "green"
    },
    "sterling": {
      "audit_completion_rate_pct": 100,
      "audit_completion_status": "green",
      "measurement_adoption_pct": 86,
      "measurement_adoption_status": "green",
      "lessons_implementation_rate_pct": 82,
      "lessons_implementation_status": "green"
    },
    "harlan": {
      "commission_reconciliation_lag_days": 4,
      "commission_reconciliation_status": "green",
      "roi_accuracy_pct_in_band": null,
      "roi_accuracy_status": "not_applicable",
      "financial_clarity_index_pct": 96,
      "financial_clarity_status": "green"
    }
  },
  "rollup": {
    "total_points": 20.5,
    "wing_robustness_pct": 97.6,
    "health_threshold": "full_operational_capacity"
  },
  "red_flag_persona": null,
  "decisions_logged": "None; all metrics green/acceptable"
}
```

---

## NEXT STEPS

1. **June 2026 Data Collection (Retroactive):** Sterling pulls June data from logs + messaging
2. **June Scorecard Creation:** Sterling assembles scorecard (target: 2026-06-20)
3. **Hale Documentation:** One-line entry in hale_decisions.md § "Monthly Health Reviews"
4. **July 1, 2026:** Full review meeting with Commander (on schedule)
5. **Ongoing:** Monthly cadence every 1st of month

---

**Authority:** A7 Sterling | **Owner:** Hale COS | **Maintained in:** `/home/john/Thunderbird/OpsCenter/persona_health_monthly/`
