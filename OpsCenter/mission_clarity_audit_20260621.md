# Mission Clarity Audit — 2026-06-21
## ELON Review: 6 UNCLEAR Missions

**Board State:** 314 total missions | 47 active/in_progress | 6 flagged UNCLEAR

---

## Executive Summary

| Mission | Category | Recommendation | Reason |
|---------|----------|---|---------|
| **MISSION-236** | Manual Portal Maintenance | **KILL** | Tactical workaround masquerading as a mission; should be a runbook step, not a standing task |
| **MISSION-291** | Tool Monitoring | **SUSPEND** | Valid but dormant; triggers only if OpenCode hits 3-strike failure threshold — zero action until then |
| **MISSION-296** | Prep Work | **CLARIFY** | Real work, but scope is undefined — missing "done" criteria and blocking factor (awaiting Anthropic announcement) |
| **MISSION-297** | Model Evaluation | **CLARIFY** | Clear test scope but missing success pass/fail gate and routing table decision criteria |
| **MISSION-301** | Infrastructure Hardening | **SUSPEND** | Residual risk accepted by design; revive only if threat model changes or local compromise detected |
| **MISSION-304** | Tool Watch | **SUSPEND** | Speculative multi-vendor architecture; triggers only on explicit Commander decision to add new agent vendor |

---

## Detailed Analysis

### MISSION-236 — Manual Regent OA Re-authentication
- **Status:** Active | **Priority:** P1 | **Assigned:** Commander
- **Title:** Manual Regent OA re-authentication to restore B2B portal coverage
- **Scope:** Log into Regent OA portal via Firefox to bypass reCAPTCHA, restore automated keepalive
- **Problem:** This is a WORKAROUND disguised as a mission, not an actionable task. "Restore coverage before the next fare watch cycle" is vague and requires manual intervention on every credential reset.
- **Clarity Issues:**
  - No clear "done" — is it done once the login succeeds? Or once keepalive is verified? Or until the next timeout?
  - No suspense date — when should this be completed?
  - No success metric — how do we know keepalive is truly restored?
  - Assigned to Commander, but it's tactical ops work (belongs in runbook)

**Recommendation: KILL**  
*Reason:* This is a **known blocker in a runbook**, not a strategic mission. Convert to a runbook step in "Regent Portal Keepalive Failure Recovery" with clear decision tree (detect failure → execute steps A-C → verify → close). The mission board should track strategic initiatives, not recurring manual workarounds.

**Next:** Move to `docs/RUNBOOKS/regent_keepalive_failure_recovery.md`. Revisit automation opportunity (A12 ELON audit: can we solve the reCAPTCHA block via API or session capture?).

---

### MISSION-291 — ELON WATCHLIST (Omnigent Meta-Harness)
- **Status:** In_Progress | **Priority:** P0 | **Assigned:** Unassigned
- **Title:** ELON WATCHLIST —
- **Scope:** Monitor omnigent-ai/omnigent (4.2K stars) meta-harness. Relevance trigger: if OpenCode fails as primary engine, this architecture can hot-swap Claude Code/Codex/Cursor without rewriting prompts.
- **Completion Criteria:** "Zero action until OpenCode hits 3-strike replacement threshold per CI doctrine."

**Clarity Issues:**
- Title is incomplete ("—" is not a description)
- "Zero action until" = this is a MONITORING mission with no explicit kill criteria
- No owner assigned
- No decision gate (when does ELON escalate this to Commander?)
- Success metric is implicit: "if OpenCode fails, we know this worked"

**Recommendation: SUSPEND**  
*Reason:* This is a valid **contingency watch** but should NOT be on the active mission board. It's an insurance policy that pays off only if OpenCode fails 3x. It has a clear activation trigger (CI doctrine: 3-strike) and a clear owner (ELON). Suspend to dormant; Hale auto-revives on CI threshold breach.

