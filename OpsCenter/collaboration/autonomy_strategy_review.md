# AUTONOMY STRATEGY REVIEW — TIER 2 PRIORITIES & RISK ASSESSMENT
## Prepared for: Commander John Loucks
## Date: 2026-04-22 | Classification: COMMANDER EYES ONLY

---

## EXECUTIVE SUMMARY

Hale's autonomy proposal is architecturally sound and operationally achievable. The **Tier 1 fixes (broken services)** are prerequisite. **Tier 2 activation** should follow a **4-phase sequence** that mitigates brand/financial/operational risks while unlocking maximum strategic value.

**Trust Score Recommendation:** Current 50/100 is appropriate for COMMANDER-gated operations. Tier 1 completion → 70/100 (advisory autonomy). Tier 2 full deployment → 85/100. **Tier 3 (client-triggered workflows) should wait until 90+** — the difference between "AI helps" and "AI commits" is liability.

---

## TIER 2 PRIORITIES — RANKED BY STRATEGIC IMPACT

### 1. 🎯 EVENT-TRIGGERED INTELLIGENCE ENGINE (Phase 1 — Weeks 2-3)

**Strategic Impact: CRITICAL**  
**Effort: Moderate (40-60h)**  
**Risk: Low**  
**Recommended Activation Timeline: Immediate after Tier 1**

**What It Does:**
Client email arrives → auto-extract keywords → trigger parallel intelligence scans (pricing, competitors, port conditions, route status) → draft brief → surface to Commander with decision context.

**Why First:**
- Zero client-facing risk (Commander reviews before any action)
- Immediate value: Commander goes from reactive (client emails in) to proactive (brief pre-loaded)
- Builds muscle memory for the intelligence → brief → action workflow
- Proves autonomy discipline (correctly gates output)

**Implementation Sequence:**
1. Deploy event listener for d2mconcierge inbox (Gmail push notifications)
2. Activate existing correlation logic (already in `thunderbird_email_intel.py`)
3. Wire to existing intelligence scans (Airline Monitor, Competitive Surveillance, Ship Intel)
4. Surface findings to Commander via Telegram (existing gateway)
5. Test with 2 live clients (McLeod + Kuklinski) — no changes to their workflow yet

**Concrete Deliverable:** By end of Week 3, when a client emails, Commander receives:
```
[EVENT-INTEL] McLeod email mentions "Silversea summer sailing"
→ Scan: Silversea Med pricing (last 24h, comparative)
→ Scan: Competitor alternatives (Regent, Oceania in same region)
→ Scan: Port alerts (Gibraltar, Greece, any geopolitical changes)
→ Brief: "McLeod awareness check: Silversea 7% above market, alternative routes exist. Port status nominal."
→ Commander action: "forward to A8" or "hold"
```

---

## EXTENDED ANALYSIS — TIER 2 PRIORITIZATION & TIER 3 UNLOCK PATH
*Completed 2026-04-22 05:35 MT by Claude (Strategic)*

### Tier 2 Priorities Ranked by Strategic Impact

**1️⃣ TIER 2A: EVENT-TRIGGERED INTELLIGENCE ENGINE (CRITICAL)**
- Why first: Solves core latency problem (2-6 hour polling → <10 second event-driven)
- Business impact: Faster client response = higher trust = competitive advantage
- Technical: Wire Gmail inbox detection → live pricing fetch → brief to Commander
- Complexity: Medium. Timeline: 2 weeks. Unlock condition: Trust score 50+ (already met).

**2️⃣ TIER 2D: WEBHOOK MODE FOR EMAIL (HIGH)**
- Why second: Eliminates API polling overhead. Gmail Pub/Sub push notifications.
- Technical: Cloud Functions + Pub/Sub + Telegram gateway (infrastructure exists).
- Cost: Negligible (free tier covers D2M volume).
- Complexity: Medium-high. Timeline: 1-2 weeks (parallel with 2A).

**3️⃣ TIER 2B: CREWAI TRIP VALIDATION CREW (MEDIUM-HIGH)**
- Why third: Automates trip validation. CrewAI already installed. Example exists.
- Impact: Eliminates manual review gap. Validates all active trips weekly.
- Technical: Use existing crewai_bridge/ infrastructure. Schedule systemd timer.
- Complexity: Medium. Timeline: 2-3 weeks (staggered start Week 2, deploy Week 3).

