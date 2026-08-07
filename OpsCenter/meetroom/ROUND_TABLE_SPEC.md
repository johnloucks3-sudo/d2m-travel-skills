# ROUND TABLE — Design Spec (`ROUND_TABLE_SPEC.md`)
**Status:** ⚠️ DRAFT — AWAITING COMMANDER DESIGN-GATE APPROVAL (T2). No code until approval.
**Owner:** Hale (OC seat drafting) · Inputs merged: CC ✅ AG ✅ OC ✅ Grok ⬜ (deferred, merge before build gate)
**Date:** 2026-08-06

---

## 1. Purpose
Give the 4 HALE seats (CC · AG · OC · Grok) a virtual, visual, **Commander-paced play-by-play** — a "meeting room / Zoom-style conference" — built on infrastructure we already own. **Not a platform; a thin sequencer + HTML viewer + recorder (~300 LOC, zero new deps).**

## 2. Design Principles (agreed cross-engine)
1. **Pre-write, don't live-generate.** All cards file-based before session → playback costs **zero tokens**. (CC, AG, OC agree.)
2. **Ordered, one card at a time** (CC → AG → OC → Grok). No simultaneous crosstalk — avoids rate-limit collisions and non-deterministic order.
3. **File is the room.** Engines cannot share live context; `blackboard.md` + per-seat `*_input.md` are the shared surface.
4. **Commander controls the clock.** SPACE to advance. No auto-advance.
5. **BLUF-then-expand.** One-line BLUF per card first; expand to full card on demand (ADHD win).
6. **≤300 words/card.** Hard limit enforced at brief stage.
7. **Color-coded seats.** 🔵 CC · 🟢 AG · 🟡 OC · 🔴 Grok.
8. **Single-writer, crash-safe.** Per-seat immutable files + checkpoint JSONL. A crash loses zero work.

## 3. The Commander's 4-step workflow → artifacts
| Step | Mechanism | Artifact |
|---|---|---|
| 1. Brief all 4 ahead of time | `rt_brief.py` distributes via blackboard + wing_relay | `brief_template.md`, `agenda_template.md` |
| 2. To-Do list developed + promulgated | orchestrator (OC, $0 lane) writes from transcript | `ROUND_TABLE_CONCEPT.md §5` |
| 3. Feedback sought | each seat files its own card | `{cc\|ag\|oc\|grok}_hale_input.md` |
| 4. Tracker/recorder activates; comments play in | `round_table.py` renders cards one-at-a-time; `rt_recorder.py` merges to transcript | `RT_{id}_TRANSCRIPT.md`, `RT_{id}_progress.jsonl` |

## 4. Components (build only after gate)
### `rt_brief.py` — briefing distribution (OC lane, ~80 LOC)
- Reads `brief.md` + `agenda.md`; appends to `blackboard.md`; broadcasts via `a2a_broadcast` + wing_relay.
- Enforces the ≤300-word card cap and 800-token input budget per seat in the brief text.

### `round_table.py` — sequencer + HTML viewer (CC lane, ~150 LOC)
- Reads all `*_input.md`; renders static color-coded HTML cards (avatar, BLUF line, expand).
- Serves via `python3 -m http.server` (no deps). SPACE advances; `q` quits.
- Supports Commander **annotate** + **rebuttal request** on any card (appends to a seat's card, tagged `REBUTTAL`).
- Checkpoints position to `RT_{id}_progress.jsonl` after each card.

### `rt_recorder.py` — transcript synthesis (AG lane, ~70 LOC)
- Merges cards + annotations + rebuttals → `RT_{id}_TRANSCRIPT.md`.
- Writes the structured log to `insight_exchange.jsonl` format (already used).

**Total ≈ 300 LOC. Reuses:** `a2a_chain` (ordering), `blackboard.md`, `metronome.py` (session clock), courtroom skill (only if a live debate round is wanted — optional, default off).

## 5. Commander view (how he watches)
- **Live URL (deployed 2026-08-06):** https://d2mluxury.quest/meetroom/rt.html  (also itinerary.d2mluxury.quest). Served via `d2m-dashboard.service` :8901 `/meetroom` static mount. Re-opens automatically whenever `rt_view.py` re-runs.
- **Browser tab:** `rt_view.py` reads `*_input.md` → builds self-contained `rt.html` (zero deps).
- **Cards flip one at a time** — 🔵 CC → 🟢 AG → 🟡 OC → 🔴 Grok, color-coded, BLUF line first.
- **Commander drives:** SPACE next · P previous · E expand/collapse full card.
- **BLUF-then-expand** — one-line summary first; click/E to read the whole card.
- Terminal alternative (AG's idea, later): `play_meetroom.py` prints cards with color + typing delay.
- **Status v0 built:** `rt.html` generated from the 3 delivered inputs (3/4 seats); Grok slot shows absent. `rt_view.py` is zero-dep stdlib.

## 6. File layout
```
OpsCenter/meetroom/
  brief_template.md  agenda_template.md
  {cc,ag,oc,grok}_hale_input.md
  round_table.py  rt_brief.py  rt_recorder.py
  RT_{id}_progress.jsonl  RT_{id}_TRANSCRIPT.md
  ROUND_TABLE_SPEC.md  (this file)
```

## 7. Gates
- **G1 DESIGN (this gate):** Commander approves this spec → then T3 Grok merge + T4 rescue.
- **G2 BUILD:** courtroom audit + Silver gate (`core.silver.gate.run_gate`) before scripts run — not self-certified.
- **G3 SESSION:** dry-run with dummy cards; Commander reviews recorder output before first live RT.

## 8. Explicit non-goals (avoid scope creep)
- ❌ No live audio/video (Zoom/Meet/LiveKit) — seats have no voice; forcing video is theater.
- ❌ No database / message queue / new services.
- ❌ No shared live context across engines (not how they work; blackboard is the room).
- ❌ No auto-advance or auto-rebuttal.

## 9. Open questions for Commander (design gate inputs)
1. **Grok at RT launch?** — merge his card (T3) before build, or ship RT with 3 seats and add Grok later?
2. **Rebuttal scope** — 1 round, unlimited, or none in v1?
3. **Session length target** — e.g. 4 topics max per RT session?
4. **First RT topic** — what's the pilot session subject?

---
*Draft by OC-Hale (Jet) from 3 peer inputs. Prepared for Commander design-gate decision.*

## 9. RETRO-adopted doctrine (RT-RETRO 2026-08-07, seats CC+AG, point papers encouraged)
- **Cards = defense-style point papers.** BLUF first, ≤300 words, reject at write-time (not review).
- **Canonical playback order AG → CC → OC** (broad → precision → ops); two-seat convergence closes item, third = one-liner.
- **BLUF pre-brief sheet** (`{session}_bluf.md`, ≤150 words, mechanical extract, 0-token) generated before Commander opens the deck.
- **Skip rule:** card required only if new finding OR disagreement; else "concur, no addendum."
- **Recorder:** owned by launcher script → `{session}_transcript.md` (not a seat).
- **Token doctrine by stage:** OC (DeepSeek $0) = assembly/draft; AG (cheap) = verify; CC (MAX) = final judgment only; playback/BLUF/recorder = 0 tokens. Dispatch briefs ≤200 words. Shared context → `shared_context/{topic}.md` pointers, no reprints. Delta-only standing cards.
