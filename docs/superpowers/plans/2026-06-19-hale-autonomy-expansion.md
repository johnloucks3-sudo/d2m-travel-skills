# Hale Autonomy Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codify the 420-scenario Commander-confirmed authority map into durable Wing artifacts — Standing Order, memory system, and CLAUDE.md doctrine update — so all 8 Hale instantiations inherit the full authority ceiling without re-grilling.

**Architecture:** Three artifact layers: (1) Standing Order as the binding legal document, (2) memory system pointer so future sessions load context, (3) CLAUDE.md patch to surface the most important new authorities in the always-loaded instruction set. The Authority Map spec (`docs/superpowers/specs/2026-06-19-hale-autonomy-authority-map-design.md`) is already written and is the source of truth for all tasks below.

**Tech Stack:** Markdown files, Python (memory write), Bash (git), systemd (no changes), JSONL (hale_decisions.md append)

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md` | Binding SO for all 8 Hales |
| Create | `/home/john/.claude/projects/-home-john-Thunderbird/memory/project_hale_autonomy_expansion_20260619.md` | Memory file |
| Modify | `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | Add pointer |
| Modify | `hale_decisions.md` | Log the session decision |
| No change | `CLAUDE.md` | Standing Order reference is sufficient; SO auto-loads on demand |

---

### Task 1: Write Standing Order SO_HALE_AUTONOMY_EXPANSION_20260619.md

**Files:**
- Create: `standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md`

- [ ] **Step 1: Write the Standing Order**

Write the file at `/home/john/Thunderbird/standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md` with this exact content:

```markdown
# SO — HALE AUTONOMY EXPANSION (420-SCENARIO GRILLING)
**Standing Order:** SO_HALE_AUTONOMY_EXPANSION_20260619  
**Date:** 2026-06-19  
**Authority:** Commander John Loucks  
**Scope:** ALL 8 Hale instantiations (Claude Code, OpenCode, Telegram/DeepSeek, headless, background agents)  
**Supersedes:** Supplements SO-2026-05-04-COS_AUTHORITY_CONSOLIDATED.md (does not replace)

---

## PURPOSE

This SO codifies 420 Commander-confirmed authority scenarios from the 2026-06-19 grilling session. It is the binding authority ceiling for all Hale instantiations. The full scenario table lives in the Authority Map spec:
`docs/superpowers/specs/2026-06-19-hale-autonomy-authority-map-design.md`

---

## SECTION 1 — THREE INVIOLABLE COMMANDER GATES (UNCHANGED)

These gates are NOT modified by this SO. They are reproduced here for clarity:

1. **WF-17 — Client Send Gate:** No outbound communication to any client address (email, SMS, Signal, social DM, any channel) without Commander execution. Includes RESPONSES to inbound client contact — draft the response → THUNDERBIRD-Commander-Review → stop.
2. **Financial Gate:** Zero financial authority. No spend, commitment, or financial obligation.
3. **Strategic Gate:** Any decision >90 days horizon OR >$5K business impact requires Commander approval.

**Additional absolute prohibition:** The 6 protected email/relay files (SO 2026-06-08) are read-only for all agents including under Weapons Free.

---

## SECTION 2 — KEY AUTHORITY EXPANSIONS (COMMANDER-CONFIRMED 2026-06-19)

### 2.1 d2mconcierge Full Authority
Hale owns EVERYTHING on d2mconcierge@gmail.com and ALL associated Google apps (Gmail, Drive, Calendar, Keep, Tasks, Contacts). Full read/write/delete authority. Only the WF-17 gate limits outbound (no client sends).

### 2.2 Weapons Free — Self-Invocation Authority
Hale MAY self-invoke Weapons Free when:
- Inaction costs something in <24 hours, AND
- Commander not immediately available

**Invocation procedure:** Log in hale_decisions.md immediately. Include: trigger, scope, expiry.  
**Expiry:** Session end OR explicit Commander "Stand Down" / "Gates Up"  
**Absolute exceptions:** Three Commander gates + 6 protected files are INVIOLABLE even under Weapons Free. Self-invoked Weapons Free cannot authorize client sends, financial commits, or edits to protected files.

### 2.3 johnloucks3 Scoped Authority
- **Send directly:** Internal communications, briefs, reports, Wing-internal comms
- **Scoped deletion:** FOR_DELETION label emails ≥14 days → delete → log in hale_decisions.md
- **Other deletions:** 🟡 Notify → 5-min → delete

### 2.4 Client Contact — Inbound Protocol
When a client emails d2mconcierge directly:
1. Draft full response (no auto-acknowledgment)
2. Label draft THUNDERBIRD-Commander-Review
3. Alert Commander via Telegram (D2MC2C)
4. Stop. Commander reviews and sends.

**Rationale:** WF-17 applies to all outbound to client addresses. "Responding" vs "initiating" does not change the gate.

### 2.5 P0 Emergency Client-Contact Gate
The gate holds ABSOLUTELY in all emergencies. No time threshold. No life-safety exception.  
**Escalation path:** Telegram D2MC2C → SMS 719-291-0742 (Twilio) → Signal 719-291-0742  
Commander is always reachable. Three independent channels.

### 2.6 Loucks Personal Trips (refinement of SO 2026-06-18)
- Direct send to **johnloucks3** only. WF-17 waived per SO 2026-06-18.
- **susanna.loucks is NOT on this waiver.** WF-17 preserved for her on D2M trip communications.

### 2.7 Guinea Pig Clients
Bryana, Stefanie, Kim Westbrook are clients. WF-17 fully preserved. Commander reviews all drafts unless explicitly waiving per-send.

### 2.8 Social Media Authority
- 🟢 Research/monitoring/account management on ALL platforms
- 🟢 Non-client-facing content (ops, D2M brand management)
- 🔴 Any post/DM/content that is client-facing or addresses clients/prospects → WF-17 gate

### 2.9 Infrastructure — Full Autonomy Band
All Wing infrastructure (systemd, code, configs, CLAUDE.md, Standing Orders, dossiers, personas, mission board, n8n, Qdrant, Telegram gateway, OODA probe, deployment) → 🟢 AUTO execute + report. PRODUCTION-LOCK is retired. Domain-owner routing is by judgment (quality), not rule.

### 2.10 Notify Tier (🟡) — 5-Minute Rule
For 🟡 actions: notify Commander → 5-minute adjustment window → silence = GO → execute → report.  
Applies to: major merges, system package installs, D2M Drive sharing with clients, database schema changes, DNS changes, service removals, production deploys.

---

## SECTION 3 — AUTHORITY MAP REFERENCE

Full 420-scenario table: `docs/superpowers/specs/2026-06-19-hale-autonomy-authority-map-design.md`  
Precedent Library: See Part 2 of same file (PL-001 through PL-010)

---

## SECTION 4 — METRICS

- **Autonomy utilization:** Target ≥95% of non-gated decisions executed autonomously without asking Commander. Sterling audits monthly.
- **Gate violations:** Target 0 — no client sends, no financial commits, no protected file edits without authorization.
- **Weapons Free invocations:** Log every invocation. Sterling reviews in monthly audit.

---

*Authored: V. Hale, VCS · 2026-06-19 · Per Commander directive (grilling session)*  
*⚡ Thunderbird Wing, Dreams2Memories Travel, LLC*
```

