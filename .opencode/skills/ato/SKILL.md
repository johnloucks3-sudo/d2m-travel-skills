# ATO (AIR TASKING ORDER)

**Use for:** a REAL COMPLEX TASK where one problem needs decomposition across multiple agents/engines with a definitive plan, parallel sorties, and a definition of done. The ATO is the USAF mechanism for tasking assets to accomplish a mission — in the Wing it's the standing way to run a complex multi-lane build.

## When to trigger
- The task is genuinely **complex / multi-step / multi-discipline** — not a one-liner.
- Multiple engines or agents must work the SAME problem (team approach needs a tasking frame).
- There are **dependent slices** (chains) and **independent slices** (parallel) — the ATO separates them.
- You must hand a full problem to agents who weren't in the conversation (they need the whole picture in one document).

## Anatomy of an ATO (canonical structure — file at `OpsCenter/ato/ATO_YYYY-MM-DD_<mission>.md`)
1. **Header** — FROM/TO (orchestrator = AOC/JFCC), engines, constraint line (e.g. "Claude LIGHT — 88% burn"), valid-until.
2. **SECTION 1 — MISSION** — the FULL problem written for EVERY lane: situation, ground truth, links to key files, verified-ready tools, END STATE (definition of done — checkable, cross-lane).
3. **SECTION 2 — COMMANDER'S DECISION** — strategy authority: which of the three strategies (solo / apportion / same-problem-best) and why.
4. **SECTION 3 — TASKING** — sorties, each with: lane, objective, deliverable ABSPATH, RDD, priority, rank-fallback options. Parallel sorties = independent meters.
5. **SECTION 4 — SPINS/CONTROL** — rules that apply to every lane: ground-truth-is-arbiter, no client sends, light-touch constraints, timeline gates, RFI channel.
6. **SECTION 5 — EXECUTION RECORD** — issue line + the standing-up quote.

## The three strategies (Commander's framing — orchestrator picks)
1. **Do it all yourself** — smallest unit, one context. Right only for a single well-defined task.
2. **Apportion by strength** — fan out independent slices to the lane each fits. Right for parallelizable execution.
3. **Same problem to everyone, take the best** — capability discovery; independent engines on the same brief. Right for strategy / unknown-technique.

**The ATO's own rule:** strategy 3 for the DESIGN slice (find the winner), then 2 for EXECUTION (split the win into lanes), never 1 for anything >1 layer deep.

## Rules learned hard (2026-08-06, ATO-006-08 on Centrav autonomy)
- **Everyone gets the entire problem** — no lane works on a fragment it must re-derive.
- **Ground truth is the arbiter** — a lane claim contradicting a proven live result defers to the live capture, not the stronger prose.
- **Independent meters = parallel sorties** — don't serialize engines that don't share a budget.
- **RDD per sortie + gate** — A-01/A-02 by T+90 becomes A-03's gate; a light-touch verify sortie (CC) closes.
- **CLOSE the ATO** — record what delivered, what dead-ended, what the team re-routed to. The next ATO reads it.

## Sequence
1. Write the ATO (full problem, sorties, SPINS, definition of done).
2. Dispatch parallel sorties to the lanes (see `multi-hale-team` skill).
3. Synthesize + verify vs ground truth.
4. Close the ATO with a walkthrough artifact + commit.

## Worked example
`OpsCenter/ato/ATO_2026-08-06_centrav.md` — 4 sorties across Gemini/Grok/Claude/DeepSeek on Centrav B2B session autonomy. Results: AG (survival design), Grok (capture method + tasking doctrine), Claude (light verify), OC (live session + aggressive keepalive). Close: cookie-decrypt dead-ended (v11); team re-routed to ride-the-authenticated-tab keepalive; ATO closed clean.