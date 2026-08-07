# ROUND TABLE — Virtual Meetroom / Play-by-Play Capability

**Project:** Enhanced virtual + visual interaction across the 4 HALE seats (CC · AG · OC · Grok)
**Status:** BRAINSTORM → CONCEPT (3/4 seats delivered; Grok deferred on Commander login)
**Date:** 2026-08-06 ~21:50 MT | Owner: Hale (this seat) · Build lane: TBD

---

## 1. BLUF
We already own ~80% of this. **Do not build a meeting platform.** Build a thin **sequencer + HTML card renderer + recorder** (~300 LOC, zero new deps) over existing A2A/blackboard/metronome/courtroom infrastructure. The core design call — agreed by all 3 delivered seats independently: **pre-written cards, file-based, Commander-paced.** Playback costs ZERO tokens.

## 2. The 3 delivered inputs (peer, cross-engine)
| Seat | Engine | Deliverable | Verdict |
|---|---|---|---|
| **CC-Hale** | Claude Sonnet 4.6 (Thinking) | `cc_hale_input.md` (192 lines) | ✅ Build ROUND TABLE, ~300 LOC, BLUF-then-expand UX |
| **AG-Hale** | Gemini 3.1 Pro | `ag_hale_input.md` (36 lines) | ✅ Reuse CLI dispatchers; JSONL transcript + terminal playback |
| **OC-Hale** | DeepSeek v4 (this seat) | `oc_hale_input.md` | ✅ Same read; single-orchestrator To-Do; BLUF-then-expand |
| **Grok-Hale** | xAI | ⬜ DEFERRED — grok.com login required (bsk cannot SSO) | merge before build gate |

**Cross-engine agreement (high confidence):**
- Pre-write all cards → playback is file reads → 0 token cost
- Ordered, one-at-a-time (CC → AG → OC → Grok); synchronous, single-writer per-seat files
- blackboard.md IS the meeting room (shared context); engines can't share live context
- Commander-paced (SPACE to advance); ≤300 words/card; color-coded avatars
- ~300 LOC, no new deps, no DB, no Zoom/LiveKit (AI seats have no voice — video is theater)

## 3. AVOID-THE-BUILD — what we already have (verified)
- **`a2a_chain([...])`** — sequential per-seat call = the ordering backbone
- **`a2a_broadcast`** — fire-and-forget = briefing distribution
- **`run_staff_meeting.py`** (scratch/FOR_DELETION/) — closest prototype; **rescue, don't delete**
- **`blackboard.md`** — shared write surface = the whiteboard
- **`metronome.py`** — tick cadence = session clock
- **`courtroom` skill** — cross-model debate + recorder; RT may be courtroom + renderer (<150 LOC if so)
- **`wing_relay.py`** — Telegram open/close announce
- **`wind_staff.py`** — named-seat dispatch; add a `round_table` mode
- External: Zoom/Meet/LiveKit ❌ · Mermaid 🟡 (diagram only) · shared DB/queue ❌

## 4. THE BUILD (if approved) — ~300 LOC, 3 scripts
```
OpsCenter/meetroom/
  brief_template.md          ← Commander fills per session
  agenda_template.md
  rt_brief.py                ← distribute brief to 4 seats (blackboard + wing_relay)
  round_table.py             ← sequencer: reads *_input.md → HTML cards, http.server, SPACE advance
  rt_recorder.py             ← merge cards+rebuttals+annotations → RT_{id}_TRANSCRIPT.md
  RT_{id}_TRANSCRIPT.md      ← post-session record
  ROUND_TABLE_SPEC.md        ← Commander-approved design spec (build gate)
```

## 5. To-Do List (promulgated for feedback)
| # | Item | Owner | Engine |
|---|---|---|---|
| T1 | Draft `ROUND_TABLE_SPEC.md` from 3/4 inputs | Hale/OC | DeepSeek (free) |
| T2 | Commander reviews spec → **DESIGN GATE approval** | Commander | — |
| T3 | Grok login complete → harvest `grok_hale_input.md` → merge | Commander + Grok | xAI |
| T4 | Rescue `run_staff_meeting.py` from scratch/FOR_DELETION | Hale/OC | DeepSeek |
| T5 | Build `rt_brief.py` (distribution) | JET (OC) | DeepSeek |
| T6 | Build `round_table.py` (sequencer + HTML viewer) | TALON (CC) | Claude |
| T7 | Build `rt_recorder.py` (transcript) | AG | Gemini |
| T8 | **BUILD GATE:** courtroom audit + Silver gate (not self-certified) | Sterling | — |
| T9 | **SESSION GATE:** dry-run with dummy cards; Commander reviews recorder output | Hale | — |
| T10 | First live ROUND TABLE session | Commander | — |

## 6. Risks (ranked)
1. Token burn if live-generated → **fix: pre-write** (all 3 seats agree)
2. AG quota exhaustion (confirmed today) → async collection off AG blackout; session itself costs 0
3. Commander attention (ADHD) → BLUF-then-expand + SPACE-pacing + ≤300 words/card
4. Ordering/overlap/single-writer → synchronous, per-seat immutable files
5. Grok instability → verify headless_grok_spawn first; manual fallback

## 7. Opinion
- **This is a weekend, not a project.** The one high-leverage addition is BLUF-then-expand cards.
- **Cheapest lane for orchestration:** OC (DeepSeek $0) — endorsed by AG and CC's ownership table.
- **Don't gate the whole build on Grok** — merge him at T3 before the build gate, not the design gate.
