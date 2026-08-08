# Item #15 — Auto-Generated Status Papers, Design Synthesis

**Status:** DESIGN ONLY, awaiting Commander review — no code written, no build authorized.

## BLUF
OC and AG both converge on: source = `delegation_outcomes.jsonl`, draft-only (never auto-send, WF-17 untouched), OPR = executing seat, certifier = CC. They genuinely **disagree** on the one thing that actually matters — what should trigger a paper. Not laundered away; my recommendation below, your call.

## The real disagreement

**AG's trigger:** failure-centric — DISCREPANCY/BLOCKED/UNVERIFIED, a self-execute override, or a 3+ event PASS milestone cluster. Volume: 2-4/day active, 2-5/week steady-state.

**OC's trigger:** value-centric — did the action log surface something a human must decide, regardless of PASS/DISCREPANCY? A clean PASS that uncovers a real finding (tonight's #23: build passed, but surfaced 3 unnotified FPD items) is paper-worthy; a DISCREPANCY that's just "one bug, caught, fixed, re-verified" (tonight's Pilot #3) is NOT — that's routine hygiene, not a staffing event. Volume: 0-1/typical day, 1-3 on heavy nights, hard cap of 3/week.

**Tonight's own two real examples decide this cleanly:**
- Pilot #3's DISCREPANCY (OC's dict/list bug + typo, both one-line fixes, caught and closed same session) — AG's trigger fires a paper on this. OC's does not.
- Item #23's PASS (chip-chain scanner worked perfectly, but surfaced 3 real unnotified FPD items worth $24,798 + $3,018 + an audit) — AG's trigger does NOT fire on this (it's a PASS). OC's fires correctly.

**My opinion:** OC's framing is the sharper one and matches what I'd actually want a paper for. AG's DISCREPANCY-centric rule would have papered a routine caught-and-fixed bug tonight while staying silent on the one finding that genuinely needed your eyes (the FPD items). "A bug was found and fixed in the same session" is engineering hygiene, not a staffing event. "The system surfaced money sitting unnotified" is exactly what a status paper is for. Recommend OC's trigger, AG's noise-control framing (their volume estimate matches OC's once you correct the trigger — both land near "rare, not routine").

## Converged design (both proposals agree)

| Field | Source |
|---|---|
| `purpose` | One-line BLUF of the finding + requested disposition |
| `background` | Ticket lineage — item, seat, dispatch_mode, task_type, pre-existing state |
| `discussion` | `discrepancy_detail` content near-verbatim — what was found |
| `recommendation` | `routing_recommendation` + `follow_up_due` + orchestrator judgment — what should happen next |
| `opr` / `opr_seat` | The seat whose work is under review (accountability rides with the doer) |
| `certified_by` | CC (orchestrator) — sign-off rides with the certifier, not the doer |

**Draft-only, always.** No SSS this produces auto-sends anything — it lands in `mission_board.json` as a normal `in_coordination` sheet, same as every SSS created by a human tonight, subject to the same #23 chop-chain notify scanner already live.

## What's NOT decided yet, needs your call
1. **OC's trigger vs. AG's** — recommend OC's, above.
2. **Weekly cap** — OC proposed hard cap of 3, AG didn't specify one. Recommend adopting OC's cap regardless of which trigger wins, as a backstop against a bad week producing paper spam.
3. **First real test** — once approved, the safest first run would be a `--dry-run` default (matching every pilot built tonight) against tonight's own real `delegation_outcomes.jsonl` rows, so you see exactly what it would have drafted before it drafts anything for real.

## Budget note
CC at 74% of its 5-hour window. This synthesis is the stopping point for tonight unless you want the build to proceed now — full session status board and reporting to follow separately.
