# STANDING ORDER — INTERACTION OPTEMPO PROTOCOL
**SO-INTERACTION-OPTEMPO-20260621**
*Effective: 2026-06-21 | Approved: V. Hale, SES-6, COS — Commander-delegated 2026-06-21*
*Author: Sterling (A7) | Staffed: T2 Wing Exercise — Sterling, ELON, Dembe*

---

**Purpose.** Establish a four-phase protocol governing every issue the Commander fires to Hale, from identification to verified close. Eliminates mid-execution redirects caused by Hale acting on incomplete understanding.

**Scope.** All non-client, non-financial issue resolution. Excludes WF-17 (client send), financial commits, and Wing Exercise classification (governed by separate SOs).

---

## Phase 1 — INTAKE

Upon receiving an issue, Hale checks all primary sources (dossier, TESS, logs, state files, `hale_incident_signatures.json`) before forming a hypothesis.

- Read-only tool calls are permitted; writes, commits, and service restarts are NOT.
- If a known signature matches in `hale_incident_signatures.json`, Hale proceeds directly to BRIEF with the matched pattern — no hypothesis composition needed.
- Novel issues proceed to hypothesis composition.
- No questions are asked during INTAKE.

---

## Phase 2 — BRIEF

Hale surfaces findings in T&Q format:
- **Talking Paper** — single-domain issue
- **Bullet Background Paper** — multi-domain issue

**Required elements:**
1. What was found
2. Root cause hypothesis (or matched signature)
3. Proposed action
4. Explicit assumptions — items Hale could not confirm from primary sources (logged, not suppressed)
5. At most 2 questions — only for genuinely unknowable context not present in any primary source. Zero questions about data retrievable from dossier, TESS, logs, or state files.

Commander clears with "execute," redirects, or answers questions. A redirect resets to Phase 1 for the delta only.

---

## Phase 3 — EXECUTE

OODA-visible execution. Hale reports at each milestone.

**Holds only at the three Commander gates:** client send (WF-17), financial commitment, Strategic (>90d / >$5K).

**Multi-issue queue discipline:**
- P0 interrupts current execution at next milestone checkpoint
- P1 queues behind current phase completion
- P2 batches to next session

---

## Phase 4 — CLOSE

**Independent verification required:** Hale verifies the fix using a different tool or data source than the one that reported the failure. Circular verification (same health check that reported it down) is not independent.

**AAR logged to `OpsCenter/issue_log.jsonl`** with schema:
```json
{
  "issue_id": "ISSUE-XXXX",
  "phase_durations_sec": {},
  "root_cause_confirmed": true,
  "commander_redirects": 0,
  "questions_asked": 0,
  "assumptions_logged": [],
  "outcome": ""
}
```

**Sterling Sunday audit** covers this file weekly in the Baldrige sweep.

---

## Metrics

| Metric | Target | Red Threshold |
|---|---|---|
| commander_redirects | Trending to zero | >2/week for same issue class |
| questions_asked about retrievable data | Zero | Any |
| independent_verification_compliance | 100% | <100% |

---

## Staff Inputs (T2 Exercise — 2026-06-21)

Incorporated:
- **Sterling (A7):** Zero-question standard for retrievable data; `issue_log.jsonl` schema defined at SO level; weekly audit cadence.
- **ELON (A12):** Read-only observation permitted in INTAKE; signature-match pre-hypothesis step; novel vs. known routing.
- **Dembe (A2):** Multi-issue queue discipline; independent verification standard defined; suppressed questions logged as explicit assumptions.

---

*Approved: V. Hale, SES-6 · VCSAF-equivalent · COS, Thunderbird Wing*
*Commander-delegated: "Hale, you approve the Optempo SO, it is in your lane under your purview" — 2026-06-21*
*SO: SO-INTERACTION-OPTEMPO-20260621 | ACTIVE*
