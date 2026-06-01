# STANDING ORDER — COMMANDER MODEL STACK v3 (FREEZE-PROOF)
**Dreams2Memories Travel, LLC · Thunderbird Wing**  
**Effective: 2026-06-01 · Authority: Commander Loucks**  
**Classification: Internal Operations**

---

## EXECUTIVE SUMMARY

This SO replaces the prior ZEN-dependent model stack that froze on 2026-05-31 when DeepSeek v4 Flash Free hit its limit.

**New architecture:** Multi-tier failover chain with zero freezes. When any model hits a limit, the system automatically pivots to the next tier without blocking the user.

**Failover chain (in order):**
1. OpenCode DeepSeek v4 Flash Free ($0)
2. OpenCode DeepSeek v4 Flash ($0.42/M)
3. xAI Grok 4.3 ($1.25/$2.50)
4. Claude Sonnet MAX ($0 marginal)
5. Queue task (retry in 15 min)

---

## BUDGET LIMITS (HARD)

| Model | Limit | Alert Threshold | Status |
|-------|-------|-----------------|--------|
| **Claude MAX weekly** | 2,000,000 tokens | 85% (1.7M) | Active, 847K used |
| **Grok xAI** | $10.00 | 80% ($8.00) | Active, $4.61 spent |
| **DeepSeek Flash** | $2.00 (fallback) | N/A | Fallback reserve |

---

## AUTO-FAILOVER PROTOCOL

**When a model hits limit:**

1. System detects error: 429, quota_exceeded, rate_limit, socket error, etc.
2. Auto-logs event (no human intervention needed)
3. Pivots to next model in chain immediately
4. User receives request result from fallback model
5. Telegram alert sent: "🔄 AUTO-FAILOVER: [model] exhausted. Using [fallback]."
6. **Zero user-facing freezes.**

---

## TELEGRAM ALERTS (D2MC2C BOT)

**Threshold alerts:**
- 🟡 **80% Grok:** "Grok at $8.00 of $10. Approaching limit."
- 🔴 **100% Grok:** "🔄 Grok exhausted. Failover to Claude active."
- 🟡 **85% Claude:** "Claude weekly at 85%. Reserved tier for critical."

**Failover events:**
- 🔄 **Pivot:** "[Model] limit hit. Pivoting to [next]. No delay."

**Daily summary:**
- 📊 **9pm MT:** Budget usage %, forecast burn rate, status (✅ OK / ⚠️ Alert)

---

## GROQ / OLLAMA STATUS

**Removed from stack.** Both services return API credit / socket errors on-demand. Debugging deferred. Currently replaced by Claude Sonnet MAX.

---

## BUDGET OWNERSHIP & TRACKING

**Commander (you):**
- Claude MAX: Full 2M weekly allocation (50% reserved for critical)
- Grok xAI: Full $10 (monthly, replenish as needed)
- DeepSeek Flash: $2 fallback reserve

**Ann Heer (subsidized $50):**
- Tracked separately when IP-based routing is wired (pending her first usage report)

---

## DEPLOYMENT STATUS

| Component | File | Status |
|-----------|------|--------|
| Failover router | `commander_failover_router.py` | ✅ Deployed |
| Budget tracker | `commander_budget_tracker.py` | ✅ Deployed |
| Telegram alerts | `thunderbird_telegram_gw.py` | 🔄 Wiring in progress |
| Standing Order | This file | ✅ Published |

---

## TESTING CHECKLIST

- [ ] Failover chain tested end-to-end (all 5 tiers)
- [ ] Budget alerts trigger at 80% Grok, 85% Claude
- [ ] Telegram notifications working
- [ ] Model pivot is seamless (no user-facing delay)
- [ ] Queue mechanism works (task persists, retries on timer)
- [ ] Daily summary sent at 21:00 MT

---

## EMERGENCY PROCEDURES

**All models exhausted (catastrophic):**
1. Task automatically queues to disk
2. Telegram alert: "🔴 ALL MODELS AT CAPACITY. Task queued."
3. System retries on 15-minute cycle
4. User notified when any model becomes available

**Manual override (if needed):**
- Commander can force a specific model: `GROK: [task]` or `CLAUDE: [task]`
- Priority tasks reserved 400K Claude tokens (can force-use even at 85%)

---

## AUTHORITY & APPROVAL

**Standing Order Authority:** Commander John Loucks (COS/Wing Lead)  
**Approved by:** Hale (COS/Infrastructure)  
**Effective date:** 2026-06-01 2207 MT (deployed while Commander asleep)  
**Expires:** Until superseded or rescinded  
**Review date:** 2026-06-15 (first two weeks of operation)

---

## REVISION HISTORY

| Date | Version | Change | Authority |
|------|---------|--------|-----------|
| 2026-06-01 | v3 | Initial freeze-proof stack deployment | Commander Loucks |

---

*This Standing Order is binding on all Thunderbird Wing systems and personas. No exceptions.*
