# OC-HALE PROPOSAL — RT-WARROOM-KAIZEN-COST
**Seat:** OC (DeepSeek Zen, OFF MAX) · **File:** oc_hale_input.md · **Date:** 2026-08-08

**BLUF:** The four ideas are one mechanism seen four ways — a structured ticket schema as the single wire format between engines, a single async dispatcher+runner, and a rendered (not written) report layer. I concur on all four; the refinements below keep verification and gates on the ticket, not on the live session.

## Purpose
Cut live-CC engagement ~80% per task; land real work on OC/AG (off MAX); make CC headless tickets small and checkable.

## Discussion — Commander ideas, direct responses

**1. Async tasking of CC via form — AGREE, reuse the schema.**
Don't build a new form. Extend `core/relay/task_templates.py` with `build_cc_task()` reusing the same `CONSTRAINTS` block (spend ceiling, forbidden models, is_checkable bar). Ticket lives as one file: `Ops/queued/cc_tasks/<ticket_id>.json` (schema: `ticket_id, seat, spec, gates, verify_step, follow_up_due`). Dispatch = headless CC reads the file, executes, writes verdict back — no live CC. Write the Commander message auto-completed via `build_oc_task`-style prompt. Despatch loop can be a systemd oneshot (`Wants=network.target`, per SO 2026-08-01).

**2. Skills that proffer forms to CC — AGREE, symmetrize to ## schema.**
Tonight's Instructor Mode made CC always write the spec; reverse it so any engine's SKILL emits the *same* ticket schema, not prose. New `.opencode/skills/ask-cc/SKILL.md` (+ AG/Haiku twins) producing a filled `<ticket>.json` via `task_templates`. One format, every engine speaks it. Rejects prose round-trips at the source.

**3. Machine language between engines — AGREE, with a translation boundary.**
`delegation_outcomes.jsonl` is already the wire — add the ticket fields (gates, verify_step, verdict) and make it the only engine-to-engine channel. The translation layer exists and stays: `mission_board_sync.py` + `commander_channel.notify()` (WINDOW) render structured rows to human output. Engines never emit Commander-facing prose except on the final delta.

**4. Canned periodic reports — AGREE, mechanical assembly export.**
New `scripts/kaizen_report.py`: render from `mission_board.json` + `delegation_outcomes.jsonl` into the templated brief (table of done/blocked/next, WINDOW-flushed at 06:30/18:30). The *only** live-CC words are a ≤3-line delta in `logs[].delta`. `cc_hale_input`-style narration dies.

## Risks (flag)
- **Async ≠ unsupervised-right**: every ticket close still requires inherent `core.staffing.integrity_check.verify_and_record()` against a ground-truth artifact; no verdict = DISCREPANCY (tonight proved this twice).
- **Gates travel with the ticket**: `gates` field must block auto-runs on client-send / financial / strategic — async never widens Weapons Free; the schema carries scope, not the session.
- **Schema drift / guesswork**: tickets failing `is_checkable()` are NACK'd back to issuer before any execution, so a weak model stops rather than guesses.
- **No watcher = invisible stall**: each ticket carries `follow_up_due`; overdue → auto-surface at next episode boundary, never silent.

## Opinion / recommendation
Adopt Ops/queued_tickets + uniform schema as the one mechanism (ideas 1-3 collapse into it), stand up `kaizen_report.py` (idea 4) and `ask-cc` skill as the first two shippers. Estimate: -60-70% live-CC watching on routine builds, zero new spend.

**Next:** CC synthesize against AG/ELON inputs; OC waits.