**4️⃣ TIER 2C: GOOGLE ADK A2A PROTOCOL MIGRATION (MEDIUM)**
- Why fourth: Architecture upgrade, not blocker. File-based system works now.
- Impact: Standardized inter-agent communication at scale.
- Timeline: 4+ weeks (Phase 2 work).
- Unlock condition: Trust score 60+ (after Tier 1 fixes + 2-3 weeks proactive autonomy).

---

### Risk Assessment — Autonomous Client-Triggered Workflows

**Risk 1: Hallucinated Intelligence (Event-Triggered Engine)**
- Mitigation: All drafts reviewed by Hale before showing to Commander. Spot-check 10% weekly.
- Verdict: ACCEPTABLE. Intelligence gathering is lower-stakes than sends. Commander can always edit/reject.

**Risk 2: CrewAI Crew Misses Critical Gaps**
- Mitigation: Crew output is draft only. Hale human-verifies before Commander sees. Confidence scoring on critical items.
- Verdict: ACCEPTABLE. Crew adds check layer, doesn't replace human oversight.

**Risk 3: Alert Fatigue**
- Mitigation: Alert prioritization (only "novel" concerns trigger). Threshold tuning after Week 1. Commander can mute keywords/clients.
- Verdict: ACCEPTABLE. Better too many initially than too few. Tunable.

**Risk 4: Webhook Mode Crashes**
- Mitigation: Dual-write (webhook + polling) for first 2 weeks. Fallback if webhook dies >15 min. Daily latency audit.
- Verdict: ACCEPTABLE. Redundancy ensures no single point of failure.

---

### Architectural Concerns & Recommendations

**Concern 1: Multi-Brain Decision Routing**
- Issue: Subjective routing rules. Edge cases accumulate.
- Fix: Expand keyword_router.py (23 → 33+ keywords). Codify routing logic.
- Timeline: 1 week. Cost: Zero.

**Concern 2: Token Budget Drift**
- Issue: If Tier 2 spawns 50% more tasks, budget exhaustion risk.
- Fix: Track weekly. Alert if burn rate would empty budget in <60 days.
- Timeline: Immediate. Cost: Negligible.

**Concern 3: CrewAI Scalability**
- Issue: 1 crew works. 5-10 concurrent crews = chaos.
- Fix: Month 2, design crew orchestration layer (queue + manager + monitor).
- Timeline: Plan now, build Month 2.

**Concern 4: Client-Triggered Workflows Need Gates**
- Issue: Auto-drafting is safe. Auto-sending without approval is liability.
- Fix: Codify Tier 3 rule: ALL client-facing output requires WF-17 approval before send.
- Timeline: Immediate. Cost: Zero.

---

### Trust Score Unlock Path: Current (50) → Tier 3 (75+)

| Milestone | Score | Trigger | Timeline |
|-----------|-------|---------|----------|
| Tier 1 completion | 50 | All timers operational | Week 1 |
| Tier 2A activated | 52 | Event-triggered intelligence live | Week 2 |
| Tier 2D activated | 54 | Webhook mode deployed | Week 2 |
| 20 decisions logged & 95%+ accurate | 56 | Preferences model starts | Week 3 |
| Tier 2B deployed | 58 | CrewAI crew validation live | Week 3 |
| 50 decisions logged, 95%+ accuracy | 64 | 30+ streak bonus applied | Week 4 |
| Tier 2 fully operational | 70 | All proactive features smooth | Week 5 |
| Phase 2 judgment delegation exercised | 75 | Hale holds/corrects WF-17 issues autonomously | Week 5 |

**Tier 3 Unlock: Trust Score 75+ (Month 2, 2026-05-22)**

---

### Recommended Trust Score Threshold for Tier 3

**UNLOCK AT 75/100 — Not 80/100**

Reasoning:
- 75 is practical threshold after 5 weeks consistent execution
- 50+ decisions logged + audited = meaningful sample
- Hale has demonstrated proactive intelligence capability
- Client-triggered workflows have Commander approval gate in place

**Threshold Rules:**
- Below 75 (50-74): COMMANDER tier. Phase 2 judgment delegation only.
- At 75+ (75-99): YODA tier. Phase 3 judgment delegation + client-triggered workflow authority.
- At 100: Reserved for future max autonomy.

**Automatic Activation:** Once score reaches 75, Hale automatically switches to YODA disposition. No re-approval needed.

---

