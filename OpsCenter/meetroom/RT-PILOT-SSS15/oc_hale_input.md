# RT-PILOT-SSS15 — OC-Hale Input: Auto-Generated Status Papers from the Action Log

**BLUF:** Draft an SSS only when the action log proves a human must decide something — never on routine PASSes. The best trigger isn't DISCREPANCY per se; it's *value surfaced* (a production finding, or a rework pattern). Source: `delegation_outcomes.jsonl` — structured, verdicts + detail, the repo's real action log.

## 1. Trigger condition (draft-only; never auto-send)
Fire, in priority order:
- **Value-surfaced PASS** — `discrepancy_detail`/`routing_recommendation` carries a real finding needing disposition. Tonight's #23 is the gold case: build passed, but 3 genuine financial/FPD items were uncovered.
- **DISCREPANCY with pattern** — ≥2 defects in one handoff, or a lane-routing change. Single one-line bug fixed + re-verified = routine, no paper (tonight's `pilot3` corrects to PASS-by-fix).
- **Cluster** — ≥3 related rows (same ticket family / seat / task_type / day) that individually are routine but collectively show a trend.
- **Gate/SO-adjacent self_execute** — verification-primitive-adjacent code executed alone without Commander note (tonight's #14/#2 pattern, `pilot2-run-gate-cache`).

## 2. Source mapping — worked example: `tranche3-sss23-chain-notify` (OC, cross_engine_verify PASS)
- **purpose** — "Inform: build passed but surfaced 3 unnotified financial/FPD items needing disposition."
- **background** — from structured lineage: Item #23 (chop-chain notify); OC, `oc_direct_lean`; pre-existing state = SSS-005/006/007 sitting `in_coordination` with no notify mechanism.
- **discussion** — `discrepancy_detail` content: first-try PASS, exact-match verified against known-good data; items = Loucks Grandeur FPD 24798, TESS pipeline 3018 gap, Furlow/Kuklinski FPD audit.
- **recommendation** — from `routing_recommendation` + `follow_up_due` + orchestrator judgment: "Dispatch notifications; assign FPD-audit ownership; close SSS-005/006/007."

Mapping rule: `discussion` ≈ verdict detail verbatim; `recommendation` ≈ routing + due + orchestrator call; `background` ≈ ticket lineage (id/seat/dispatch/task_type).

## 3. Noise control
Estimate: **0–1 papers/typical day; 1–3 on heavy build nights** (tonight: 1–2). Controls: draft-only (WF-17 unchanged), daily dedupe by ticket family, hard weekly cap of 3.

## 4. OPR / action_officer
**Executor seat** (the one whose work is under review) = `opr`/`opr_seat`. Orchestrator (**CC**) = `certified_by` on the recommendation. Accountability rides with the doer; sign-off rides with CC.
