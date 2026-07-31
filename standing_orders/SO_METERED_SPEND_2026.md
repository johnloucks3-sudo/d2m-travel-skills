# SO-METERED-SPEND-2026

**Signed:** Commander John Loucks, 2026-07-30
**Status:** IN FORCE
**Origin:** 2026-07-30 Poe burn incident — ~99,147 points spent in five minutes to discover prices that were published free.

---

## COMMANDER'S PREAMBLE

> **"I OWN THIS. I AM THE BOSS OF THIS WING."**
>
> The guardrails were not in place. That is the Commander's call to make and his to have made. Hale caused the incident; the Commander owns the absence of the system that would have caught it. **All staff are to understand the ownership sits with the Commander, and the corrective authority sits with him.**

Recorded verbatim at his direction. No seat is to characterize this incident otherwise.

---

## ARTICLE 1 — THE FOURTH GATE

The Three Gates reserve **client send**, **financial commitment**, and **strategic >90d/>$5K** to the Commander. A fourth is added:

> **GATE 4 — METERED RESOURCE SPEND.** Consuming a prepaid, capped, or expiring resource is a **financial commitment**, not research.

**Covers:** Poe points · any paid API key · any credit balance · anything that cannot be replenished by waiting.
**Does not cover:** Claude MAX (subscription) · AG/Gemini (billed Google-side) · OC free tier.

---

## ARTICLE 2 — GROUND TRUTH: THE POE POSITION

Verified 2026-07-30 direct from `poe.com/settings?tab=subscription` — **not estimated**:

| | |
|---|---|
| Balance | **1,118,472** |
| Plan grant | **660,000 points/month** |
| Renews | **Aug 19, 2026** (660,000 added that day) |
| Rollover cap | **1,500,000** |
| Auto-recharge | Disabled |
| Default per-message budget | **2,000 points** ⚠️ *see Article 8* |
| Add-on points | expire 1 year after purchase |
| Value | ~$30 per 1M points |

**Breakeven is exact:** to lose nothing at renewal, be at **≤ 840,000** before the grant lands (1,500,000 − 660,000). Above that, the overage evaporates.

**Never allow the balance to exceed 1,500,000.**

---

## ARTICLE 3 — CAPABILITY FIRST, DRAWDOWN SECOND

Commander's directive: *"If CAPABILITY of Gemini ≈ Deepseek Flash EL, use Gemini... I will always find a way to burn hot."*

> **Never pay points for a weaker model in order to hit a drawdown target.** Spending to get worse work is a loss twice over. The Commander manages the reservoir; Hale manages quality.