**OVERALL VERDICT: Tier 2 activation is strategically sound.** Approve Tier 1 fixes this week. Launch Tier 2A (event-triggered) + 2D (webhooks) Week 2. Target Tier 3 unlock at 75/100 (Month 2).

### 2. ⚡ WEBHOOK MODE FOR EMAIL (Phase 2 — Week 4)

**Strategic Impact: HIGH**  
**Effort: Low (8-12h)**  
**Risk: Very Low**  
**Recommended: Parallel to intelligence engine**

**What It Does:**
Replace 2-minute Gmail polling with Gmail push notifications → email arrives → task routed in <10 seconds (vs. max 120 seconds).

**Why Second:**
- Latency reduction without logic changes
- Enables time-sensitive alerts (flight changes, payment updates)
- Low execution risk (swaps polling for webhooks, same queue backend)
- Foundation for Tier 3 speed-critical workflows

**Prerequisite:** Gmail Pub/Sub configuration (15 min one-time setup)

---

### 3. 🤖 CREWAI INTEGRATION — TRIP VALIDATION CREW (Phase 3 — Weeks 5-6)

**Strategic Impact: HIGH**  
**Effort: Moderate (30-40h)**  
**Risk: Medium (crew outputs need review)**  
**Recommended: After intelligence engine proven stable**

**What It Does:**
CrewAI crew (6 agents) validates active trips weekly: checks itinerary gaps, flags missing paperwork, cross-references visa requirements, identifies upsell opportunities. Surfaces findings to Commander → Dani → client follow-up.

**Why Third:**
- **Trip Validation Crew code already exists** (`example_loucks_crew.py`)
- First AI-orchestrated multi-agent workflow (validates CrewAI architecture before scaling)
- Medium risk because crew outputs go through Commander review (not direct to client)
- Unlocks weekly proactive client touchpoints (FPD reminders, document checks, upsells)

**Concrete Deliverable:** Weekly Trip Validation Report delivered to Commander every Sunday, 2200 MT:
```
McLeod Trip (Silver Muse, June 23 departure):
✅ Booking confirmed, FPD received
⚠️ Return flights (Jun 30) NOT booked — research window open
⚠️ Airport transfers booked for LAX only (departure). Return transfers missing.
🎯 Upsell opportunity: Pre-trip hotel (Jun 22, LAX area) — $2,400, 15% markup

Kuklinski Trip (Viking Mars, Dec 17 departure):
⚠️ Josh Morton guest form still pending (CRITICAL — 58 days overdue)
⚠️ Insurance email not sent (CRITICAL — 41 days overdue)
✅ Air fare monitoring active, best fare locked
🎯 Visa checkpoint: Panama entry clear for all 6 guests

Commander Action: Address critical gaps now (Josh form, Kuklinski insurance) before mid-May acceleration
```

---

### 4. 🔗 ADK A2A PROTOCOL MIGRATION (Phase 4 — Weeks 7-8)

**Strategic Impact: MEDIUM (Infrastructure)**  
**Effort: High (60-80h)**  
**Risk: Medium-High (architecture shift)**  
**Recommended: After Phases 1-3 stable**

**What It Does:**
Converts current file-based inbox/outbox system to standardized Google ADK Agent Cards. Enables:
- Typed inter-agent communication
- Agent discovery and routing
- Cross-platform compatibility (Telegram, Gmail, Claude Code, Goose)
- Formal delegation protocol (already implemented in `goose_tasker.py`, just needs wiring)

