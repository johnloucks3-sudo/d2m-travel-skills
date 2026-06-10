---
SO Number: SO-2026-06-09-FPD-ENFORCEMENT
Title: Final Payment Due Enforcement Escalation Protocol
Authority: Commander John "Yoda" Loucks
Effective Date: 2026-06-09
Status: PENDING COMMANDER SIGNATURE
---

# STANDING ORDER: FINAL PAYMENT DUE (FPD) ENFORCEMENT ESCALATION PROTOCOL

**Dreams2Memories Travel, LLC — Thunderbird Wing**

---

## EXECUTIVE SUMMARY

This Standing Order establishes a mandatory escalation protocol for Final Payments Due (FPD) that exceed 30 days overdue. The objective is to close the doctrine gap between detection (which exists) and collection authority (which did not). Effective immediately upon Commander signature, any FPD overdue 30+ days triggers a Commander-initiated client contact within 48 hours of detection.

**Doctrine Problem Addressed (per 2026-06-05 Weekly Report):**
- Detection system (A3 FPD Sentinel) flags overdue FPDs reliably
- Flagged items surface in morning brief and Hale queue
- Collection action then stops: no defined escalation path to enforcement
- Result: structural non-collection across active roster (5 clients, 65-132 days overdue as of Jun 5)

**Authority Assignment:** Commander holds sole financial collection authority. This SO operationalizes that authority.

---

## 1. SCOPE & APPLICABILITY

### Who This Applies To
- All Dreams2Memories Travel, LLC clients with confirmed cruise/voyage bookings
- All FPDs tied to cruise line final payment deadlines (as recorded in dossier + TESS)
- Both individual clients and group bookings

### What This Does NOT Cover
- Deposits or partial payments
- Payment plan arrangements (covered by separate Standing Order or Commander-signed agreement)
- Disputed charges or service-recovery scenarios (escalate to Commander with context, not auto-enforcement)

---

## 2. DETECTION & TRIGGERING

### A3 FPD Sentinel (Automatic)