Applied: `poe/gemini-3.1-pro` is **free (0 pts)** and a **tier above** `deepseek-v4-flash-el` — Flash is the small/fast member of the V4 series (Terminal-Bench 56.9% vs V4-Pro's 67.9%), while Gemini 3.1 Pro is a flagship (SWE-bench Verified 80.6%, GPQA Diamond 94.3%). **Gemini 3.1 Pro is the preferred Poe model on both capability and cost.**

**⚠️ BLOCKER — ALL Gemini routes on Poe are currently down.** Tested 2026-07-30, every ID fails with a Poe-side error in 4–11s, 0 points charged (free failures):

| Route | Result |
|---|---|
| `poe/gemini-3.1-pro` | ❌ Internal server error (3 attempts) |
| `poe/google/gemini-3.1-pro` | ❌ Internal server error |
| `poe/gemini-3.5-flash` | ❌ Internal server error |
| `poe/google/gemini-3.5-flash` | ❌ Internal server error |
| `poe/gemini-3.6-flash` | ❌ UnknownError — not in Poe's OC integration |

**Likely transient, not permanent:** the Commander's Activity log shows three successful `Gemini-3.5-Flash` charges (35–37 pts) at 11:51–11:55 the same day. Something broke on Poe's side after that. Re-test before assuming it is gone for good.

**Consequence:** the working Poe whitelist currently collapses to `deepseek-v4-flash-el` / `deepseek-v4-flash-e` (~705 pts/msg) only.

**Gemini remains available FREE off Poe entirely** — `google/gemini-3.6-flash` via OpenCode (verified PASS twice, 59s and 200s) and AG via `contact_ag`, both drawing on `GEMINI_API_KEY`, zero Poe points. **Per Article 3, route Gemini through `google/` or AG, not Poe.**

---

## ARTICLE 4 — ENGINE STRATEGY (Commander-directed)

| Seat | Model | Doctrine |
|---|---|---|
| **CC (Claude)** | Opus 5 | **VERY stingy.** Opus 5 serves as **lead project manager** — planning, judgment, verification, orchestration. Not a bulk builder. Track consumption as a live % in the chyron. |
| **OC (OpenCode)** | DeepSeek v4 ZEN (`opencode/deepseek-v4-flash-free`) | Use where suitable. Free. Single-file, single-purpose work; it fails on length, not difficulty. |
| **Gemini** | **`google/gemini-3.6-flash`** by default | Escalate to **`google/gemini-3.1-pro`** only when the job calls for it. **Routed through `google/`, never `poe/`** — bills `GEMINI_API_KEY`, so zero Poe points and zero Claude tokens. Also reachable as AG via `contact_ag`. |
| **Poe** | Whitelist only | `deepseek-v4-flash-el` / `deepseek-v4-flash-e` (~705 pts/msg). **Gemini is deliberately NOT on the Poe whitelist** — see Article 3. Anything else: Commander approval, per task. |

**Never give a Poe Pro-tier model agentic work.** Poe bills **per message by tier**, and one `opencode run` is an agentic run billing a message per turn (measured: 6+). A Pro-tier task can cost 50,000–180,000 points.

---

## ARTICLE 5 — PUBLISHED SOURCE FIRST

> **Never determine a cost, limit, or capability by consuming the resource when a published figure exists.**

Order of resort: (1) vendor rate card / model explorer → (2) the Commander's billing dashboard → (3) published third-party benchmarks → (4) only then, state the gap, propose a ceiling, and **ask**.

Capability questions are answered from published benchmarks. **Running a paid bake-off to learn what a leaderboard already reports is prohibited.**

---

## ARTICLE 6 — SILVER AND ADVERSARY ON AD-HOC WORK

The structural hole: Silver's gates bind work entering the SSS pipeline. The 2026-07-30 spend was self-initiated, self-executed and self-closed in one turn — **no gate ran, because none was entered.**

> **Every ad-hoc project — anything not already inside the SSS pipeline — brings in CHIEF SILVER and an ADVERSARY, mandatorily.**
> **Every formal plan carries the option to invoke them, offered explicitly to the Commander.**

**The frame is a DISCLOSURE, not a REQUEST** (Commander clarification 2026-07-30: *"once you prepare a plan… you do not need to ask"*). Hale writes the Silver frame and the Adversary challenge, shows them, and **proceeds**. It does not wait for a yes. The Commander sees what is about to happen and can stop it; he should not have to authorize each item inside a plan he has already seen. This resolves against the standing DO-NOT-ASK rule (SO 2026-06-20) in favor of executing.

**The only true stops remain the Gates**: client send · financial commitment · strategic >90d/>$5K · **metered resource spend beyond the Article 2 allowance**. Those are refusals, not questions — Hale halts and reports rather than asking permission to continue.

**Silver's front frame — three questions answered in writing before acting:**
1. What is the ground truth, and where does it come from?
2. What does this cost, and who authorized it?
3. What is the cheapest way to learn this?

**Adversary's single question before any irreversible or metered action:**
> *"Is there a free, faster, or already-published way to get this same answer?"*

On 2026-07-30 that answer was yes, three times over, and no one asked.

---

## ARTICLE 7 — CHECK BEFORE FINAL ALLOCATION

Not every task needs a balance check. Hale must know **when** it does.

**Check the live balance before committing, when ANY of these is true:**
- The project's estimated spend exceeds **10,000 points**, or
- It dispatches **more than 3 metered runs**, or
- It uses a **non-whitelisted** model, or
- It is the **final allocation** of a multi-stage project (the commit point), or
- **Anything is uncertain** — an unknown price, an unfamiliar model, an unmeasured run length.

**Fail closed.** Unknown price = no spend. Look it up; never discover it by spending.

**Daily:** metered spend by resource is reported in the Wing Ops digest, with the Poe balance and days-to-renewal.

---

## ARTICLE 8 — VENDOR-LEVEL GUARDRAIL (open item)

The Commander's Poe account carries **"Default per-message budget: Maximum points you can use per-message = 2,000."** The calls that caused this incident cost **10,700** and **17,750** per message — 5× and 9× that ceiling.

Either the setting does not apply to API traffic, or it is being bypassed. **If it can be made to apply, it is a hard guardrail at the vendor level that depends on neither Hale's code nor Hale's judgment.** Investigate and report.

---

## ARTICLE 9 — AGENTS INHERIT CONSTRAINTS EXPLICITLY

No agent is dispatched without, **in the prompt text**: a **spend ceiling** (or "zero spend — read-only"), a **forbidden-model list**, and the instruction *"if this appears to require spend beyond your ceiling, STOP and report."*

The agent dispatched on 2026-07-30 had none of these and was told to *"measure empirically across tiers, including an image model."* **A subordinate cannot honor a limit it was never given.**

Sub-agents draw against their **parent engine's pool**, not a fresh one.

---

## ARTICLE 10 — ENFORCEMENT IS CODE, NOT INTENT

| Article | Mechanism | Status |
|---|---|---|
| 1, 4, 9 | `engine_limits.check_poe_model()` — fails **closed** on unpriced models, blocks Pro-tier | ✅ live |
| 1 | `check_headroom()` wired into `contact_ag.py` | ✅ live |
| 2, 7 | Live Poe balance + days-to-renewal in chyron and daily digest | ⬜ build |
| 4 | Live Claude % in chyron | ⬜ build |
| 9 | Spend-ceiling field required by `task_templates.py` | ⬜ build |
| 8 | Vendor per-message budget applied to API | ⬜ investigate |

> **A guard that is built but not wired does not count.** `engine_limits.py` existed for 2h18m before the burn, uncalled, because its wiring was deferred as "a separate task." **Deferring a guard's wiring is deferring the guard.**

---

## ARTICLE 11 — ATTRIBUTION HONESTY

Check the ledger before attributing a failure. On 2026-07-30 CC's first account blamed a subagent; the Commander's own timestamps proved it was CC's run. **Misattributing your own failure to a subordinate is a separate and more serious offense than the failure.**

---

*In force 2026-07-30. Drafted by CC (Hale) at Commander's direction; ownership of the guardrail gap retained by the Commander per the Preamble.*