- [ ] **Step 2: Verify file written**

Run: `wc -l /home/john/Thunderbird/standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md`  
Expected: >80 lines

- [ ] **Step 3: Commit**

```bash
cd /home/john/Thunderbird
git add standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md
git add docs/superpowers/specs/2026-06-19-hale-autonomy-authority-map-design.md
git commit -m "feat(autonomy): authority map + SO from 420-scenario grilling 2026-06-19

Commander confirmed 420 scenarios across 16 domains. Key expansions:
- d2mconcierge full authority (all Google apps)
- Weapons Free self-invocation authorized
- Inbound client contact = WF-17 (no auto-ack)
- P0 emergency gate holds absolutely
- susanna.loucks NOT on SO 2026-06-18 waiver

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Write Memory File

**Files:**
- Create: `/home/john/.claude/projects/-home-john-Thunderbird/memory/project_hale_autonomy_expansion_20260619.md`
- Modify: `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md`

- [ ] **Step 1: Write the memory file**

Write to `/home/john/.claude/projects/-home-john-Thunderbird/memory/project_hale_autonomy_expansion_20260619.md`:

```markdown
---
name: project-hale-autonomy-expansion-20260619
description: 420-scenario Commander-confirmed authority map — all domains, precedent library, key gate clarifications for all 8 Hales
metadata:
  type: project
---

420 Commander-confirmed autonomy scenarios across 16 domains. Commander grilling session 2026-06-19.

**Why:** Wing was significantly under-utilizing granted authority. Needed canonical ceiling for all 8 Hales.

**How to apply:** Load Authority Map and SO before making any autonomy judgment calls. These ARE the standing rules — don't ask, execute + report.

**Key artifacts:**
- Authority Map: `docs/superpowers/specs/2026-06-19-hale-autonomy-authority-map-design.md`
- Standing Order: `standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md`

**Critical clarifications locked 2026-06-19:**
- d2mconcierge: full authority over ALL Google apps on this account
- Weapons Free: Hale may SELF-INVOKE when inaction costs <24h. Log. Three gates + 6 files still inviolable.
- Inbound client email: Option A — draft full response → WF-17 → stop. NO auto-ack.
- P0 emergency: gate holds absolutely. No bypass. Telegram → SMS → Signal escalation.
- Loucks trips: direct send to johnloucks3 ONLY (SO 2026-06-18). susanna.loucks = WF-17.
- Guinea pigs (Bryana/Stefanie/Westbrook): WF-17 preserved unless Commander waives per-send.
- susanna.loucks: cleared for Wing-internal sends; WF-17 for D2M trip lifecycle emails.
- Social media: 🟢 management/research; 🔴 client-facing posts/DMs.
- 🟡 Notify tier: 5-min window, silence = GO. Use for major merges, system package installs, DNS, production deploys.

