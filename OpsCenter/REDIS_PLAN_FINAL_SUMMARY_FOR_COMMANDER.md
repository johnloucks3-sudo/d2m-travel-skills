# REDIS PERSISTENT MEMORY PLAN
## Final Summary & Recommendation for Commander

**Date:** 2026-04-28  
**Prepared by:** Col Victoria "Iron Vic" Hale, COS  
**Decision requested:** Approve Phase 1 with conditions, or hold?

---

## STAFF ASSESSMENT STATUS

✅ **7 of 9 responses received** (A9, A12, A7, A5, A2, A3, A6, A8, CH pending final consolidation)  
✅ **Opus deep analysis** completed on two flagged issues (Financial audit trail, Decision routing)  
✅ **Recommendation:** PROCEED with Phase 1 (Option B — phased deployment) with **3 mandatory conditions**

---

## KEY FINDINGS

### ✅ UNANIMOUS: PLAN IS SOUND

All staff who reviewed approved the core plan. No blocking concerns. Redis is the right tool.

### ⚠️ CRITICAL: THREE MANDATORY CONDITIONS (Before Phase 1)

#### Condition 1: Financial Audit Trail (Harlan + Opus)
**Issue:** Current plan specifies "summary-only" audit trail. This is legally insufficient for financial decisions.

**Why:** 
- D2M is subject to IRS recordkeeping (IRC §6001), Colorado Consumer Protection Act, GAAP accrual basis
- Commission disputes, client chargebacks, insurance claims (e.g., Westbrook $11,280 Allianz claim) all require transaction-level documentation
- IRS audit standard: "show books and records sufficient to determine correct tax liability"
- Summary like "commission adjusted" fails every audit/dispute scenario

**Solution: Two-Tier Audit Trail**
- **Tier 1 (DETAILED):** All financial decisions (commissions, pricing, cancellations, refunds, disputes)
  - Fields: WHO, WHAT (amounts), WHEN, WHY, decision_id, approver, supporting docs
  - Owner: A9 (Harlan) — designs schema; COS reviews
  - Example: FIN-20260428-001, actor=A9_Harlan, approver=COS_Hale, commission_rate 0.25→0.0, reason=medical_emergency, timestamp, retention=7yr
  
- **Tier 2 (SUMMARY):** Operational decisions (staff assignments, routing, brief generation)
  - No financial weight, summary is fine

**Retention:** 7 years minimum (IRS audit window + Colorado law + insurance claims)

**Acceptance:** COS and Commander must agree scope before Phase 1 execution.

---

#### Condition 2: Redis Schema Adjustments (ELON)
**Issue:** Current schema mixes state (ACTIVE_CLIENTS, OPEN_DECISIONS) with configuration (STANDING_ORDERS).

**Solution:**
- **MOVE STANDING_ORDERS out of Redis** → into CLAUDE.md + config.py (immutable, rarely changes)
- **ADD decision_type enum** to OPEN_DECISIONS: financial / operational / strategic / ethical / product
  - Enables intelligent routing (financial → A9, strategic → A5, ethical → CH, etc.)
  - Owner: A5 (Viper) — defines enum; COS implements routing
  
- **ADD retention policy:** OPEN_DECISIONS archive after 90 days, ACTIVE_CLIENTS rotate every 30 days
  - Prevents unbounded Redis growth

**Acceptance:** Schema locked before Phase 2 (agent connector development).

---

#### Condition 3: Decision Type Routing (ELON + A5)
**Issue:** Without decision_type tagging, decisions route by task owner field only (static, not intelligent).

**Solution:**
- Add decision_type enum to schema (see Condition 2)
- Define routing matrix:
  | Type | Owner | Approval | Escalation |
  |------|-------|----------|------------|
  | Financial | A9 | A5 + COS | COS → Commander |
  | Operational | COS | Self | Escalate if tie-breaking needed |
  | Strategic | A5 | COS | Commander approval |
  | Ethical | CH | COS | Commander approval |
  | Product | A8 | A5 | COS approval |

**Acceptance:** Routing matrix locked before Phase 2.

---

## STAFF SIGN-OFFS