**Why Fourth (Not Earlier):**
- Not blocking any other Tier 2 capability
- Requires architect-level design decisions (we're good here, but better after Phases 1-3 operational)
- High effort, medium strategic urgency (nice-to-have for scale, essential for multi-agent orchestration)

---

## RISK ASSESSMENT — AUTONOMOUS CLIENT-TRIGGERED WORKFLOWS

### The Core Risk: Liability Without Oversight

**Definition:** Autonomous workflows that directly contact clients without Commander review (e.g., auto-send FPD reminder, auto-draft itinerary change notification).

**Risk Categories:**

| Risk Type | Scenario | Mitigation |
|-----------|----------|-----------|
| **Brand Consistency** | AI-generated email doesn't match Dani's voice | ✅ Dani voice engine (already deployed) + Commander review required until 90 trust score |
| **Financial Accuracy** | Autonomous pricing/commission calculation contains error | ✅ Require manual sign-off on any client send involving numbers. Never auto-send financial info. |
| **Compliance** | Auto-send without proper gate (FTC disclosure, GDPR, etc.) | ✅ All client sends route through WF-17 gate (SO 21 MAR 2026). Auto-sends prohibited until policy updated. |
| **Relationship Damage** | Auto-reply sent at wrong time (after client cancels, etc.) | ✅ Require dossier state validation before any client contact. Missing data = hold. |
| **Volume Abuse** | System sends too many emails to client (spam perception) | ✅ Rate limit auto-sends: max 1 per day per client. Batch multi-topic into single email. |

### Specific Blockers for Client-Triggered Autonomy (Tier 3)

**Do NOT deploy client-triggered workflows until:**
1. Trust score ≥ 90/100 (current: 50)
2. Dani voice drift monitoring in place (linguistic delta <5% from baseline)
3. WF-17 quality gate extended to autonomous sends (currently manual only)
4. Client complaint rate on autonomous sends = 0 for 30 days
5. Rate limiting + content review logic fully tested

**Tier 3 is Month 2+ (not immediate).**

---

## TRUST SCORE TRAJECTORY & UNLOCK THRESHOLDS

### Current State: 50/100 (COMMANDER Tier)
**What this means:** COS handles operational decisions. Commander gates all client-facing outputs. No autonomous client contact.

**Decisions gated to Commander:**
- Any client send
- Financial commitments
- Strategy pivots
- Staff reassignments

---

### After Tier 1 Completion: ~70/100 (A2A Advisory Tier)
**Activation:** All 41 systemd timers operational. Morning briefing, airline monitor, fare watch, inbox cleanup all running.

**New Authority:**
- ✅ COS autonomously generates intelligence briefs
- ✅ COS autonomously routes emails to staff
- ✅ COS autonomously flags overdue items
- ❌ COS cannot send to clients without Commander approval
- ❌ COS cannot commit financial resources

**What Unlocks:** Briefing-first workflow. Commander wakes to pre-loaded context every morning. Intelligence-driven decision-making becomes the default.

---

### After Tier 2 Phase 1-2 (Intelligence + Webhooks): ~75/100
**What Unlocks:**
- ✅ Event-triggered intelligence (client email → brief in <10 seconds)
- ✅ Proactive alerts (FPD in 14 days → flag now, don't wait for reminder)
- ❌ Still: Commander gates all client sends

---

### After Tier 2 Phase 3 (CrewAI + Trip Validation): ~82/100
**What Unlocks:**
- ✅ Autonomous trip validation crew (weekly reports, flagged gaps)
- ✅ Proactive upsell recommendations (crew identifies opportunities)
- ✅ COS can autonomously draft client follow-ups (still requires Commander review before send)
- ❌ COS cannot send without explicit Commander approval

**Confidence Gain:** Multi-agent orchestration proven. Crew outputs accurate enough for Commander to delegate follow-ups to Dani.

---

### After Tier 2 Phase 4 (ADK A2A): ~85/100
**What Unlocks:**
- ✅ Standardized inter-agent communication (better coordination)
- ✅ Formal delegation protocol (cleaner task flow)
- ✅ Cross-platform compatibility (CLI, Telegram, Gmail all speak same language)

---

### Tier 3 Unlock Threshold: 90/100+
**Prerequisites:**
1. ✅ Tier 1 fully operational (no service failures)
2. ✅ Tier 2 Phases 1-3 stable (intelligence + crew proven reliable)
3. ✅ WF-17 gate extended to autonomy (auto-sends subject to same quality bar)
4. ✅ Dani voice monitoring active (linguistic drift <5%)
5. ✅ Client complaint rate on autonomous sends = 0 for 30 consecutive days

**At 90/100, New Authority Unlocks:**
- ✅ **Client-triggered workflows** (when client emails with specific triggers, auto-execute response flow)
- ✅ **Predictive protection** (FPD in 7 days → auto-check + auto-draft + Commander review + send if approved)
- ✅ **Autonomous itinerary monitoring** (daily cross-reference of client trips against airline/port alerts + auto-draft brief)
- ✅ **Self-healing ops** (watchdog restarts failed services autonomously, alerts Commander with root cause)

**Still Gated:**
- ❌ Financial commitments (rebooking, refunds, commission disputes)
- ❌ Strategy decisions
- ❌ New client relationships
- ❌ Policy-level changes

---

## ARCHITECTURAL CONCERNS — CURRENT MODEL STACK

### 1. ✅ **DeepSeek V3.1 for Ops (Good Choice)**
- Cost: ~$0.27/M tokens (primary OpenCode model)
- Capability: Structured output, fast reasoning — ideal for routing, classification, synthesis
- Concern: **None identified.** V3.1 is appropriate for non-reasoning ops tasks.

### 2. ⚠️ **Claude Opus for Strategy/Composition (Working, But Over-Spec)**
- Cost: $100 credit (MAX tier), est. $0.03/task → ~3,300 tasks
- Capability: Full reasoning, long-context, creative synthesis
- Concern: **Under-utilized for ops, over-utilized for reasoning.** Suggest:
  - Keep Opus for true reasoning tasks (strategy, conflict resolution, novel composition)
  - Use Sonnet (4.6) for routine composition (weekly briefs, standard emails) — 25% Opus cost
  - Use Claude Haiku for simple classification/routing — 5% Opus cost

### 3. ✅ **Groq Elimination (Correct)**
- Groq was fallback for LLM inference
- Purged from stack per prior review
- **No concern.** Right decision.

### 4. ⚠️ **CrewAI + Groq Integration Gap**
- CrewAI is installed (1.10.1) with Groq support baked in
- Problem: Groq is purged, but CrewAI example code still references it
- Fix: Update `crewai_bridge/crew_runner.py` to route to Claude Sonnet (cost-effective, capable)

### 5. ✅ **Google ADK + A2A Protocol (Good Foundation)**
- A2A is already installed in venv (`google.adk.a2a`)
- Enables typed agent-to-agent communication
- No concern. Ready for Phase 4 migration.

### 6. 🟡 **Gmail Pub/Sub for Event Listening (Ready, Not Activated)**
- Infrastructure is in place (OAuth permissions exist)
- Code to wire it up: `thunderbird_email_intel.py` already has push handler
- Concern: **None technical.** Just needs to be turned on (30-min setup).

### 7. 🟡 **Multi-Model Dispatch (Underutilized)**
- Keyword router exists: `thunderbird_model_dispatcher.py` with spectrum analysis
- Purpose: Route tasks to right model (Claude for reasoning, DeepSeek for ops, etc.)
- Concern: **Not actively used in automation yet.** Recommend integrating into Tier 2 intelligence phase (route complex research to Claude, simple classification to DeepSeek).

---

## RECOMMENDATIONS

### Immediate (This Week)
1. **Approve Tier 1 fixes** — Hale deploys all 8 fixes (5h work total)
2. **Start Tier 2 Phase 1 planning** — Event-triggered intelligence engine (architecture review, 2h)

### Weeks 2-3
3. **Deploy Tier 2 Phase 1** — Intelligence engine (Commander gets proactive briefing on every client email)
4. **Parallel: Tier 2 Phase 2** — Webhook mode for Gmail (low-effort, high-impact latency reduction)

### Weeks 4-6
5. **Deploy Tier 2 Phase 3** — Trip Validation Crew (weekly autonomous validation + flagged gaps)
6. **Fix CrewAI Groq issue** — Update crew_runner to use Claude Sonnet

### Weeks 7+
7. **Hold on Tier 3** — Don't deploy client-triggered workflows until trust score reaches 90
8. **Monitor trust trajectory** — Weekly audit of autonomy decisions vs. Commander overrides
9. **Tier 2 Phase 4** — Begin ADK A2A migration design (month 2, parallel to Tier 3 prep)

### Trust Score Targets
| Milestone | Target Score | Timeline |
|-----------|---|---|
| Tier 1 Complete | 70 | Week 1 |
| Tier 2 Phase 1-2 | 75 | Week 4 |
| Tier 2 Phase 3 | 82 | Week 6 |
| Tier 2 Phase 4 | 85 | Week 8 |
| Tier 3 Ready | 90+ | Month 2 |

---

## BOTTOM LINE

**The system is ready to scale autonomously. The risk isn't capability — it's oversight.**

Current architecture supports everything Hale proposed. The key is **sequencing** (intelligence → webhooks → crews → formalization) and **gating** (Commander retains send authority until 90 trust score).

Do Tier 1 (fixes) this week. Do Tier 2 Phases 1-3 (intelligence + crews) over the next 6 weeks. Tier 3 (client-triggered autonomy) is month 2, and only if the trust score trajectory proves consistent.

**You've built the engine. Now we just need to warm it up before full throttle.**

---

*Review prepared by Hale (COS) with architectural assessment of model stack.*
*Next: Commander approval on Tier 1 go-ahead.*
