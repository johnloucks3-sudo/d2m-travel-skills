BLUF: Item #15 — auto-generated status papers from the action log. `render_sss()` already renders a paper from a filled-in sheet; the real gap is deciding WHAT counts as the action log and HOW it maps to a sheet's `purpose`/`background`/`discussion`/`recommendation` fields. This is a design question, not a build — Commander wants AG and OC's independent perspectives before CC synthesizes a final scoped design.

## What's already confirmed (real, checked tonight — don't re-derive)
- Canonical SSS lives inside `OpsCenter/mission_board.json`'s `missions` list, created via `core/staffing/staff_summary_sheet.py`'s `open_sss()`, rendered via `render_sss()`.
- Real SSS entry fields: `id, title, purpose, opr, assigned_to, action_type, ocr_chain, coordination_log, acceptance_criteria, ground_truth_sources, verification_artifact, certified_by, silver_front_frame, suspense_date, priority, status, created_at, updated_at, logs, opr_seat, decision, cross_hale_cert, completed_at`.
- Candidate real "action log" sources already in this repo (not exhaustive — propose others if you know a better one):
  - `OpsCenter/delegation_outcomes.jsonl` — every delegate/verify/certify/self-execute event, PASS/DISCREPANCY/UNVERIFIED verdicts, real detail text (this is what tonight's own Pilot #2/#3/#23 work got logged to).
  - `hale_decisions.md` — append-only free-text decision/AAR log (very large, ~477K lines, append-only, human-readable sections).
  - Individual missions' own `logs` field (per-mission timeline, already structured).

## The actual design question
For an auto-generated SSS to be worth creating (not noise), something real has to have happened that a human should see formally, not just a routine PASS. Propose:
1. **Trigger condition** — what pattern in the action log should cause a new SSS to be auto-drafted? (e.g. a DISCREPANCY after a prior PASS streak; a self_execute with an unjustified rationale; a batch of related outcomes worth summarizing together; something else?)
2. **Source mapping** — given a triggering event/cluster from your chosen log source, how does it become `purpose` (one line), `background` (why this happened / prior context), `discussion` (what was found/done), `recommendation` (what should happen next)? Be concrete — show it working on a REAL recent entry from tonight's own delegation_outcomes.jsonl (it has real rows from tonight: mission_auto_escalate build with 2 real bugs, run_gate_cached PASS, sss_chain_notify PASS — use one of these as your worked example).
3. **Noise control** — what's the volume this would realistically produce per day/week if it ran continuously? A trigger that fires on every PASS would flood the Commander; one that only fires on genuine DISCREPANCY/escalation-worthy events is closer to what "worth a formal paper" means.
4. **Who's the OPR/action_officer** on an auto-drafted sheet — the seat that did the work, or CC as orchestrator?

## Format
Write your proposal as a point paper (BLUF first, ≤300 words), covering all 4 numbered questions above. File: this session's own `{oc,ag}_hale_input.md` — you'll be told the exact path in your dispatch.

## Not asked for
Do not write any code. Do not touch mission_board.json. This is a design proposal only — CC will synthesize both proposals into a final scoped plan for Commander review before anything gets built.
