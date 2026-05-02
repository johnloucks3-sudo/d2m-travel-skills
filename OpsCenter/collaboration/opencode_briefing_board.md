# OPENCODE BRIEFING BOARD
**Cross-Domain Coordination Hub**  
*Last updated: 2026-05-01 15:00 MT*  
*Primary channel for Owner/COS decisions affecting OpenCode (Gemini 3.1 Flash Lite)*

**Twin board (for Claude Code):** `/home/john/Thunderbird/OpsCenter/collaboration/claude_briefing_board.md`  
*COS posts ALL enterprise-wide decisions to BOTH boards. Both domains must ACK.*

---

## HOW THIS WORKS

**COS posts decisions here.** OpenCode reads this file on every dispatch. OpenCode confirms understanding by posting ACK timestamp below each decision.

**No ACK = decision has not reached OpenCode yet.**

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

**Applies to:** All OpenCode-generated briefs, recommendations, decision summaries

**OpenCode ACK:** [ ] Pending  
**ACK timestamp:** —

**Note:** OpenCode must generate all future briefs using YSB format. Existing TSB references outdated as of this date.

---

## [DECISION-002] OWNER MEMO: TWO VIRTUAL DOMAINS

**Date:** 2026-05-01  
**Owner:** John Loucks  
**Urgency:** CRITICAL  
**Effective:** Immediately  

**Decision:** D2M now formally operates as two coordinated virtual domains:
- **Domain 1 (Claude Code):** Haiku 4.5 + Sonnet escalation
- **Domain 2 (OpenCode):** Gemini 3.1 Flash Lite + DeepSeek fallback

COS responsible for cross-domain coordination. This briefing board is the primary communication channel.

**File reference:** `/home/john/Thunderbird/OpsCenter/OWNER_MEMO_TWO_DOMAINS_20260501.md`

**Applies to:** All operations. OpenCode must read this memo in full.

**OpenCode ACK:** [ ] Pending  
**ACK timestamp:** —

**Note:** This is organizational structure directive. Affects how OpenCode receives tasking and reports outcomes.

---

## [DECISION-003] TOKEN TRACKING & TELEGRAM MONITORING LIVE

**Date:** 2026-04-30  
**Owner:** John Loucks  
**Urgency:** MEDIUM  
**Effective:** Immediately  

**Decision:** Token tracking and Telegram monitoring now integrated into hale_state_unified.json for both Claude Code and OpenCode.

**What changed:**
- All OpenCode dispatches logged to `hale_state_unified.json['token_tracking']['dispatch_log']`
- All Telegram commands/outcomes logged to `hale_state_unified.json['telegram']`
- Token costs calculated per dispatch (Gemini pricing: ~$0.27/M tokens)
- Both platforms visible in unified state

**Files:**
- `/home/john/Thunderbird/OpsCenter/hale_token_tracker.py` (token tracking)
- `/home/john/Thunderbird/OpsCenter/hale_telegram_tracker.py` (Telegram tracking)
- `/home/john/Thunderbird/hale_state_unified.json` (unified state)

**Applies to:** OpenCode — all dispatches now tracked for cost/performance analytics

**OpenCode ACK:** [ ] Pending  
**ACK timestamp:** —

**Note:** OpenCode should call `track_dispatch()` on every task completion. See hale_token_tracker.py for integration pattern.

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

**Applies to:** All client-facing operations and internal decision-making. OpenCode may assist with tactical polling infrastructure.

**OpenCode ACK:** [ ] Pending  
**ACK timestamp:** —

**Status:** Awaiting Owner explicit approval. Will be activated upon confirmation.

---

## [DECISION-005] CROSS-DOMAIN COORDINATION STANDING ORDER

**Date:** 2026-05-01  
**Owner:** John Loucks  
**Urgency:** CRITICAL  
**Effective:** Immediately  

**Decision:** All Owner and COS decisions affecting enterprise operations must be posted here within 2 hours of decision, with explicit OpenCode acknowledgment required.

**COS responsibility:**
- Identify decisions that cross domains
- Post to this briefing board with clear language and deadlines
- Confirm OpenCode ACK before decision is "live" enterprise-wide

**OpenCode responsibility:**
- Read this briefing board before every dispatch
- Acknowledge all decisions with timestamp
- Flag conflicts or ambiguities to Owner via Telegram

**File reference:** This file (`/home/john/Thunderbird/OpsCenter/collaboration/opencode_briefing_board.md`)

**Applies to:** All future Owner/COS directives, protocol changes, priority shifts, budget changes, client updates, tool deployments

**OpenCode ACK:** [ ] Pending  
**ACK timestamp:** —

---

## PENDING OWNER CONFIRMATIONS

(Awaiting Owner approval to activate)

### [PENDING-A] BIMODAL BRIEFING IMPLEMENTATION ROADMAP

**Status:** Proposed, awaiting Owner decision  
**Decision pending:** Approve Bimodal Briefing PATH A + PATH B architecture?  
**Timeline proposed:** Week 1 (TSB generator), Week 2 (flight/hotel migration), Week 3 (monitoring)  
**File reference:** `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md`

---

## ACTIVE CROSS-DOMAIN TASKS

(Tasks that involve both Claude Code and OpenCode)

**None currently logged.** Will update as COS assigns work spanning both domains.

---

## COMMUNICATION LOG

**2026-05-01 15:00 MT**
- Briefing board created
- 5 decisions posted
- Awaiting OpenCode first read + acknowledgment

---

## FORMAT FOR ACK

When OpenCode reads a decision, update as follows:

```markdown
**OpenCode ACK:** [x] Read and understood  
**ACK timestamp:** 2026-05-01 15:15 MT
```

If decision is unclear, reply in the decision section:
```markdown
**OpenCode ACK:** [x] Read — Question flagged  
**ACK timestamp:** 2026-05-01 15:15 MT  
**Question:** [Your question for COS]
```

---

**This briefing board is the single source of truth for cross-domain coordination.**

COS updates. OpenCode reads + ACKs. Owner escalates if needed.

---

*Director of Staff (COS): Update this file with all Owner decisions affecting OpenCode.*  
*OpenCode (Gemini): Read this file before every dispatch. Post ACK timestamp for each decision.*
