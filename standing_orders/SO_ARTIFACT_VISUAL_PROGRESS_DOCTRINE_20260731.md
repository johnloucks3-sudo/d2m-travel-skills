# Standing Order — Mandatory Artifact Process & Visual Progress Bars in Project Management

**Date:** 2026-07-31
**Issued by:** Commander (John Loucks)
**Applies to:** All seats (Hale/CC, Jet/OC, Hale-AG/AG), personas, and delegated subagents

---

## 1. Directive

1. **Mandatory Durable Artifacts for Project Management & Delegation**:
   - For any non-trivial, multi-step, project management, or delegated task, the orchestrating seat and all delegated subagents MUST produce durable markdown artifacts:
     - **Implementation Plan Artifact**: `<plan_name>.md` created prior to non-artifact code changes.
     - **Walkthrough Artifact**: `walkthrough.md` created/updated upon completing work.
   - Chat scroll text alone is strictly prohibited for tracking substantive project status or multi-step execution. Chat text scrolls away; artifacts endure.

2. **Mandatory Visual Progress Bars Standard**:
   - Every project status brief, implementation plan, walkthrough, and task delegation report MUST include ASCII/Unicode visual progress bars:
     - **Overall Progress**: `[████████████████████] 100%` / `[████████░░░░░░░░░░░░] 40%`
     - **Component-Level Breakdown**: Visual progress bar for each sub-task, feature area, or milestone.

3. **Delegation Contract Requirement**:
   - All agent tasking specs (Claude Code `ask`, OpenCode `dispatch_oc`, Anti-Gravity `contact_ag`, and native subagent prompts) MUST explicitly instruct recipient agents to maintain visual progress bars and produce durable artifact deliverables.

4. **Compliance & Audit**:
   - Sterling (A7 Oversight & Quality Chief) shall audit task outputs for adherence to the Artifact & Visual Progress Bar standard. Missing artifacts or progress bars on non-trivial work constitute a documentation compliance failure.