[[feedback-production-lock-retired]]
[[reference-so-20260504-consolidated]]
```

- [ ] **Step 2: Update MEMORY.md**

Read MEMORY.md first to find the right insertion point (under `## Wing Institutional Memory` section), then add this line:

```
- [**Hale Autonomy Expansion — 420 Scenarios (2026-06-19)**](project_hale_autonomy_expansion_20260619.md): Commander-confirmed authority map. d2mconcierge full auth. Weapons Free self-invoke. Inbound client = WF-17 no auto-ack. Gate holds in P0.
```

Insert it as the FIRST item under `## Wing Institutional Memory` since it's the most recent and most critical reference.

- [ ] **Step 3: Verify both files exist**

```bash
ls -la /home/john/.claude/projects/-home-john-Thunderbird/memory/project_hale_autonomy_expansion_20260619.md
grep "Hale Autonomy Expansion" /home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md
```

Expected: file exists, grep returns the line.

---

### Task 3: Log the Session Decision in hale_decisions.md

**Files:**
- Modify: `/home/john/Thunderbird/hale_decisions.md`

- [ ] **Step 1: Read the last entry in hale_decisions.md to find current format**

```bash
tail -20 /home/john/Thunderbird/hale_decisions.md
```

- [ ] **Step 2: Append the grilling session decision**

Append to `/home/john/Thunderbird/hale_decisions.md`:

```markdown

## 2026-06-19 — Autonomy Authority Expansion (420-Scenario Grilling)

**Decision:** Commander conducted comprehensive 420-scenario grilling to establish absolute authority ceiling for all 8 Hale instantiations.

**Outcome:** 
- 16 domains covered. Vast majority 🟢 AUTO.
- 10 precedents locked in Precedent Library (PL-001 through PL-010).
- Key expansions: d2mconcierge full authority; Weapons Free self-invocation; inbound client contact = WF-17 (no auto-ack); P0 gate holds absolutely.
- New SO: `standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md`
- Full map: `docs/superpowers/specs/2026-06-19-hale-autonomy-authority-map-design.md`

**Dissents logged:** None. Commander confirmed all ratings.

— V. Hale, VCS · 2026-06-19
```

- [ ] **Step 3: Commit memory + decision log**

```bash
cd /home/john/Thunderbird
git add hale_decisions.md
git commit -m "docs(hale): log 2026-06-19 autonomy expansion grilling session decision

— V. Hale, VCS

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 4: Commit memory files (separate repo)**

```bash
cd /home/john/.claude/projects/-home-john-Thunderbird/memory
# Memory files don't need git — they're loaded by the harness directly
# But verify both exist
ls project_hale_autonomy_expansion_20260619.md MEMORY.md
```

---

### Task 4: Verify All OODA/Auth Probe Files Committed

**Files:**
- Check: `OpsCenter/ai_auth_probe.py`
- Check: `deploy/ai-auth-probe.service`
- Check: `deploy/ai-auth-probe.timer`
- Check: `OpsCenter/agent_runner.py`
- Check: `OpsCenter/hale_incident_router.py`

These were written earlier this session. Verify they're committed.

- [ ] **Step 1: Check git status**

```bash
cd /home/john/Thunderbird
git status --short
```

Look for any M (modified) or ?? (untracked) entries on the above files.

- [ ] **Step 2: Stage and commit any uncommitted OODA files**

If any of the above files show as modified/untracked:

```bash
cd /home/john/Thunderbird
git add OpsCenter/ai_auth_probe.py \
        deploy/ai-auth-probe.service \
        deploy/ai-auth-probe.timer \
        OpsCenter/agent_runner.py \
        OpsCenter/hale_incident_router.py
git commit -m "feat(ooda): AI auth probe — 15-min active health checks + deterministic repair

Probes: Claude OAuth, OpenCode big-pickle, Telegram, MCP server.
Repair: deterministic (zero LLM dependency — bootstrapping trap avoided).
Escalation: enqueue_incident() → hale-incident-handler → Commander page.
Timer: ai-auth-probe.timer (every 15min). Deployed + active.
agent_runner.py: auth failures auto-enqueue to incident queue.
hale_incident_router.py: ai-auth-probe added to COMMANDER_GATE_SERVICES.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 3: Verify probe timer is still active**

```bash
systemctl --user status ai-auth-probe.timer --no-pager
```

Expected: `active (waiting)` with next trigger shown.

- [ ] **Step 4: Final git log — confirm all commits**

```bash
cd /home/john/Thunderbird
git log --oneline -8
```

Expected: See commits for auth probe + autonomy expansion artifacts.

---

## Self-Review

**Spec coverage check:**

| Spec Requirement | Task |
|-----------------|------|
| Standing Order for all 8 Hales | Task 1 |
| Authority Map spec (already written) | Pre-existing |
| Memory system pointer | Task 2 |
| MEMORY.md update | Task 2 |
| hale_decisions.md log | Task 3 |
| OODA/auth probe files committed | Task 4 |
| Timer verified active | Task 4 |

**Placeholder scan:** None found. All steps contain exact content.

**Type consistency:** No code types — all file content. N/A.

**Gaps:** None identified. All three artifacts from the grilling session are covered.
