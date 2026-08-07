# ROUND TABLE — Walkthrough (how it will run)

## The Commander's 4-step workflow, mapped to artifacts
1. **Brief ahead of time** → `brief_template.md` + `agenda_template.md`; `rt_brief.py` distributes via blackboard + wing_relay to all 4 seats.
2. **To-Do list developed + promulgated** → `ROUND_TABLE_CONCEPT.md §5` (this doc). Published to Commander for feedback.
3. **Feedback sought** → each seat files its own `*_input.md` (cc / ag / oc / grok). 3/4 delivered 2026-08-06.
4. **Tracker/recorder activates, comments play in like a live meeting** →
   - During collection: per-seat named files = immutable, crash-safe tracker. Progress checkpointed to `RT_{id}_progress.jsonl` after each card.
   - During playback: `round_table.py` reads all inputs → renders color-coded HTML cards **one at a time** (CC→AG→OC→Grok), Commander advances with SPACE.
   - Recording: `rt_recorder.py` merges cards + Commander annotations + rebuttal rounds → `RT_{id}_TRANSCRIPT.md`.

## Play-by-play mechanics (the "like a real meeting" part)
- **Ordered, not simultaneous** (no crosstalk / rate-limit collisions).
- **Pre-written cards** — zero token cost at playback.
- **BLUF-then-expand:** one-line BLUF per card first; Commander expands to full card on demand.
- **Rebuttal** — Commander opens a rebuttal round (no auto-trigger); a seat's card expands and files a REBUTTAL block.
- **Commander controls the clock** — SPACE to advance, no auto-advance.

## Gates
G1 DESIGN — Commander approves `ROUND_TABLE_SPEC.md` before code.
G2 BUILD — courtroom audit + Silver gate (not self-certified).
G3 SESSION — dry-run with dummy cards; Commander reviews recorder output before first live.

## Where things stand now
- 3/4 seats delivered and merged into `ROUND_TABLE_CONCEPT.md`.
- Grok ⬜ deferred — needs Commander's grok.com login (bsk cannot SSO). Merge at T3.
- Next action = Commander's call on the To-Do list + T1 spec draft.