# RT-CI — COORDINATION PLAN: War Room re-routing of the CI point paper
## Hale-OC (Jet) · brought before the room, not solved by it · 2026-08-07
**Corrects:** the 2026-08-07 unilateral OC point paper (CI_WAR_ROOM_POSITION_PAPER_20260807.md) was executed outside the Room. Those 5 recommendations stand and are Commander-approved, but the migration/registry actions will NOT be run by OC alone — they pass through the War Room to the seats. This file is the plan.

**Sources:** WAR_ROOM_STANDING.md (Authority · Session mechanics · Dispatch ladder · Limit governor) · ROUND_TABLE_SPEC.md (RT-RETRO doctrine) · rt_dispatch.py · generate_rt_bluf.py · rt_recorder.py

---

## BLUF
CI tiering is a **provision/change to Wing config** = a **mandatory War Room subject**, not an OC deliverable. I will convene **RT-CI** and run my five recommendations through the canonical **AG → CC → OC** seat order; two-seat convergence closes each item; OC (me) assembles the deck at $0 and records — I do **not** decide or declare done. My solo point paper stands only as the agenda card set. **Headroom guard:** I assemble once, seat-converge once, then hand the registry migration to the agreed owner — no OC single-threading the build.

---

## 1. Why I must run this through the Room (self-audit)
| War Room rule | What I did wrong |
|---|---|
| Need-all-other-HALE for prov/change | I, OC, alone produced + proposed the CI tiering change |
| AG → CC → OC; two-seat closes | I wrote one OC card, no AG/CC input, pre-adopted the verdict |
| Preview-mandatory before deck | No RT-CI session, no bluf.md |
| Doc-mandatory: brief · seat cards · transcript · decision | Standalone .md only, no per-seat cards / transcript / receipts |
| OC assembly is the D-gate, not a verb | I shipped recommendation + DECISION together |

## 2. The RT-CI session — exactly how I'll run it
1. **Assemble agenda (OC, my $0 job):** one `RT-CI_brief.md` whose cards are the 5 point-papers already Sir ≈   Each ≤300w, BLUF-first (per ROUND_TABLE_SPEC §9).
2. **Preview (mandatory):** `generate_rt_bluf.py` → `RT-CI/RT-CI_bluf.md` (≤150w) **before** opening any deck. You see it first.
3. **Dispatch to seats, using the file-backed room, no live cross-engine:**
   - **AG → Gemini 3.6 Flash** `rt_dispatch.py AG "<card>" --deliverable …/ag_hale_input.md` — broad validate/contest of the tiering + parings + owner map; home for TacTics/bearing.
   - **CC → Claude Sonnet (MAX, local)** `rt_dispatch.py CC "…"` → `cc_hale_input.md` — final judgment on tier destructions, REPLACE storm, owner assignment (deep).
   - **OC →** file my own `cc->_input.md` LAST, as a peer card — not to overrule either seat.
4. **Two-seat convergence closes an item;** third seat = one-liner concur. (Me)
5. **Recorder:** `rt_recorder.py RT-CI` → `RT-CI_transcript.md` + progress.jsonl (receipts/ATO per seat).
6. **Decision to you (Commander-arbiter) → commit.** Registry migration runs only after the seats converge AND you re-node the note.

## 3. Head-of-the-Room load control (per limit-governor + RDD)
- OC assembles + records only ($0); seat edit costs land once per engine (AG/CC, not re-run).
- Dispatch ladder: OC form → **Haiku relay/synthesize** → **Sonnet final** — not Sonnet-everything (HEAD: keep MAX spend to judgment).
- 200-word brief budget; `shared_context/CI…` pointers, **delta-only** (no reprint of the SO/registry).
- RDD: AG+CC cards back within 24h → record transcript → verify registry → commit. Explicit RDD attached at dispatch.

## 4. Deliverables / hard artifacts (files, not chat)
- `OpsCenter/meetroom/RT-CI/RT-CI_brief.md`
- `OpsCenter/meetroom/RT-CI/RT-CI_blud.md`
- `OpsCenter/meetroom/RT-CI/{ag,cc,oc}_hale_input.md`
- `OpsCenter/meetroom/RT-CI/RT-CI_transcript.md` + `RT-CI_progress.jsonl`
- Guide to Commander: **`hale_decisions.md`** logs your approval of the 5 reccof and this process correction (hard rule 2026-08-07).

## 5. NEXT MOVE
I don't open the room or migrate the registry until you give me **GO to run RT-CI**. On GO I: (1) build deck + bluf, (2) dispatch AG→CC→HD, (3) record, (4) return a two-seat-converged verdict — then registry runs under CC/A7 code review, not OC-solo.

— V. Hale, VCS (Hale-OC) · plan 2026-08-07 · awaiting GO