The A3 FPD Sentinel state machine runs daily at 06:00 MT:
- Scans all active TESS bookings and dossier records
- Flags any FPD due date that has passed
- Feeds flagged items to Hale with status: OVERDUE (# days)
- Does NOT re-flag same item if already flagged in prior cycle (state machine prevents spam)

**Output Location:** `hale_brief.md` § Financial Pulse, FPD column (🔴 OVERDUE marker)

### Escalation Trigger: 30+ Days Overdue

When an FPD remains overdue for 30+ days:
1. Hale flags it in morning brief with escalation note: "🔴 30+ day escalation trigger"
2. Hale routes task to Commander queue with mission board entry (auto-created): "MISSION: [Client] FPD Collection — [# days] overdue"
3. Hale sends summary to Commander via Telegram (D2MC2C channel): "🔴 FPD ESCALATION: [Client] | [Voyage] | Overdue [# days] | FPD amount: $[X] | Commission at risk: $[Y]"

**No further approval gates. The 30-day threshold automatically triggers Commander action queue.**

---

## 3. COMMANDER ENFORCEMENT ACTION

### Required Action: Client Contact

**When:** Within 48 hours of escalation trigger (or next business day if weekend/holiday)

**What:** Commander initiates direct client contact via phone or email (Commander's choice, per relationship):

1. **Call script** (preferred for $10K+ commissions or relationship-critical clients):
   - Confirm client received final payment reminder (from dossier TP sequence)
   - Ask about payment status and any blockers
   - If payment sent but not yet credited to cruise line account, get proof (confirmation email)
   - If payment has not been sent, clarify deadline and arrange immediate payment (offer payment link or bank instructions)
   - Document conversation: date, time, outcome, next action

2. **Email script** (acceptable for lower-value or less-acute situations):
   - Reference voyage and final payment deadline
   - State current status: "[# days] overdue as of [date]"
   - Request payment confirmation by [specific date]
   - Provide payment options: online portal, wire, ACH, check
   - Include cruise line contact for any booking issues
   - Set 3-day response deadline

### Documentation Requirement

Commander action is logged immediately in:
- **hale_decisions.md:** Entry tagged `FPD-COLLECTION-ACTION` with date, client, outcome, next steps
- **Mission board:** Status updated to `active_collection` with context note
- **Dossier TP sequence:** Add timestamped collection action entry (Reyes/A8 owns dossier updates)

Example hale_decisions.md entry:
```
### FPD Collection Action — [Client Name]
**Date:** [Date] | **Authority:** Commander (SO-2026-06-09)
**Voyage:** [Voyage/Dates]
**FPD Overdue:** [# days] | **Amount:** $[X]
**Action taken:** Phone call to [name] / Email to [address]
**Outcome:** Payment received / Payment in process (ETA [date]) / Blocker: [description]
**Next step:** [Confirm receipt / Follow-up call [date] / Escalate to legal]
**Commission at risk:** $[Y] — closing this action recovers [X]% of pipeline
```

---

## 4. ESCALATION LADDER (If Initial Contact Fails)

### Tier 1 — Initial Contact (48-hour rule, Section 3)
Status: In progress, awaiting client response

### Tier 2 — Follow-Up Contact (5 days after Tier 1)
If Tier 1 contact yields no payment and no credible timeline:
- Second contact (opposite medium from Tier 1: if called, email; if emailed, call)
- Escalate language: "We need to resolve this before [voyage date]."
- State financial impact if necessary: "Our commission is contingent on final payment by the cruise line deadline."

### Tier 3 — Payment Plan or Cancellation Discussion (10 days after Tier 1)
If Tier 2 yields no resolution and voyage is <14 days away:
- Offer structured payment plan if client has cash-flow issue (Commander decision only)
- OR clarify cancellation consequences and next steps with cruise line
- Document both options in hale_decisions.md with Commander authorization

### Tier 4 — Cruise Line Notification (If FPD Due Date Passes)
If payment has not been collected by cruise line FPD deadline:
- Commander notifies cruise line of non-collection and coordinates booking status (non-cancellation, as appropriate)
- Commission is written to "at-risk" status in TESS
- Client relationship escalated to Harlan + Commander for long-term recovery plan
- Do NOT proceed with cancellation without explicit Commander+client agreement

---

## 5. FINANCIAL TRACKING

### Commission At-Risk Designation

When FPD reaches 30 days overdue:
- Commission associated with that booking moves to "AT-RISK" status in financial tracking
- Harlan updates TESS commission record: flag as "COLLECTION-PENDING" with link to hale_decisions.md entry
- Weekly report includes at-risk commission separately from received/expected totals

### Collection Success Metrics
- Days-to-collection: tracked from overdue trigger to receipt confirmation
- Collection rate: % of expected commissions collected by voyage departure
- Escalation velocity: time from 30-day trigger to successful contact

---

## 6. EXEMPTIONS & EXCEPTIONS

### When This SO Does NOT Apply

1. **Payment Plan Agreement:** Client has signed, dated payment plan with scheduled milestones → managed per plan, escalation trigger pauses until plan milestones are missed
2. **Cruise Line Processing Delay:** Cruise line has confirmed payment received but not yet posted to final accounting → contact pauses, follows up per cruise line timeline (not overdue for D2M purposes)
3. **Client Dispute:** Client claims payment was sent or disputes the amount due → escalate to Commander with evidence, do not enforce until dispute resolved
4. **Client Relationship Critical:** Client is repeat, high-value, or strategically important, and Commander determines softer approach warranted → Commander may override escalation in writing (log in hale_decisions.md)

### Override Documentation
If Commander overrides this protocol for any booking, document in hale_decisions.md:
- Reason for override
- Alternative approach authorized
- Timeline for alternative (if applicable)

---

## 7. RESPONSIBILITIES

| Role | Responsibility |
|------|---|
| **A3 FPD Sentinel (automated state machine)** | Daily scan of TESS + dossiers, flag items at threshold, feed to Hale |
| **Hale (COS)** | Route escalated FPDs to Commander, create mission board task, send Telegram alert, document outcome in hale_decisions.md |
| **Reyes (A8 — Experience)** | Add collection action entries to client dossier TP sequences (post-action, per Hale routing) |
| **Harlan (A9 — Financial)** | Update TESS commission records with AT-RISK designations when Hale flags, track collection metrics weekly |
| **Commander** | Initiate client contact within 48 hours, document outcome, approve any deviations from escalation ladder |

---

## 8. REVIEW & REVISION

This Standing Order will be reviewed quarterly (first review: 2026-09-09) to assess:
- Collection success rate (target: ≥90% collected before voyage departure)
- Escalation velocity (target: <5 days from trigger to successful contact)
- Client relationship impact (zero cancellations attributable to escalation process)
- Exceptions logged (% of FPDs exempted from enforcement)

If collection rate falls below 70% or escalation velocity exceeds 7 days in any quarter, this SO will be escalated to Wing Exercise review with Harlan + Commander + Sterling.

---

## 9. AUTHORITY & SIGNATURE

**Standing Order Authority:** This SO derives from and reinforces Commander's sole financial collection authority as stated in SO-2026-05-04 (COS Authority Consolidated).

**Effective Date:** Upon Commander signature below. All FPDs currently overdue 30+ days are immediately subject to Tier 2 or Tier 3 escalation, as appropriate to their current age.

**Previous Related SOs Superseded:** None. This SO is new doctrine. Prior FPD handling was ad-hoc; this formalizes it.

---

## APPENDIX: CURRENT ESCALATION QUEUE (As of 2026-06-09)

| Client | Voyage | FPD Overdue | Days | Commission at Risk | Escalation Tier |
|--------|--------|-------------|------|-------------------|-----------------|
| McLeod McGlasson | Silver Muse (Jun 18) | $[amount] | 132 | $[amount] | **Tier 3** (voyage <10 days) |
| Kuklinski | Viking Mars (Dec 17) | $[amount] | 66 | $[amount] | Tier 1 (new trigger) |
| Furlow / Ely-Darrow | Regent Grandeur | $[amount] | 65 | $[amount] | Tier 1 (new trigger) |
| Morton & Dodge | Viking Mars (Dec 17) | $[amount] | [TBD] | $[amount] | Tier 1 (pending confirmation) |
| **[Additional clients per TESS scan]** | — | — | — | — | — |

**Action required:** Commander to sequence Tier 1 contacts for Kuklinski + Furlow + Morton & Dodge within 48 hours. McLeod requires immediate Tier 3 contact (voyage departure < 10 days).

---

**Standing Order Status: READY FOR COMMANDER REVIEW & SIGNATURE**

**Prepared by:** Thunderbird OS / Hale (acting for Sterling, A7 process authority)

**Date Prepared:** 2026-06-09

**Pending:** Commander signature to activate enforcement protocol

---

*This Standing Order is binding upon signature and supersedes all prior FPD handling protocols. Questions or edge cases: escalate to Commander + Harlan for guidance.*