**Clarified Definition-of-Done:** "ELON monitors OpenCode failure rate daily via CI dashboard. If OpenCode hits 3 consecutive failures within 7 days (per SO_CI_RAZOR_SHARP), escalate omnigent as replacement architecture to Commander with cost/complexity analysis. Done when Commander approves next-engine selection."

---

### MISSION-296 — Agent SDK Billing (Split Prep)
- **Status:** In_Progress | **Priority:** P0 | **Assigned:** Unassigned
- **Title:** Agent SDK Billing
- **Scope:** Audit all headless `claude -p` invocations in Thunderbird OS. Anthropic paused June 15 billing split (MAX 5x headless/Agent SDK moving to separate $100/mo credit pool). Prepare for cost tracking when split lands.
- **Problem:** Mission is blocked on Anthropic announcement; no clear definition-of-done; target deliverable is vague.

**Clarity Issues:**
- **No completion date** — "When it lands" is speculation, not a deadline
- **No deliverable specified** — is the audit a CSV? A config change? A report to Sterling?
- **No owner** — unassigned; ELON owns cost optimization, but this is assigned to nobody
- **Blocking factor is external** — Anthropic's announcement timing
- Success criteria "Flag which are interactive vs automated" is clear, but what comes next?

**Recommendation: CLARIFY**  
*Reason:* Real work, but scope drifts. This is **prep work for a future billing model**, not a current mission. Should be reprioritized when Anthropic lands the split.

**Suggested New Title & Definition-of-Done:**  
"**MISSION-296 (DEFERRED) — Agent SDK Billing Inventory**  
*Done when:* Inventory complete of all headless Claude invocations (scripts, GitHub Actions, cron jobs, agent spawns) categorized as interactive (developer-initiated) or automated (daemon/mission-triggered). Output: CSV in `config/agent_sdk_inventory.csv` with columns [Path, Type, Interactive/Automated, Monthly Invocation Est.]. Owner: ELON. Status: HOLD until Anthropic announces billing split; auto-activate on announcement. Review interval: weekly."

---

### MISSION-297 — Big Pickle (GLM-4.6) Model Evaluation
- **Status:** In_Progress | **Priority:** P0 | **Assigned:** Unassigned
- **Title:** Big Pickle (GLM-4.6)
- **Scope:** Evaluate GLM-4.6 (free tier, 200 req/5hr limit) for low-complexity tasks (log scans, JSON extraction, status checks, classification). If passes, add to SO-TOKEN-DISCIPLINE routing table as zero-cost tier below Haiku.
- **Test Plan:** Run 5 current Haiku tasks through GLM-4.6, compare output quality.
- **Problem:** Test scope is clear but **success criteria are missing**. What does "pass" mean? No pass/fail gate defined.

**Clarity Issues:**
- **No pass/fail threshold** — "compare output quality" is subjective. Pass if 4/5 tasks match? 90% accuracy? Response time <2s?
- **No owner** — unassigned; should be ELON (tech adoption) with Sterling (code quality gate)
- **Vague routing integration** — "add to SO-TOKEN-DISCIPLINE routing table" — what are the exact integration points?
- **No decision criteria** — if it passes, is it auto-adopted? Or Commander approval?

**Recommendation: CLARIFY**  
*Reason:* Test scope is solid, but mission needs **objective success gate** and integration decision rule.

**Suggested New Definition-of-Done:**  
"**MISSION-297 (REVISED) — Big Pickle (GLM-4.6) Evaluation**  
*Scope:* Test GLM-4.6 free tier (200 req/5hr) on 5 representative Haiku tasks: (1) log scan + filter, (2) JSON extraction from text, (3) status code classification, (4) CSV parse + aggregate, (5) error message routing.  
*Pass Criteria:* ≥4/5 tasks produce functionally correct output matching existing Haiku output (token cost <0.5x Haiku, latency <3s). If passes: add to `SO-TOKEN-DISCIPLINE-20260529.md` routing table with rule 'Route: log-scan, json-extract, status-check, classification → Big Pickle if response_complexity < threshold_2 tokens.' Owner: ELON (test lead) + Sterling (QA gate). Suspense: 2026-06-28. Done when: routing rule live in SO and first 3 production tasks routed + monitored 48h with zero regressions."

