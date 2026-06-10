# File-Level Permission Architecture — Implementation Guide

**Status:** READY FOR PHASE 2  
**Authority:** Sterling (A7) — Architecture Author  
**Date:** 2026-06-09  
**Approval:** Pending Commander Review

---

## Quick Start for Developers

### Phase 1 Status: ✅ COMPLETE
- [x] File registry created: `docs/FILE_OWNERSHIP_REGISTRY.json`
- [x] Architecture documented: `output/executor_results/MISSION-079_20260609.md`
- [x] Domain ownership finalized
- [x] Ready for Commander approval

### Phase 2: Coming 2026-06-16 (Pending Approval)
When Commander approves, Sterling will:
1. Write `hooks/file-permission-pre-commit.py` (full Python script provided in architecture doc)
2. Write `scripts/setup-permission-hook.sh` (installation script)
3. Deploy to all dev machines
4. Test with 5 commits (mixed scenarios)

---

## Understanding Your Ownership

### As Sterling (A7)
**You own:** All production code, governance, configuration, and infrastructure
- Can commit to: `core/`, `scripts/`, `config/`, `CLAUDE.md`, `standing_orders/`, `Personas/`, `infra/`, `docs/`
- Cannot commit to: Dossier experience sections (Reyes), state files (Hale), proposals (ELON)
- Responsibility: All architecture decisions, code review, policy publication

### As Reyes (A8)
**You own:** Client experience planning and dossier experience sections
- Can commit to: `dossiers/*/Excursion*.md`, `dossiers/*/Dining*.md`, `dossiers/*/Activity*.md`
- Cannot commit to: Code, governance, state files, financial sections
- Responsibility: Experience curation, excursion/dining planning, accessibility coordination

### As Hale (COS)
**You own:** Operational state and routing
- Can commit to: `hale_*.json`, `hale_*.md`, `OpsCenter/collaboration/`, `logs/executor_results/`
- Cannot commit to: Code, governance, dossiers, proposals
- Responsibility: State management, routing, operational status

### As ELON (A12)
**You own:** Innovation proposals and incubation
- Can commit to: `OpsCenter/elon_proposals/*`
- Cannot commit to: Code, governance, dossiers, state
- Responsibility: Proposal curation, innovation pipeline, kill-audit

### As Naia (EXEC) or Dani (A3)
**You own:** Editorial feedback (not file commits)
- Can edit: Provide voice/brand feedback on drafts
- Cannot commit: No direct file writes (editorial pass through review)
- Workflow: Review drafts → provide feedback → original author incorporates

---

## The Three-Layer Architecture

```
┌─────────────────────────────────────────────┐
│ LAYER 1: PROCESS (PRODUCTION-LOCK Routing)  │
├─────────────────────────────────────────────┤
│ Hale recognizes cross-domain work needed    │
│ → Creates routing ticket to domain owner    │
│ → Domain owner executes change              │
│ → Hale closes ticket when commit appears    │
└─────────────────────────────────────────────┘
           ↓ (enables enforcement)
┌─────────────────────────────────────────────┐
│ LAYER 2: AUTOMATION (Pre-commit Hook)       │
├─────────────────────────────────────────────┤
│ Author writes code → stages commit          │
│ → Pre-commit hook validates ownership       │
│ → ✅ Pass: commit allowed                   │
│ → ❌ Fail: commit rejected + clear message  │
│ → NO BYPASS without Commander override      │
└─────────────────────────────────────────────┘
           ↓ (supports monitoring)
┌─────────────────────────────────────────────┐
│ LAYER 3: POLICY (Standing Order + Metrics)  │
├─────────────────────────────────────────────┤
│ PRODUCTION-LOCK rule (Hale COS § Failure D) │
│ Metrics: 0 unauthorized commits/week        │
│ Audit: Monthly by Sterling (Baldrige sweep) │
│ Escalation: Commander if trend reverses     │
└─────────────────────────────────────────────┘
```

---

## When You Hit the Hook (Phase 2+)

### Scenario 1: Legitimate Commit (Passes Hook)
```bash
$ git commit -m "Fix: validate Kuklinski FPD logic"
[master 5a7c3b1] Fix: validate Kuklinski FPD logic
 1 file changed, 15 insertions(+)
✅ Commit accepted
```

### Scenario 2: Cross-Domain Edit (Hook Rejects)
```bash
$ git commit -m "Update Reyes dossier excursion"
🚨 FILE PERMISSION VIOLATIONS DETECTED

  File:       dossiers/Kuklinski/Excursion_Plan.md
  Owner:      Reyes
  Protection: EXPERT
  Author:     Sterling
  Status:     ❌ UNAUTHORIZED

RESOLUTION:
  1. Revert changes (git checkout dossiers/Kuklinski/Excursion_Plan.md)
  2. Route to Reyes via PRODUCTION-LOCK ticket
  3. Or obtain Commander override for this commit

❌ Commit rejected
```

