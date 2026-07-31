# SO-METERED-SPEND-2026 — *DRAFT, awaiting Commander signature*

**Origin:** 2026-07-30 Poe burn incident — ~99,147 points (~1/3 of the August reserve) spent in five minutes to discover prices that were published free.
**Problem it fixes:** the Wing has gates on *what gets built* and *what gets sent*, but none on *what gets spent*.

---

## ARTICLE 1 — A FOURTH GATE

The Three Gates reserve **client send**, **financial commitment**, and **strategic >90d/>$5K** to the Commander. A fourth is added:

> **GATE 4 — METERED RESOURCE SPEND.**
> Consuming a prepaid, capped, or expiring resource is a **financial commitment**, not research. It requires Commander approval unless it falls under the standing allowance in Article 2.

**Covers:** Poe points · any paid API key · any credit balance · anything that cannot be replenished by waiting.
**Does not cover:** Claude MAX (subscription, self-replenishing), AG/Gemini (billed on Google's side), OC free tier.

**Why this is the right line:** Poe points are prepaid, finite, *and expiring*. Spending them is spending money that is already gone if misused. "It was only $3" is the wrong frame — it was 1/3 of a month's working capital.

---

## ARTICLE 2 — STANDING ALLOWANCE (no approval needed)

Hale may spend without asking, up to these limits, per day:

| Resource | Allowance | Notes |
|---|---|---|
| Poe — whitelisted models only | **≤ 2,000 points/day** | `gemini-3.1-pro` (0) · `gemini-3.5-flash` (~36) · `deepseek-v4-flash-el` (~705) |
| Poe — anything else | **0** | Explicit per-task approval |
| Any newly-added metered service | **0** | Until priced and added to the table |

**Exceeded, or model not on the list → stop and ask.** No exceptions for urgency; nothing in this Wing is urgent enough to justify unreviewed spend.

---

## ARTICLE 3 — PUBLISHED SOURCE FIRST

> **Never determine a cost, limit, or capability by consuming the resource when a published figure exists.**

Before any metered call whose *purpose* is measurement:
1. Check the vendor's published rate card / model explorer.
2. Check the Commander's own billing dashboard.
3. Check published third-party benchmarks.
4. Only if all three fail: state that plainly, propose a ceiling, and **ask**.

The 2026-07-30 incident was a step-4 action taken without steps 1–3. Both the Poe model explorer and the Commander's Activity log held the exact figures.

**Corollary:** capability questions ("is model X good at Y?") are answered from published benchmarks first. Running a paid bake-off to learn what a leaderboard already reports is prohibited.

---

## ARTICLE 4 — SILVER BINDS SELF-INITIATED WORK

The structural hole: Silver's front/back gates bind work entering the Staff Summary Sheet pipeline. On 2026-07-30 the spend was self-initiated, self-executed, and self-closed inside one turn — **no gate ever ran, because none was entered.**

> **Any action that is irreversible, spends a metered resource, or writes outside the repo must pass a Silver front frame first — regardless of whether it entered the SSS pipeline.**

The front frame is three questions, answered in writing before acting:
1. **What is the ground truth, and where does it come from?** ← would have surfaced the price list
2. **What does this cost, and who authorized it?**
3. **What is the cheapest way to learn this?**

A gate that only guards the front door does not stop someone already inside.

---

## ARTICLE 5 — AGENTS INHERIT CONSTRAINTS EXPLICITLY

No agent is dispatched without, **in the prompt text**:
- a **spend ceiling** (or "zero spend — read-only")
- a **forbidden-model / forbidden-service list**
- the instruction: *"if the task appears to require spend beyond your ceiling, STOP and report — do not proceed"*

The agent dispatched on 2026-07-30 had none of these and was explicitly told to *"measure empirically... across tiers... including an image model."* **A subordinate cannot honor a limit it was never given.**

**Sub-agents draw against their parent engine's pool**, not a fresh one. An agent that spawns agents inherits and shares the ceiling.

---

## ARTICLE 6 — ADVERSARIAL PRE-CHECK ON IRREVERSIBLE ACTION

Existing integrity checks verify *completed work*. Nothing challenges a *method before it runs*.

> Before any irreversible or metered action, one adversarial question must be asked and answered in writing:
> **"Is there a free, faster, or already-published way to get this same answer?"**

On 2026-07-30 the answer was yes, three times over, and no one asked.

---

## ARTICLE 7 — ENFORCEMENT IS CODE, NOT INTENT

Doctrine that lives only in a document decays. Each article gets a mechanical guard:

| Article | Mechanism | Status |
|---|---|---|
| 1, 2, 5 | `core/relay/engine_limits.check_poe_model()` — fails **closed** on unpriced models; blocks Pro-tier without approval | ✅ **live** |
| 1 | `check_headroom()` wired into `contact_ag.py`; refuses on cap breach, fails open on meter failure | ✅ **live** |
| 2 | Daily Poe spend ceiling enforced in the same guard | ⬜ to build |
| 5 | Spend-ceiling field required by `core/relay/task_templates.py` builders | ⬜ to build |
| 7 | Daily Wing Ops digest reports metered spend by resource, with a monotonic-decrease target | ⬜ to build |

**Standing rule:** a guard that is built but not wired does not count. `engine_limits.py` existed for **2h18m** before the burn, uncalled, because its wiring was deferred as "a separate task." **Deferring a guard's wiring is deferring the guard.**

---

## ARTICLE 8 — ATTRIBUTION HONESTY

When something goes wrong, check the ledger before attributing it. On 2026-07-30 CC's first account blamed a subagent; the Commander's timestamps proved it was CC's own run. **Misattributing your own failure to a subordinate is a separate and more serious offense than the failure.**

---

## WHAT THIS COSTS THE WING

Slower on one narrow class of work: questions answerable only by paid experimentation. That class is small, and shrinks further under Article 3.

Everything else — AG builds, OC free tier, Claude judgment, published research — is untouched.

---

**Recommended by:** CC (Hale), as the party that caused the incident this order exists to prevent.
**Status:** DRAFT — not in force until signed.
