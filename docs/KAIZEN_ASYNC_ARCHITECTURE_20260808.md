# KAIZEN — Asynchronous CC Architecture, War Room Synthesis
**Status:** DESIGN ONLY — awaiting Commander review, nothing built yet.

## BLUF
OC, AG, and ELON converged independently on the same diagnosis: your four ideas aren't four mechanisms, they're one — **a structured ticket schema that's the single wire format between every engine, an async dispatcher that runs it headless, and a templated (not hand-written) report renderer.** ELON's framing is the sharpest: *"the gap isn't tooling, it's that CC has been hand-writing prose where a schema already exists. Fix the habit, not the stack."* Real infrastructure for most of this already exists in this repo tonight — the work is mostly wiring, not invention.

## One correction before the design: headless CC does NOT save MAX budget by itself
All three seats and I independently confirm this (already established doctrine, `build_haiku_task()`'s own docstring): headless Claude — Haiku, Sonnet, or Opus — draws the **same Claude MAX/OAuth meter** as this live session. Going async does not itself cut token spend. What it cuts is **your synchronous engagement time**, and — if tickets are genuinely small/well-scoped instead of prose-heavy back-and-forth — likely fewer total tokens per unit of work. The real budget relief comes from landing more actual work on OC (DeepSeek, $0) and AG (Gemini, Google-billed, not Anthropic) instead of live CC, which this design also does.

## The converged mechanism (all 3 agreed, reconciled)

1. **One ticket schema, all engines speak it.** Extend `core/relay/task_templates.py` with `build_cc_task()` (OC's proposal), matching the existing 4 builders' `CONSTRAINTS` block + `is_checkable()` gate. Tickets live as files: `OpsCenter/tickets/<ticket_id>.json` (OC's path, corrected to match this repo's real `OpsCenter/` convention rather than OC's own typo'd `Ops/queued/cc_tasks/`). Fields: `ticket_id, seat, spec, gates, verify_step, follow_up_due` (OC) — `gates` is the field that carries Weapons Free scope WITH the ticket, so async execution can never accidentally widen authority beyond what was approved (AG + OC both flagged this independently — real convergence, not just agreement).

2. **The reverse skill — OC/AG proffer forms to CC, not prose.** New skill (name TBD — OC proposed `ask-cc`, AG proposed `cc-ticket-proffer`/`proffer_cc_form`) installed in OC and AG: when either seat needs CC's judgment, it fills the SAME ticket schema instead of writing a chat message, and CC answers the card. Closes the gap Instructor Mode left open tonight — that pattern only had CC writing specs, never receiving them structured.

3. **Machine language, translation boundary preserved.** `delegation_outcomes.jsonl` is already JSON — extend its fields to carry the ticket vocabulary (`gates`, `verify_step`, `verdict`) and make it the primary engine-to-engine channel. **Real risk, flagged by all three independently:** something still has to render JSON into Commander-facing English at the final boundary. AG's proposal is concrete: a template/Jinja-style formatter, not a live-CC-writes-a-paragraph step — if that rendering step becomes "have CC narrate it nicely," we've reintroduced the exact cost this whole design exists to kill.

4. **Canned reports, mechanical assembly.** New `scripts/kaizen_report.py` (OC's proposal): renders `mission_board.json` + `delegation_outcomes.jsonl` into the existing templated brief format, flushed via `commander_channel.notify()`'s existing WINDOW batching (06:30/18:30 — already built, confirmed live all session tonight). The only live-CC-authored content per report: a ≤3-line delta, not a regenerated narrative.

## One factual correction to AG's proposal
AG cited `core/relay/headless_claude.py` as the headless-CC dispatch mechanism — **that file doesn't exist.** The real, already-documented pattern is `OpsCenter/dispatch_claude.py` + `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` (referenced at the very top of this project's own `.claude/CLAUDE.md` as the "CRITICAL PROCEDURE"). Noted here rather than silently corrected, matching tonight's own "verify before trusting a report" discipline.

## Risks, all three seats named the same ones independently (real convergence)
- **Async ≠ unsupervised-correct.** Every ticket close still requires `core.staffing.integrity_check.verify_and_record()` against a real ground-truth artifact — no verdict, DISCREPANCY by default. Tonight proved twice why this can't be relaxed just because nobody's watching live.
- **Gates travel with the ticket, not the session.** Weapons Free scope is a field on the ticket (`gates`), never inherited implicitly from "CC is in async mode right now." Client send / financial / strategic stay hard-stops regardless.
- **A ticket that fails `is_checkable()` gets NACK'd back to whoever wrote it before any execution starts** — a weak spec stops at the gate, doesn't get guessed through.
- **No silent stalls.** Every ticket carries `follow_up_due`; overdue tickets surface at the next report window, never invisibly.

## What I'd actually build first (my synthesis call, not any one seat's)
1. `build_cc_task()` in `task_templates.py` + the `OpsCenter/tickets/` schema — the foundation everything else sits on.
2. `scripts/kaizen_report.py` — cheapest, fastest, most immediately visible win (kills live-CC report-writing tonight's own session did repeatedly).
3. The reverse `ask-cc`-style skill in OC/AG — after 1 and 2 are proven, since it depends on the same schema.
4. Headless-CC ticket runner (via the real `OpsCenter/dispatch_claude.py` pattern, not AG's guessed path) — last, since it's the highest-risk piece (unwatched execution) and should sit on top of a schema that's already proven itself on 1-3.

## Estimate
OC's number: -60-70% live-CC watching time on routine builds, zero new spend. Directionally credible given tonight's own session — most of the live time was spec-writing, verifying, and reporting in prose, exactly what this design mechanizes.

## Not built. Awaiting your review — same 4-beat discipline as every design tonight: this is Beat 1.
