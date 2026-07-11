# STANDING ORDER — P-D-T-A-C Proposal/Task Workflow
## "NO MORE BLACK HOLES" — Full Visibility Until Completion
**Effective:** 2026-07-11  
**Owner:** Commander (John Loucks)  
**Status:** ACTIVE

---

## PURPOSE
Eliminate proposals and tasks disappearing into limbo. Every proposal/task tracked through 5 stages with full visibility until certified complete.

---

## THE FIVE STAGES

| Stage | Owner | Action | Visibility |
|-------|-------|--------|---|
| **P** | Staff | **PROPOSE** — staff submits proposal/idea to Strategic Inbox | Pending Commander decision |
| **D** | Commander | **DECIDE** — Commander approves/modifies/rejects; decision logged | Moved to Operational; assigned SLA/deadline |
| **T** | Hale (COS) | **TASK** — Hale defines front-end conditions: success criteria, deadline, dependencies, assigned staff member | Task card created; assigned to staff; Watch section |
| **A** | Assigned Staff | **ACCOMPLISH** — staff executes work, reports status, escalates blockers | Watch section shows progress; P1 blockers → D gate |
| **C** | Silver + Commander | **CERTIFY** — Silver assesses back-end; Commander signs off or requests rework | Completion verified, logged to audit trail, marked DONE |

---

## KEY RULES

### Response Times
- **P→D (Proposal→Decision):** No proposal sits unanswered >48h
- **D→T (Decision→Task):** Task assigned and conditions defined same business day
- **T→A (Task→Accomplishing):** Staff begins work within 24h of task assignment
- **A→C (Accomplish→Certify):** Completion review within 5 business days

### Blocking & Escalation
- **Staff blocked** (can't proceed, waiting for info/approval) → escalates to **D gate** immediately
- **Blocker at D gate** → Commander makes decision or defers >5d → Red alert
- **Overdue task** (past SLA deadline) → Daily reminder to staff + CC Commander

### Certification Rules
- **C (Certify)** is the ONLY exit from the workflow
- If rework required → restart at T stage (retain same task ID for audit trail)
- Commander approval is final gate — no task is "done" until Commander certifies

### Audit Trail
- Every stage transition logged with timestamp, owner, and status change
- Voice notes encouraged at decision points (D) and blockers (A)
- hale_decisions.md captures all P-D-T-A-C lifecycle entries

---

## STATUS PILLS (TCD Implementation)

Each task displays its current stage:
- 🔵 **Proposed** — awaiting Commander decision
- 🟢 **Decided** — conditions being defined
- 🟡 **Tasked** — assigned, awaiting staff to begin
- 🟠 **Accomplishing** — in progress (staff working)
- ✅ **Certified** — complete, verified by Silver + Commander

**Overdue indicators:**
- Tasks past SLA → Red pill
- Proposals pending >48h → Red pill
- Blockers pending >24h → Red pill

---

## TCD FILTERING & VIEWS

Commander can filter by stage:
- "Show all **Proposed** items" → decisions needed
- "Show all **Accomplishing** items" → Watch section (in-flight work)
- "Show all **Blocked** items" → escalations requiring decision
- "Show **Overdue** items" → timeline violations, priority escalation

---

## EXAMPLE WORKFLOW

**Day 1 (Mon):**
- A2 Dembe proposes new Regent pricing tier analysis → P stage in Strategic Inbox

**Day 1 EOD:**
- Commander reviews, approves with modification ("include Silversea comparison") → D stage
- Hale defines task: deadline Fri 5pm, success = pricing matrix + competitive analysis, assigned to Sterling

**Day 2 (Tue):**
- Sterling marks task "Accomplishing" in TCD, begins work

**Day 4 (Thu):**
- Sterling hits blocker: Silversea portal session expired
- Escalates to D gate → Commander approves re-scrape via CloakBrowser, restores session access
- Sterling resumes work

**Day 5 (Fri):**
- Sterling completes pricing matrix, posts to task comments + attaches document

**Day 5 EOD:**
- Silver reviews back-end work quality, flags one data discrepancy
- Hale routes back to Sterling for correction (rework, restart at T stage, same task ID)

**Day 6 (Sat) (if needed):**
- Sterling fixes, resubmits
- Commander certifies complete → C stage
- Task marked DONE, logged to audit trail

---

## ROLES & AUTHORITY

| Role | P-D-T-A-C Responsibility |
|------|---|
| **Commander (Yoda)** | P (receive), D (all decisions), A (escalation gate), C (sign-off) |
| **Hale (COS)** | D (parsing), T (task definition + assignment), A (progress tracking), C (coordination) |
| **Silver (A7)** | T (consult on conditions), A (status visibility), C (back-end assessment) |
| **Assigned Staff** | A (execution + status updates), escalate blockers to D gate |
| **Dani (A3)** | P (client proposals → Strategic), A (client-facing status) |
| **Dembe (A2)** | P (research proposals), A (findings + blockers) |

---

## EXCEPTIONS & DEVIATIONS

**No exceptions to P-D-T-A-C.** All proposals and tasking flow through this workflow.

**Urgent items (P0, <6h deadline):**
- Compress P→D→T into single async round (Commander decides + Hale tasks simultaneously)
- Still require A→C certification before completion

---

## REVISION HISTORY
| Date | Change | Owner |
|------|--------|-------|
| 2026-07-11 | Standing Order established | Commander |

---

**Document Authority:** This Standing Order supersedes all prior ad-hoc proposal/tasking processes.  
**Approved by:** John Loucks, Commander  
**Effective immediately.**
