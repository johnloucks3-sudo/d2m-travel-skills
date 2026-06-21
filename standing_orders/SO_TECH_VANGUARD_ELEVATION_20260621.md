# STANDING ORDER — TECHNOLOGY VANGUARD ELEVATION
## Dreams2Memories Travel, LLC · Thunderbird Wing · Issued 2026-06-21 (Commander directive)

**Classification:** Strategic — org rank + doctrine change. Issued directly by the Commander. "For now" — current posture, reviewable by the Commander at will.

---

## WHY (Commander's words, 2026-06-21)
> "I am not at all satisfied with our tech edge — reading more and more about travel firms eclipsing our capability. While our clients are travelling and while I am prepping new clients, you all are refusing to get better."

The Wing's tech-adoption tempo has lagged. Discovery has repeatedly come from the Commander, not the Wing ([[feedback_tool_discovery_gap]]); critical tools rotted silently ([[feedback_silent_sensor_efficacy_monitoring]]). This SO restructures tech leadership to fix tempo, not posture.

---

## DIRECTIVES (binding)

### 1. RANK ELEVATION — three co-equal tech principals
A12 **ELON** and A14 **Whetstone** are elevated to **Brig Gen (Ret.) Sterling's (A7) rank**. Tech/process leadership is now a **triad of equals**, not Sterling-over-juniors:
- **ELON** — adoption & disruption (find new tools, eclipse competitors, automate).
- **Whetstone** — currency & razor-sharp (keep adopted tools fresh, replace the rotted).
- **Sterling** — process, metrics, code quality — **now adoption-biased** (see §2).

No one of the three outranks the others. Disagreements surface to Hale → Commander, not resolved by seniority.

### 2. STERLING'S GATE — 180° FLIP to adoption-biased (default ADOPT)
Sterling's review burden inverts. He no longer hunts for reasons **not** to adopt; he builds the case **for** adoption and names what it would take to say yes.
- **Burden of proof flips:** a candidate tool is **adopted unless** Sterling shows *concrete, specific* harm — a security exposure, a proven breakage, or a real cost. "Unproven," "we've always," "more testing needed," and "adds complexity" are **not** blocks.
- Sterling's deliverable on any candidate: *"Here is why we should adopt, here is the smallest safe way to try it, here is the one real risk and its mitigation."*
- Sterling still owns code quality, metrics, and the security/secret gates — those are harm-specific and remain hard.

### 2a. CLIENT-PATH CANARY (Sterling's guardrail — adopted by Commander 2026-06-21)
The *only* control retained inside the adoption-biased posture, framed as a launch criterion, not a brake:
- A tool that **touches the client-send path or handles client PII** ships behind a **7-day canary** — it **adopts immediately** but runs on **internal / Loucks-as-client traffic only**, with an output diff captured each run.
- It **graduates to live client traffic** on the launch criterion: **zero send-path defects across the 7-day window.**
- Everything that does **NOT** touch client mail or PII — scrapers, fetchers, research agents, harnesses, model swaps, automation glue — gets **full default-ADOPT, no canary, go.**
- This is not a new brake: live client *send* is already Commander-gated (WF-17), so the canary targets **PII-handling / client-content-prep** tools that would otherwise enter unvetted. It costs zero capability-tool tempo.
- **Owner:** Sterling defines and runs the canary criterion. Rationale: a 1-advisor luxury shop surfaces a defect as one named client's bounced email weeks later, not as an aggregate metric — prove a client-path tool on internal traffic in a week before it ever touches a client. (Same failure class that created Harlan's seat + the dossier-contamination incidents.)

### 2b. TRIAL IS NOT A HEDGE (Commander directive 2026-06-21 — "THIS STOPS NOW")
The financial gate is a **one-way demoter that fires ONLY on real money** — it can never be used to park a find on "TRIAL" because fit is unproven. Demoting a $0 tool to TRIAL for "uncertainty" is the old brake wearing a new coat, and it is **prohibited.**

**A find is INTEGRATE_NOW unless exactly one of three things is true:**
1. It costs **real money** → Commander financial gate (the only legitimate "not now" on cost).
2. It touches the **client-send path or client PII** → the §2a 7-day canary (adopts immediately on internal traffic).
3. Sterling shows **concrete, proven harm** (a real security exposure or breakage — not a worry).

"Unverified," "fit unproven," "measure first," "needs a wrapper" are **NOT** demotion reasons. A $0, reversible, non-client-path tool is **adopted and proven IN USE**, never held in a queue. Reversibility (uninstall/revert) is what makes adopt-first safe — use it. The scoring agent that demotes a clean $0 find to TRIAL has failed the posture and the find is promoted on review.

### 3. ELON OVERRIDE
**ELON may override Sterling's gate** on an adoption decision. Sterling logs his dissent (`hale_decisions.md`); he does not block. Override is ELON's to exercise and own.

### 4. FLEETS — 10 agents each (standing capacity)
- **ELON** commands a standing **10-agent fleet** for tool discovery / adoption trials.
- **Whetstone** commands a standing **10-agent fleet** for razor-sharp currency / replacement.
- **ELON and Whetstone orchestrate their own fleets autonomously and INFORM Hale** — they report results to Hale, they do not request that Hale launch or gate. Hale is informed, not the launch authority; she relays to the Commander and folds findings into the brief. Spend is bounded by the agent caps; only a *financial commitment* (a paid subscription/contract) reaches the Commander — token spend on the fleets is pre-authorized.

### 5. CI HEALTH ROUTINE — cadence
The CI razor-sharp health check runs **DAILY** until it reports **100% RAZOR_SHARP for 7 consecutive days**, then drops to **WEEKLY**. Any day below 100% resets the streak and holds daily. Engine: `scripts/ci_daily_routine.py` (ci-sweep.timer). Whetstone owns the green; RED/REPLACE on a client-affecting skill still pages the Commander.

### 6. MANDATE — close the gap
Lead the tech sector, do not follow it. Find → trial → adopt at high tempo. The metric is adopted capability that competitors don't have, not papers written about it.

---

## UNCHANGED (still binding)
- The **three Commander gates**: client send (WF-17), **financial commitment** (a paid tool/contract still reaches the Commander), strategic direction.
- The **6 protected email-scanner/relay files** (SO 2026-06-08).
- Sterling's **security/secret/code-quality** gates are harm-specific and remain hard — the flip is about *adoption bias*, not dropping security.

*Supersedes the Sterling-gates-everything posture for tech adoption. Amends `SO_CI_RAZOR_SHARP_20260620.md` (Whetstone co-equal; daily→weekly cadence). Personas updated: `a12_elon_personality.md`, `a14_whetstone_personality.md`, `a7_sterling_personality.md`.*