---

### MISSION-301 — Chrome CDP 9222 Hardening
- **Status:** In_Progress | **Priority:** P2 | **Assigned:** Unassigned
- **Title:** Chrome CDP 9222
- **Scope:** No-auth hardening for remote debugging port. Chrome is loopback-bound (127.0.0.1) but has no native auth. Risk: any local process can drive Chrome and lift logged-in cookies from Gmail, cruise portals.
- **Current Risk:** Accepted (residual); mitigation: loopback binding limits blast radius to local foothold only.
- **Solution:** Dedicated user/namespace (M-256, follow-on). CDP collides with PII fence for non-Claude agents.
- **Problem:** Mitigation is accepted by design ("zero action" until threat model changes). This is NOT a current mission — it's a recorded risk with an acknowledged tradeoff.

**Clarity Issues:**
- **No completion target** — is this a threat model exercise? An implementation task? A decision gate?
- **No owner** — Sterling (infra) + Dembe (threat model) are mentioned but unassigned
- **"Residual risk accepted"** = the decision is already made; no action needed now
- **Blocking factor:** Implicit — waiting for a higher-privilege compromise attempt or operator decision to harden further

**Recommendation: SUSPEND**  
*Reason:* This is a **documented risk with accepted mitigation**, not an active mission. Revive only if: (a) local compromise detected, (b) threat model changes (e.g., untrusted container neighbors), or (c) Commander decides to harden now (gates 7-day implementation sprint).

**Clarified Definition-of-Done (when activated):**  
"When activated by threat event or Commander directive: implement M-256 dedicated user/namespace for Chrome process, verify PII fence isolation (no Dembe/non-Claude agent traffic via CDP), document in security runbook. Done when: Whetstone verifies no regression in live portal access, Dembe threat model confirms acceptable residual risk, no alerts for 7 days."

---

