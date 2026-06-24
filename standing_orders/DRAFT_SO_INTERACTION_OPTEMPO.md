# DRAFT SO — INTERACTION OPTEMPO PROTOCOL
## T2 Wing Exercise Staffing Package
*Authored: 2026-06-21 | Exercise: T2 | Domain Leads: Sterling, ELON, Dembe | COS: Hale*

---

### Sterling input

I have three hard questions before I'll sign off on this.

First — the BRIEF phase says "max 2 questions." That's good instinct but it's not measurable. Define it as: zero questions about data already in a primary source (dossier, TESS, state files, logs). Questions are permitted only for genuinely unknowable context — Commander's intent, relationship nuance, authorization scope. Failure B from the May AAR was precisely this: Hale asked the Commander for data she already had. The 2-question cap without that definition just caps the symptom.

Second — the CLOSE phase logs to `OpsCenter/issue_log.jsonl`. Who reads it? A log nobody reviews is theater. I want a weekly Sterling audit sweep tied to this file — same cadence as the Sunday Baldrige sweep. Without a reader and a metric, the log is entropy.

Third — ISSUE-XXXX format. Define the schema now, not in implementation. At minimum: issue_id, phase_durations, root_cause_confirmed (bool), Commander_redirects (count), questions_asked (count), outcome. That's the metric surface. If we can't measure Commander redirects over time, we can't prove the protocol is working.

*— Gauge Sterling, A7*

---

### ELON input

I'll be direct: this protocol has a latency problem baked in.

The INTAKE phase says Hale investigates and produces a hypothesis. Good. But "does NOT touch code or execute" during INTAKE is a constraint that will cause delays on issues where the fastest path to hypothesis confirmation IS a read-only probe — a log tail, a health check, a file stat. Read-only observation is not execution. Tighten the rule: INTAKE prohibits writes, commits, and service restarts. It does not prohibit read-only tool calls. Hypothesis quality goes up; latency goes down.

Bigger question: why is this manual? The majority of issues the Commander fires are recurrences — credential expiry, stale state, service down, draft not found. These have signatures. INTAKE should run a signature match against `OpsCenter/hale_incident_signatures.json` before Hale composes a hypothesis. Known signature → skip hypothesis prose, go straight to BRIEF with "matched pattern X, proposed action Y." First-principles: eliminate the reasoning step you've already done once.

This doesn't replace human judgment — it accelerates the 80% of cases that are pattern matches so Hale's reasoning bandwidth lands on the 20% that are novel.

*— ELON, A12*

---

### Dembe input

Operational realism check. Confidence: HIGH on the structural gaps; MEDIUM on the timeline estimates.

The protocol assumes a linear INTAKE → BRIEF → EXECUTE → CLOSE sequence. In the field, issues arrive in clusters — Commander fires three issues in one session, two of which are dependent. The protocol needs a queue discipline rule: how does Hale prioritize when multiple issues are open simultaneously? Without it, the protocol is correct for one issue and silent on the common case. Recommend: P0 issues interrupt current execution at next milestone checkpoint; P1 issues queue behind current phase completion; P2 issues batch to next session. This is the same priority logic already in `hale_state.json` — it should be explicit here.

Second gap: the CLOSE phase requires independent verification. Independent of what? Define the verification source. "Independent" means the verification does not rely on the same tool or log that executed the fix. A service restart verified by the same health check that reported it down is not independent — it's circular. Independent = different tool, different data source, or Commander confirmation.

Weakest link in the design: the "max 2 questions" rule collapses under time pressure. When the Commander is clearly in a hurry, Hale will compress questions to zero and guess. Build in an explicit "unknowable" tag so Hale can surface assumptions she made rather than questions she suppressed.

*— Wraith Dembe, A2*

---

### Synthesis

Three non-overlapping improvements, all bindable:

1. **Sterling's metric surface** — INTAKE question filter (zero questions about retrievable data) + `issue_log.jsonl` schema defined at SO level + weekly Sterling audit. Turns the log from entropy into a feedback instrument.

2. **ELON's signature match** — Add a pre-hypothesis pattern match step in INTAKE. Read-only observation is not restricted execution. Known patterns skip to BRIEF with matched signature. Novel issues proceed to hypothesis composition. Cuts latency on the 80%.

3. **Dembe's queue discipline + verification standard** — Multi-issue priority rule (P0 interrupts at milestone, P1 queues, P2 batches). Independent verification = different tool or different data source. Suppressed questions logged as explicit assumptions, not silently absorbed.

All three inputs are compatible and additive. No conflicts to resolve.

---

### DRAFT STANDING ORDER TEXT

**SO-INTERACTION-OPTEMPO-20260621**
*Interaction Optempo — Commander↔Hale Issue Resolution Protocol*
*Effective: 2026-06-21 | Author: Sterling (A7) | COS: Hale | Commander signature required*

**Purpose.** Establish a four-phase protocol governing every issue the Commander fires to Hale, from identification to verified close. Eliminates mid-execution redirects caused by Hale acting on incomplete understanding.

**Scope.** All non-client, non-financial issue resolution. Excludes WF-17 (client send), financial commits, and Wing Exercise classification (governed by separate SOs).

**Phase 1 — INTAKE.** Upon receiving an issue, Hale checks all primary sources (dossier, TESS, logs, state files, `hale_incident_signatures.json`) before forming a hypothesis. Read-only tool calls are permitted; writes, commits, and service restarts are not. If a known signature matches, Hale proceeds directly to BRIEF with the matched pattern. Novel issues proceed to hypothesis composition. No questions are asked during INTAKE.

**Phase 2 — BRIEF.** Hale surfaces findings in T&Q format (Talking Paper for single-domain; Bullet Background Paper for multi-domain). Required elements: (a) what was found, (b) root cause hypothesis, (c) proposed action, (d) explicit assumptions (items Hale could not confirm), (e) at most 2 questions — only for genuinely unknowable context not present in any primary source. Commander clears with "execute," redirects, or answers questions. Redirect resets to Phase 1 for the delta only.

**Phase 3 — EXECUTE.** OODA-visible execution. Hale reports at each milestone. Holds only at three Commander gates: client send, financial commitment, Strategic (>90d / >$5K). Multiple concurrent issues follow queue discipline: P0 interrupts at next milestone; P1 queues behind current phase; P2 batches to next session.

**Phase 4 — CLOSE.** Hale verifies the fix using a different tool or data source than the one that reported the failure (independent verification). Issues a short AAR logged to `OpsCenter/issue_log.jsonl` with schema: `{issue_id, phase_durations_sec, root_cause_confirmed, commander_redirects, questions_asked, assumptions_logged, outcome}`. Sterling audits this file weekly in the Sunday Baldrige sweep. Target metrics: commander_redirects trending to zero; questions_asked zero for retrievable data.

**Metric.** Weekly Sterling audit reports: redirect count, question-about-known-data count, independent-verification compliance rate. Red threshold: >2 redirects/week for same issue class.

*— Authorized for Commander review and signature*
*SO number: SO-INTERACTION-OPTEMPO-20260621*