**What to do:**
1. Revert the file: `git checkout dossiers/Kuklinski/Excursion_Plan.md`
2. Create routing ticket to Reyes with the proposed change
3. Let Reyes commit the change himself

### Scenario 3: Emergency Override (Commander-Authorized)
```bash
Commander: "Sterling, execute the Reyes dossier fix yourself."

$ git commit -m "Fix: update Reyes excursion [COMMANDER-OVERRIDE-001]"
[master 5a7c3b1] Fix: update Reyes excursion [COMMANDER-OVERRIDE-001]
✅ Commit accepted (override token honored)

(Note: Next similar task must go through Reyes)
```

---

## PRODUCTION-LOCK Routing Ticket Template

Use this format when you need to route work across domain boundaries:

```markdown
## PRODUCTION-LOCK ROUTING TICKET

**FROM:** Sterling (A7)
**TO:** Reyes (A8)
**ARTIFACT TYPE:** dossier
**URGENCY:** P1 — blocker

### Work Item Description
Update Kuklinski excursion plan for Jun 18 departure. Need to add Grand Cayman snorkel option + update accessibility notes for Elena's mobility concerns.

### Files Affected
- `dossiers/Kuklinski_Group_Viking_Mars/Excursion_Plan.md`
- `dossiers/Kuklinski_Group_Viking_Mars/Accessibility_Accommodations.md`

### Change Summary
- Line 42-47: Add Grand Cayman snorkel as Tier-2 option (cost $150/person)
- Line 89-95: Expand accessibility section with wheelchair ramp locations at port

### Proposed Changes
[Diff or proposed text]

### Status
STAGED — awaiting Reyes execution

### Override Token
None (normal routing)

---
**Created:** 2026-06-09 14:30  
**ETA:** Same-day execution
```

---

## Metrics & Monitoring

### What Sterling Tracks (Weekly)
```bash
# Every Sunday in Baldrige sweep
git log --since=1.week --name-only \
  | xargs -I {} python3 hooks/file-permission-pre-commit.py --audit {}
```

**Report includes:**
- ✅ Legitimate commits per domain owner
- ⚠️ Pre-commit hook rejections (filed as tickets)
- ✅ PRODUCTION-LOCK tickets routed and executed
- 📊 Compliance trend (target: 0 unauthorized commits)

### What Hale Reports (Daily)
Morning brief includes section:
```
### FILE PERMISSION STATUS
- PRODUCTION-LOCK violations detected: 0
- Routing tickets active: 2 (Reyes-excursion, ELON-incubator)
- Unauthorized commits blocked: 0
```

---

## FAQ

### Q: I need to fix something in Reyes' dossier section. What do I do?
**A:** 
1. Prepare your change (diff or proposed text)
2. Create a PRODUCTION-LOCK routing ticket
3. Send to Reyes
4. Reyes commits the change
5. You close ticket when commit appears

### Q: What if Reyes isn't available and we have a blocker?
**A:** Escalate to Commander. Don't bypass the hook. Say: "Reyes unavailable for [X] hours. Do I route to Sterling or proceed solo?"

### Q: Can I commit governance files to CLAUDE.md?
**A:** No. All CLAUDE.md edits go through Sterling. Create a routing ticket with your proposed change.

### Q: The hook rejected my commit but I know I should have access. What happened?
**A:** 
1. Check `docs/FILE_OWNERSHIP_REGISTRY.json` — make sure you're listed as an authorized author
2. Confirm your git user.name matches your persona name
3. Contact Sterling to verify registry is current
4. If override is needed, get Commander approval

### Q: What counts as a "legitimate" override?
**A:** 
- Commander explicitly says: "Hale, execute [this task] yourself"
- Named, specific task (not blanket permission)
- Fires once; next similar task requires same process
- Logged in `hale_decisions.md`

---

## Success Metrics (Phase 2+)

**Weekly Target:**
- ✅ 0 unauthorized commits from pre-commit hook rejections
- ✅ 100% of routed PRODUCTION-LOCK tickets executed by domain owner
- ✅ <5% of commits marked with emergency override

**Monthly Target:**
- ✅ Trend analysis shows improving compliance
- ✅ lessons_implementation_rate_pct ≥ 80%
- ✅ No escalations to Commander for governance violations

---

## References

- **Full Architecture:** `output/executor_results/MISSION-079_20260609.md`
- **File Registry:** `docs/FILE_OWNERSHIP_REGISTRY.json`
- **PRODUCTION-LOCK Rule:** `Personas/hale_cos.md` § Failure D
- **Related SO:** `standing_orders/SO_A7_OVERSIGHT_AUTHORITY_20260513.md`

---

**READY FOR COMMANDER APPROVAL AND PHASE 2 IMPLEMENTATION**