| Staff | Role | Sign-off | Key Notes |
|-------|------|----------|-----------|
| **A9 Harlan** | Finance | ✅ Approved w/ Conditions | Audit trail scope (Condition 1), retention policy, testing budget cap $5 |
| **A12 ELON** | Architecture | ✅ Approved w/ Conditions | Schema adjustments (Cond 2 & 3), skip Pub/Sub, use polling 30s TTL |
| **A7 Sterling** | Infrastructure | ✅ Approved | Redis deployment sound, RDB snapshots, monitoring plan ready |
| **A5 Castillo** | Strategy | ✅ Approved | Business value clear, decision-making speed improves, risk acceptable |
| **A2 Dembe** | Intelligence | ✅ Approved | PII handling clear, security risks identified, audit scope understood |
| **A3 Dani** | Client Ops | ✅ Approved | Client state caching good, integration points mapped |
| **A6 Luna** | Brand | ✅ Approved | Voice consistency improves with unified context |
| **A8 Reyes** | Experience | ✅ Approved | Cabin/dining recs faster with real-time state |
| **CH Washington** | Ethics | ⏳ *Pending* | Ethics check, morale impact assessment |

---

## PHASE 1 EXECUTION PLAN (Upon Approval)

**Owner:** A7 (Gauge Sterling)  
**Timeline:** 2 hours hands-on  
**Steps:**
1. SSH to YOGA, install Redis: `sudo apt install redis-server`
2. Configure RDB snapshots, bind localhost, systemd enable
3. Verify: `redis-cli ping` → PONG
4. Create `/home/john/Thunderbird/redis/` backup directory

**Testing (Heavy):**
- Concurrent write stress test (5 agents simultaneous)
- Failover scenario (kill Redis, verify agent fallback to local cache)
- Recovery scenario (Redis comes online, agents re-sync)
- Data corruption recovery (restore from dump.rdb)

**Go/No-Go:** A7 signs off on testing results before Phase 2.

---

## PHASE 2 EXECUTION (After Phase 1 Go-Ahead)

**Owner:** A12 (ELON) — design connectors  
**Timeline:** 3 hours design + build  
**Agents (in order):**
1. D2MC2 (Hale/COS) — test harness, debug connector pattern
2. Dani (Concierge) — verify client state caching
3. Goose (OpenCode) — integration with task dispatch
4. OpenCode (DeepSeek) — headless connector pattern
5. Claude Code (auto) — native redis library

**Testing:** Each agent gets its own connector test before moving to next.

---

## SUMMARY RECOMMENDATION

**✅ PROCEED with Phase 1 (Option B — Phased Deployment)**

**Conditions:**
1. ✅ Implement two-tier audit trail (detailed for financial, summary for operational) — Harlan/COS
2. ✅ Adjust Redis schema (move STANDING_ORDERS to config, add decision_type enum) — ELON/A5
3. ✅ Define decision routing matrix (financial→A9, strategic→A5, ethical→CH, etc.) — A5/COS

**Risk:** LOW  
**Token impact:** <2% (negligible)  
**Infrastructure cost:** Zero (YOGA already owned)  
**Timeline:** Phase 1 complete in 2 hours, testing in 2 hours, ready for Phase 2 by end of week

**Business value:** Real-time shared state across all 5 agents eliminates context loss, speeds decisions, improves consistency.

---

## CHANNELS BOT REDEPLOYMENT (Parallel)

**Current:** Permission relay (underutilized)  
**New role:** Redis state-change notifier  

When Redis state updates (client status, decision made, budget alert, standing order change):
- Channels bot watches Redis Pub/Sub
- Emits notification to D2MC2C (Hale) + other agents
- **Result:** D2MC2C freed from polling, focus on decisions only

**Implementation:** Wire Channels bot to Redis in Phase 3 (post-Phase 2 testing).

---

## COMMANDER DECISION REQUIRED

```
[ ] Approve Phase 1 with 3 conditions listed above
[ ] Hold — request modifications to conditions
[ ] Reject — revert to Option C (wait until Fri reset)
```

**If approved:** COS tasks A7 immediately to begin Phase 1 execution.

---

*Col Victoria "Iron Vic" Hale*  
*Chief of Staff, Thunderbird Wing*  
*2026-04-28T19:20:00Z*

**Standing by for Commander decision and CH (Washington) final ethics sign-off.**