### MISSION-304 — Agent Switchboard (MCP Bridge)
- **Status:** In_Progress | **Priority:** P3 | **Assigned:** Unassigned
- **Title:** WATCH: Agent Switchboard
- **Scope:** Multi-vendor MCP bridge (FutureisinPast/mcp-agent-switchboard). Trigger: if Commander decides to add Antigravity/Gemini-CLI/Codex as working wing agents. Allows local cross-vendor handoff (no API keys needed).
- **Decision Gate:** "Staff ruling: only if Commander decides to expand vendor roster beyond Claude/OpenCode."
- **Problem:** This is speculative. No active need. Trigger is external (Commander's business decision, not a technical failure).

**Clarity Issues:**
- **"WATCH" is not a scope** — title is incomplete
- **No owner** — "ELON scout" is vague; no formal assignment
- **No activation condition** — "if Commander decides" is a business call, not a technical trigger
- **Blocking factor:** Explicit — waiting for Commander decision + staff gate (Sterling + Dembe)

**Recommendation: SUSPEND**  
*Reason:* This is a **contingency option** with an external activation trigger (Commander's business decision to diversify agents). It has real value if that decision happens, but doesn't belong on the active board as "in_progress." Suspend to backlog; Hale routes to active status if Commander explicitly directs multi-vendor exploration.

**Clarified Definition-of-Done (when activated):**  
"When Commander approves multi-vendor agent strategy: evaluate mcp-agent-switchboard architecture for local bridge capability (Codex/Gemini-CLI/Antigravity behind PII fence). Done when: prototype built, tested cross-vendor handoff (Claude→Codex, Codex→Gemini), Sterling verifies code quality, Dembe confirms no PII leakage, Hale tests integration in 2 live workflows. Decision: adopt vs build custom bridge. Suspense: 14 days from Commander directive."

---

## Board Health Patterns

### What Makes a Mission Stay UNCLEAR?

1. **Speculative Missions** (MISSION-291, MISSION-304)
   - Monitoring/watch tasks without explicit failure triggers
   - Listed as "if X happens, we're ready" — but X hasn't happened
   - **Root cause:** Trying to track contingencies on the same board as active work
   - **Fix:** Move contingencies to a "Contingency Backlog" (separate from mission board); auto-activate on trigger

2. **Prep Work with External Blockers** (MISSION-296)
   - Real work, but completion depends on external announcement/decision
   - No clear deadline; "when it lands" is vague
   - **Root cause:** Premature mission creation before blocker is resolved
   - **Fix:** Create mission AFTER blocker is lifted (e.g., when Anthropic announces split); use a calendar alarm instead

3. **Accepted Mitigations** (MISSION-301)
   - Technical risk documented with "residual risk accepted"
   - Not a task — it's a design decision
   - **Root cause:** Confusion between "decision logged" and "task to do"
   - **Fix:** Move to threat model docs or risk register; don't put it on mission board

4. **Workarounds Treated as Missions** (MISSION-236)
   - Recurring manual steps to work around a blocker
   - Should be in runbooks, not on board
   - **Root cause:** Treating symptom fixes as strategic initiatives
   - **Fix:** Create runbook; board tracks root-cause fix (e.g., "MISSION-XXX: Automate Regent keepalive to eliminate manual re-auth")

5. **Evaluation Tasks Without Success Gates** (MISSION-297)
   - Clear test scope but no pass/fail criteria
   - "Compare output" is subjective
   - **Root cause:** Owner didn't articulate decision rule upfront
   - **Fix:** Define thresholds before testing (4/5 pass, accuracy >90%, etc.)

---

## Recommendations for Board Hygiene

### Immediate Actions
1. **KILL MISSION-236** → Convert to runbook step; board tracks root-cause automation fix
2. **SUSPEND MISSION-291, MISSION-304** → Move to Contingency Backlog; auto-activate on trigger
3. **CLARIFY MISSION-296, MISSION-297, MISSION-301** → Rewrite with clear done criteria and owner assignment

### Process Changes
1. **No Speculative Missions** — Contingencies live in a separate backlog (not "in_progress"). Board shows only active work.
2. **No External Blockers** — If completion depends on external announcement/decision, don't create mission until blocker is resolved (e.g., Anthropic billing split lands).
3. **Every Mission Needs:** Title (complete sentence, not "—"), Description (clear scope), Owner (named), Done Criteria (objective, verifiable), Suspense Date (if applicable).
4. **Runbooks, Not Missions** — Recurring manual procedures → runbook steps. Board tracks strategic fixes only.

---

## Summary Table for Sterling Review

| Mission | Recommendation | Action | New Status | Owner | Done Criteria |
|---------|---|---|---|---|---|
| **MISSION-236** | KILL | Convert to runbook; kill mission | KILLED | Hale (runbook) + ELON (root cause) | Root cause automation fix tracked separately |
| **MISSION-291** | SUSPEND | Move to contingency backlog | SUSPENDED | ELON | Auto-activate: CI threshold 3 failures / 7d |
| **MISSION-296** | CLARIFY | Rewrite scope + deliverable | DEFERRED | ELON | Inventory CSV + routing docs; auto-activate on Anthropic announcement |
| **MISSION-297** | CLARIFY | Define pass/fail gate | IN_PROGRESS | ELON (lead) + Sterling (gate) | 4/5 tasks pass; add to SO_TOKEN_DISCIPLINE by 2026-06-28 |
| **MISSION-301** | SUSPEND | Move to threat model docs | SUSPENDED | Sterling (infra) + Dembe (threat) | Auto-activate: threat event or Commander directive |
| **MISSION-304** | SUSPEND | Move to contingency backlog | SUSPENDED | ELON (scout) | Auto-activate: Commander multi-vendor decision |

---

**Audit Date:** 2026-06-21 17:32 MT  
**Auditor:** ELON, A12 Innovation & Disruption  
**For Review:** Sterling (A7), Hale (COS)

*Done. Delivered clarity audit + board hygiene recommendations. Next: Sterling reviews; Hale routes KILLs and reformats CLARIFYs.*

— ELON
