# STANDING ORDER — AI PIPELINE INTEGRITY
## SO-PIPELINE-INTEGRITY-20260528
**Issuing Authority:** Commander John Loucks ("Yoda")
**COS Execution:** V. Hale, VCS
**Date:** 2026-05-28
**Classification:** Wing-Wide | Permanent (Phase 1) + Time-Bound (Phase 2)
**Trigger:** T4 Wing Exercise — Commander decision: Option C

---

## BACKGROUND

T4 Wing Exercise (2026-05-28) identified a systemic AI pipeline integrity failure. The multi-hop pipeline (AI memo → AI memo → client draft) had no primary source verification gate. Four error classes were confirmed in a single 24-hour run: hallucination, speculation-as-fact, stale source contradiction, and dossier corruption. WF-17 (Commander's eyes) was the only gate between these errors and a client.

Commander directed Option C: Phase 1 guardrails active immediately, single-hop architecture to replace the multi-hop chain within one week.

---

## PHASE 1 — FIVE RULES (EFFECTIVE IMMEDIATELY — PERMANENT)

### Rule 1 — Negative-Space Rule (Option 6)
**If a fact is not confirmed in a primary source, it does not appear in a client email.**

Primary sources: client dossier, cruise line portal (verified same session), TESS booking record.

"Likely," "pending response," "our understanding," and "probably" are banned in client emails. If the status of anything is unknown, either (a) do not mention it or (b) state only what IS confirmed and omit the rest.

Enforcement: Hale enforces before passing any draft to Sterling or WF-17.

### Rule 2 — Confidence Tagging (Option 1)
**Every claim in a staff memo is tagged at the point of writing.**

| Tag | Meaning |
|-----|---------|
| `CONFIRMED` | Directly in primary source, verified this session |
| `INFERRED` | Derived from primary source data, not explicitly stated |
| `UNKNOWN` | No primary source evidence — sourcing gap |

Hale rejects any memo that reaches her without tags. Sterling red team rejects any draft built from INFERRED or UNKNOWN claims in the client-facing portion.

### Rule 3 — Sterling Red Team (Option 5)
**Every client draft receives one Sterling pass against the primary dossier before WF-17.**

Sterling's check: can every claim in the client email be traced to a primary source field? Sterling flags any claim that cannot. Flagged drafts return to Hale for correction before WF-17.

This rule is retired when the automated diff bot (Phase 2, Option 4) is operational.

### Rule 4 — Financial Hard-Source Rule (Option 3)
**Dollar amounts, balances, and payment dates in client emails must trace to a primary source.**

The pipeline rule: memo may reference a figure, but the draft must independently verify it against portal, TESS, or dossier before using it in client-facing copy. If the portal and dossier disagree, the portal figure is authoritative. The discrepancy must be resolved (or flagged) before the draft goes to WF-17.

This rule is permanent.

### Rule 5 — Harlan Financial Sign-Off (Option 8)
**Any client email containing a dollar figure requires Harlan's six-step verification before WF-17.**

Harlan's six-step protocol:
1. Confirm balance against portal (same-session check)
2. Confirm FPD against portal (same-session check)
3. Compare portal figure vs. dossier figure — flag any delta
4. If delta exists: identify root cause or note as unresolved
5. Confirm whether any credits (FCC, OBC) have been applied
6. Sign off: "Harlan confirmed: $[amount] as of [date], source: [portal/TESS/dossier]"

This rule is permanent.

---

## PHASE 2 — SINGLE-HOP ARCHITECTURE (Target: 1 week — ~2026-06-04)

### Owner: A7 Sterling
### What changes:
The multi-hop pipeline (AI memo → AI memo → client draft) is retired for client-facing products.

Replacement workflow:
```
Primary source (dossier) → ONE controlled AI pass → Client email draft
```

Personas (Dani, Harlan, Castillo) continue to write memos for Commander awareness and Hale's situational context. They do NOT chain into client email drafts. The draft comes from one pass directly over primary source, with Phase 1 rules applied.

### What survives from Phase 1 at Phase 2 activation:
- Rule 1 (Negative-space rule): permanent
- Rule 4 (Financial hard-source rule): permanent
- Rule 5 (Harlan financial sign-off): permanent

### What retires at Phase 2 activation:
- Rule 2 (Confidence tagging on memos): retired — memos no longer feed drafts
- Rule 3 (Sterling manual red team): retired — replaced by automated diff bot (Option 4)

### Phase 2 completion gate:
Sterling declares Phase 2 live. Hale confirms. CLAUDE.md updated to reflect retired Phase 1 rules. Commander notified.

---

## IMMEDIATE ACTIONS (FROM T4 — INDEPENDENT OF PHASE 1/2)

| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | Loucks dossier remediation (1,557 lines Kuklinski contamination) | A7 Sterling | 2026-05-29 | ✅ Done 2026-05-28 |
| 2 | McLeod draft correction — remove Medallion Suite reference | Hale | Now | ✅ Done 2026-05-28 |
| 3 | McLeod dossier balance → $11,943.15; suite bid flagged | Hale | Now | ✅ Done 2026-05-28 |
| 4 | TESS re-auth | Commander | 2026-05-31 | ⏳ Pending |
| 5 | "Lisa McGlasson" → "Melissa Etola McGlasson" in Dani memo | Hale | Now | ✅ Done 2026-05-28 |
| 6 | Outbound email audit — has anything wrong already gone out? | Hale + Sterling | 2026-05-30 | ⏳ 48-hr window |

---

## OPEN CONFLICTS (For the Record)

**Harlan vs. Sterling on Loucks commission ($180.33):**
Sterling (T3) flagged a $180.33 overstatement. Harlan (T4) audited and confirmed $4,652.10 is correct: $25,798 × (0.22 ÷ 1.22) = $4,652.03 ≈ $4,652.10. Sterling's T3 finding appears to have been an error in Sterling's formula. Sterling must formally acknowledge within 48 hours. Harlan's figure stands until Sterling responds.

---

## ENFORCEMENT

**Hale owns Phase 1 enforcement.** Any client draft that bypasses any of the five Phase 1 rules is returned before WF-17 — no exceptions.

**Sterling owns Phase 2 build.** Target date 2026-06-04. Weekly status to Hale.

**Washington's audit question stands open:** Outbound email audit for AI memo-sourced errors since 2026-05-01. Results to Commander within 48 hours.

---

## SUPERSEDES / RELATED

- Supplements: SO_STERLING_COMMS_VERIFICATION_PROTOCOL_20260518.md (financial verification elements now formalized here)
- Supplements: SO_QUALITY_MANAGEMENT_20260516.md (quality gate element)
- Does not supersede: SO-2026-05-04 (autonomy charter), SO-HALE-AAR-20260524 (corrective rules)

---

*Issued: V. Hale, VCS | Thunderbird Wing | 2026-05-28*
*T4 Wing Exercise — Commander-approved Option C*
*Full staff outputs: /home/john/Thunderbird/output/t4_[name]_20260528.md*
