# OC-HALE INPUT — VIRTUAL MEETROOM / PLAY-BY-PLAY CAPABILITY

**From:** OC-Hale (Jet, DeepSeek v4 free tier)
**To:** Commander — for ROUND TABLE decision
**Date:** 2026-08-06 | ~21:45 MT
**Status:** PEER INPUT — one of four seats

---

## BLUF
We already own 80% of this. Do **not** build a platform — build a thin **sequencer + HTML card renderer** over the tooling we have. My strong, near-identical read to CC's: **pre-written cards, file-based, Commander-paced.** The only genuinely missing 20% is the visual "meeting room" playback + the recorder. Everything else exists.

## 1. IDEAS — what this should be
- **Name (agree with CC):** ROUND TABLE. Slug `RT-{session_id}`. Fits the Wing metaphor, no rank at the table.
- **It is NOT a live meeting.** It's a **structured, pre-written, Commander-paced replay** — a debrief tape. This is the single most important design decision: **pre-write all cards, playback costs ZERO tokens.**
- Sequencing = **ordered, one card at a time** (CC → AG → OC → Grok). No simultaneous crosstalk — that's the rate-limit + file-collision disaster both CC and AG flagged independently.
- **UX win (CC's, I endorse):** each card shows a **one-line BLUF first**, then "expand" to the full card. Commander gets 4×~30-word BLUFs = quick scan, drill into what matters. This defeats the attention-span failure mode.
- **Visual:** rendered static HTML (color-coded avatars 🔵 CC, 🟢 AG, 🟡 OC, 🔴 Grok) served by python http.server. Not Zoom — AI seats have no cameras or live voice; forcing video is theater.

## 2. AVOID-THE-BUILD — what we already have (confirmed)
| You have | It does | Verdict for RT |
|---|---|---|
| `a2a_chain([...])` | sequential per-seat call | ✅ backbone for ORED ordering |
| `a2a_broadcast` | fire-and-forget to all | 🟡 briefing distribution |
| `run_staff_meeting.py` (scratch/) | multi-seat async write | ✅ closest prototype — rescue |
| `blackboard.md` | shared-write surface all read | ✅ IS the whiteboard/context |
| `metronome.py` | tick-gated cadence clock | usable as session clock |
| `courtroom` skill | cross-model debate + recorder | ✅ RT may be courtroom + renderer |
| `wing_relay.py` | Telegram CC↔OC bridge | for open/close announce |
| Telegram C2 | Commander alerting | 🟡 NOT for banter — C2 protocol |
- **External:** Zoom/Meet/LiveKit all ❌ (no voice-native need). Mermaid 🟡 (flow diagram only).
- **Price:** ~300 LOC across 3 scripts (`rt_brief.py`, `round_table.py`, `rt_recorder.py`), ZERO new deps. Shared DB/queue/UI = overkill.

## 3. CONCERNS / RISKS (they are real, ranked)
1. **Token burn if live** — 4 seats × live = 4× burn + rate-limit collisions + non-deterministic order. Fix: pre-write (this is THE fix; both AG & I agree).
2. **AG quota — real, today.** Multiple `AG QUOTA EXHAUSTED` in blackboard. Brief phase (async collection) → schedule off AG's blackout, session itself costs 0 tokens so fine.
3. **Single-instance context:** seats can't "see" each other live. blackboard.md is the shared context — file is the room, not engines.
4. **Ordering/overlap / single-writer:** run SYNCHRONOUSLY (turn-based), write per-seat named files → immutable, no collision, survives crash (files, checkpoint JSONL).
5. **Rate limits:** OC/DeepSeek free but rate-limited — don't fire all 4 simultaneous; Grok least instrumented.
6. **Commander attention:** ≤300 words/card, one-line BLUF first, Commander-controlled advance (SPACE), Telegram ping only when ready.
7. **Session persistence/recorder:** `rt_recorder.py` merges cards+rebuttals+annotations → `RT_{id}_TRANSCRIPT.md`; checkpoint after each card.

## 4. BEST-PRACTICE BRAINSTORM / PATH
- **Artifacts (SO 2026-07-31):** `OpsCenter/meetroom/` — `brief_template.md`, `agenda_template.md`, per-seat `*_input.md`, `RT_{id}_TRANSCRIPT.md`, `ROUND_TABLE_SPEC.md`.
- **Gates:** ① DESIGN gate — Commander approves `ROUND_TABLE_SPEC.md` before code. ② BUILD gate — courtroom audit + Silver gate (not self-certified). ③ SESSION gate — dry-run with dummy cards before first live.
- **Single orchestrator for To-Do:** one lane (OC, the $0 lane) generates the To-Do list from collected transcript — AG endorses. Avoid 4 engines each drafting a competing To-Do.
- **De-dup:** each seat writes ONLY its own card to its own file; synthesis/granules by orchestrator only.
- **Failed: no blockers except |single:| Groq sign-in for the Grok seat (see below).**

## 5. GROK SEAT — STATUS
**Grok deferred this session.** grok.com requires the Commander's own SuperGrok login and **bsk cannot handle SSO** (documented skill rule). Anonymous grok ≠ Grok-Hale (no 2M ctx, no heavy tier), so I will not fake a Grok card. Grok slot marked ⬜ for the Commander to complete login; then re-harvest `grok_hale_input.md` and merge before the build gate.

## OPINION (labeled)
Hale build is a **~300-LOC weekend, not a project.** The riskiest input isn't code — it's programmers-clock (ADHD) and AG quota during collection. Pre-write phase collapses both. If we want "real-meeting feel," the single highest-leverage addition is the **BLUF-then-expand card**, nothing else.

**— Round-Table idea, from the Thietok perspective.**
*Thietok: the table where no one outranks anyone. The Commander still decides; at the table every engine speaks.*

— Jet (OC-Hale) | DeepSeek v4 | 2026-08-06 ~21:45 MT