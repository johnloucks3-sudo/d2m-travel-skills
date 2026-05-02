# CLAUDE CODE BRIEFING BOARD
**Cross-Domain Coordination Hub**  
*Last updated: 2026-05-01 15:05 MT*  
*Primary channel for Owner/COS decisions affecting Claude Code (Haiku 4.5)*

*Maintained by: COS (Hale) — run in OpenCode domain*

---

## HOW THIS WORKS

**COS posts decisions here.** Claude Code reads this file on startup. Claude Code confirms understanding by posting ACK timestamp below each decision.

**No ACK = decision has not reached Claude Code yet.**

---

## [DECISION-001] YSB BRIEFING PROTOCOL DEPLOYED

**Date:** 2026-05-01  
**Owner:** John Loucks  
**Urgency:** HIGH  
**Effective:** Immediately  

**Decision:** Replace military TSB with YSB (Yoda's Summary Brief). Two paths:
- **PATH A (Executive):** High-stakes decisions → Owner approval required, 4-hour SLA
- **PATH B (Tactical):** Real-time polling → No approval gate, 4-minute feedback loop

**Terminology change:** "Commander" → "Owner" in all briefs.

**File reference:** `/home/john/Thunderbird/OpsCenter/YSB_BRIEFING_PROTOCOL.md`

**Applies to:** All Claude Code-generated briefs, recommendations, decision summaries, client communications

**Claude Code ACK:** [ ] Pending  
**ACK timestamp:** —

**Note:** Claude Code must generate all future briefs using YSB format. Existing TSB references outdated as of this date.

---

## [DECISION-002] OWNER MEMO: TWO VIRTUAL DOMAINS

**Date:** 2026-05-01  
**Owner:** John Loucks  
**Urgency:** CRITICAL  
**Effective:** Immediately  

**Decision:** D2M now formally operates as two coordinated virtual domains:
- **Domain 1 (Claude Code):** Haiku 4.5 + Sonnet escalation
- **Domain 2 (OpenCode):** Gemini 3.1 Flash Lite + DeepSeek fallback

COS responsible for cross-domain coordination. Twin briefing boards (this one + OpenCode board) are primary communication channels.

**File reference:** `/home/john/Thunderbird/OpsCenter/OWNER_MEMO_TWO_DOMAINS_20260501.md`

**Applies to:** All operations. Claude Code must read this memo in full.

**Claude Code ACK:** [ ] Pending  
**ACK timestamp:** —

**Note:** This is organizational structure directive. Affects how Claude Code is tasked and reports outcomes.

---

## [DECISION-003] TOKEN TRACKING & TELEGRAM MONITORING LIVE

**Date:** 2026-04-30  
**Owner:** John Loucks  
**Urgency:** MEDIUM  
**Effective:** Immediately  

**Decision:** Token tracking and Telegram monitoring now integrated into hale_state_unified.json for both Claude Code and OpenCode.

**What changed:**
- All Claude Code dispatches logged to `hale_state_unified.json['token_tracking']['dispatch_log']`
- All Telegram commands/outcomes logged to `hale_state_unified.json['telegram']`
- Token costs calculated per dispatch (Claude pricing: Haiku $40/$120, Sonnet $300/$900 per 1M)
- Both platforms visible in unified state

**Files:**
- `/home/john/Thunderbird/OpsCenter/hale_token_tracker.py` (token tracking)
- `/home/john/Thunderbird/OpsCenter/hale_telegram_tracker.py` (Telegram tracking)
- `/home/john/Thunderbird/hale_state_unified.json` (unified state)

**Applies to:** Claude Code — all dispatches now tracked for cost/performance analytics

**Claude Code ACK:** [ ] Pending  
**ACK timestamp:** —

**Note:** Claude Code should call `track_dispatch()` on every task completion. See hale_token_tracker.py for integration pattern.

---

## [DECISION-004] BIMODAL BRIEFING ARCHITECTURE APPROVED (PENDING OWNER CONFIRMATION)

**Date:** 2026-05-01  
**Owner:** John Loucks (pending)  
**Urgency:** HIGH  
**Effective:** Pending approval  

**Decision:** Infrastructure improvements to client lifecycle operations via Bimodal Briefing:
- **PATH A (Executive):** Binding decisions (contracts, budgets, policy) → Approve/Disapprove flow, 4-hour SLA
- **PATH B (Tactical):** Tactical planning (flights, hotels, excursions, dining) → Interactive polling, real-time (minutes not hours)

**Benefit:** Eliminates approval bottleneck for low-stakes tactical decisions. Preserves accountability for high-stakes decisions.

**File reference:** `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md` (Friction-Velocity assessment)

**Applies to:** All client-facing operations and internal decision-making. Claude Code will manage PATH B polling UI and Owner interaction.

**Claude Code ACK:** [ ] Pending  
**ACK timestamp:** —

**Status:** Awaiting Owner explicit approval. Will be activated upon confirmation.

---

## [DECISION-005] CROSS-DOMAIN COORDINATION STANDING ORDER

**Date:** 2026-05-01  
**Owner:** John Loucks  
**Urgency:** CRITICAL  
**Effective:** Immediately  

**Decision:** All Owner and COS decisions affecting enterprise operations must be posted to BOTH briefing boards within 2 hours of decision, with explicit acknowledgment from both Claude Code and OpenCode required.

**COS responsibility:**
- Identify decisions that cross domains
- Post to THIS board (Claude) + OpenCode board (OpenCode) simultaneously
- Confirm both Claude + OpenCode ACKs before decision is "live" enterprise-wide

**Claude Code responsibility:**
- Read this briefing board on startup
- Acknowledge all decisions with timestamp
- Flag conflicts or ambiguities to Owner via email/Telegram
- Wait for OpenCode ACK before proceeding on cross-domain tasks

**File reference:** 
- This file: `/home/john/Thunderbird/OpsCenter/collaboration/claude_briefing_board.md`
- Twin file: `/home/john/Thunderbird/OpsCenter/collaboration/opencode_briefing_board.md`

**Applies to:** All future Owner/COS directives, protocol changes, priority shifts, budget changes, client updates, tool deployments

**Claude Code ACK:** [ ] Pending  
**ACK timestamp:** —

---

## PENDING OWNER CONFIRMATIONS

(Awaiting Owner approval to activate)

### [PENDING-A] BIMODAL BRIEFING IMPLEMENTATION ROADMAP

**Status:** Proposed, awaiting Owner decision  
**Decision pending:** Approve Bimodal Briefing PATH A + PATH B architecture?  
**Timeline proposed:** Week 1 (YSB generator migration), Week 2 (flight/hotel migration to PATH B), Week 3 (monitoring + metrics)  
**File reference:** `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md`

---

## ACTIVE CROSS-DOMAIN TASKS

(Tasks that involve both Claude Code and OpenCode)

**None currently logged.** Will update as COS assigns work spanning both domains.

---

## COMMUNICATION LOG

**2026-05-01 15:05 MT**
- Claude briefing board created (twin to OpenCode briefing board)
- 5 decisions posted
- Awaiting Claude Code first read + acknowledgment

---

## FORMAT FOR ACK

When Claude Code reads a decision, update as follows:

```markdown
**Claude Code ACK:** [x] Read and understood  
**ACK timestamp:** 2026-05-01 15:30 MT
```

If decision is unclear, reply in the decision section:
```markdown
**Claude Code ACK:** [x] Read — Question flagged  
**ACK timestamp:** 2026-05-01 15:30 MT  
**Question:** [Your question for COS]
```

If decision conflicts with OpenCode implementation, flag it:
```markdown
**Claude Code ACK:** [x] Read — Cross-domain issue  
**ACK timestamp:** 2026-05-01 15:30 MT  
**Issue:** [Description of conflict with OpenCode implementation]  
**Escalate to Owner:** Yes/No
```

---

## SYNC GATE: BOTH BOARDS MUST ALIGN

**Rule:** When a decision affects both domains, COS must post to BOTH boards with identical content. Then:

1. OpenCode reads OpenCode board → posts ACK
2. Claude Code reads Claude board → posts ACK
3. COS confirms both boards show ACKs
4. Only then is decision considered "live" across both domains

**Example workflow:**
```
Time: 2026-05-01 14:00
COS posts: "YSB BRIEFING PROTOCOL DEPLOYED" to BOTH boards

Time: 2026-05-01 14:15
OpenCode reads → posts ACK on OpenCode board
Claude Code reads → posts ACK on Claude board

Time: 2026-05-01 14:20
COS confirms: Both boards show ACKs → YSB protocol is NOW ACTIVE across enterprise
```

---

**This briefing board is the single source of truth for Claude Code domain coordination.**

COS updates (from OpenCode). Claude Code reads + ACKs. Owner escalates if needed.

---

*Director of Staff (COS): Post all Claude Code decisions here. Maintain sync with opencode_briefing_board.md.*  
*Claude Code (Haiku): Read this file on startup. Post ACK timestamp for each decision. Notify COS of conflicts.*
