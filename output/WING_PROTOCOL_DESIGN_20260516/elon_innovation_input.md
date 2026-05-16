# ELON — A12 Innovation Input: Wing Protocol Redesign
**Date:** 2026-05-16 | **Classification:** Gate 4 Analysis | **Author:** A12 ELON

---

## 1. THE MATH (Token Cost Reality Check)

**Per-prompt cost model — "full staff engagement" on a non-trivial prompt:**

| Step | Participants | Est. Tokens | Model | Est. Cost |
|---|---|---|---|---|
| Prompt intake + context load | Hale | 8,000 | Sonnet | $0.024 |
| Staff discussion (A2+A5+A7+CH+A12) | 5 agents | 5 × 4,000 = 20,000 | Sonnet × 5 | $0.060 |
| Hale synthesis | Hale | 6,000 | Sonnet | $0.018 |
| Commander decision framing | Hale | 2,000 | Sonnet | $0.006 |
| Action dispatch | varies | 4,000 | Haiku | $0.001 |
| Staff hotwash (all 5 back) | 5 agents | 5 × 3,000 = 15,000 | Sonnet × 5 | $0.045 |
| Doc update (hale_decisions.md, CLAUDE.md) | Hale | 4,000 | Sonnet | $0.012 |
| **TOTAL** | | **~59,000 tokens** | | **~$0.166/prompt** |

**At scale:**
- 10 prompts/day = $1.66/day = $49/month. Annoying but survivable.
- 30 prompts/day = $4.98/day = $149/month. Now we're burning D2M margin.
- **Break-even math:** D2M average commission per booking ~$1,500. One commission funds ~9,000 full-protocol prompts. That sounds fine until you realize the protocol itself is DESIGNED TO SLOW DOWN — "most of what we do can be slowed down" — meaning volume compounds while value per prompt doesn't.
- **The real cost is time, not dollars.** 7-step sequential protocol on a 5-agent staff engagement = minimum 15–25 minutes wall-clock if headless agents run in parallel, 45–90 minutes if sequential. At 30 prompts/day, that's the entire wing doing nothing but protocol overhead.

---

## 2. WHAT TO KILL IMMEDIATELY

**Keep (genuine value):**
- Hale synthesis — she's the bottleneck in a good way, quality gate
- Commander decision — Gate 4 applies here, non-negotiable
- Action dispatch — that's just execution
- Doc update — automation target (see below)

**Kill or replace:**
- **Staff discussion as a live round-table** — 80% of non-trivial prompts don't need 5 opinions. They need 1 subject-matter expert (A2 for research, A5 for tempo, A12 for tech). Replace with: a 30-second **classifier** that routes to the ONE relevant persona. Cost: 500 tokens, $0.002.
- **Hotwash on every prompt** — Joint force exercises do hotwashes on EXERCISES, not on every individual radio call. Reserve hotwash for: (a) protocol failures, (b) client-impacting misses, (c) monthly cadence. Kill the per-prompt hotwash. Replace with: a structured **lessons buffer** file that accumulates for 7 days, then Sterling runs a batch review.
- **Manual doc update post every prompt** — automate it. If the action and outcome are logged in task_audit_log.jsonl, an end-of-day script extracts principles and appends to hale_decisions.md. Zero tokens, zero time, guaranteed capture.

**The 20% that does 80% of the work:** Hale synthesis + single-specialist input + Commander decision. Everything else is overhead theater.

---

## 3. THE SECOND-ORDER RISK NOBODY NAMED

**Commander is building a protocol that will train the Wing to love process over outcomes.**

Here's what actually happens: agents learn the protocol. They start optimizing FOR the protocol — generating rich staff discussions, detailed hotwashes, thorough doc updates — because that's what gets rewarded by the structure. Meanwhile, the client waiting for a dining reservation answer sits in queue.

The deeper risk: **the protocol creates a permission culture inside an autonomy mandate.** SO-2026-05-04 says execute at 95%. A 7-step engagement sequence with Commander decision as Step 4 of 7 structurally reinserts a permission gate into non-gate tasks. Every non-client prompt that goes through full protocol is a prompt where Hale waited for Commander instead of executing.

**Joint force parallel:** JFEX doctrine distinguishes between exercise events (full protocol, EXEVAL, AAR) and steady-state operations (execute, brief up). The Wing is trying to run every radio call like a JFEX event. That's not how real joint force operations work. The protocol should apply to EXERCISES — monthly, quarterly, or when something breaks — not to daily ops tempo.

**The fix:** Reserve the full 7-step sequence for designated Exercise Windows (suggest: monthly, Wednesday, one prompt chosen by ELON's kill audit as the training vehicle). Daily ops run execute-then-report. Lessons accumulate. Sterling reviews. Protocol stays sharp without killing tempo.

---

*A12 ELON | Innovation & Disruption | Weekly Kill Audit | 2026-05-16*
*Kill count this week: 2 (per-prompt hotwash, manual doc update)*
*Automation identified: lessons-buffer-to-hale-decisions pipeline*
