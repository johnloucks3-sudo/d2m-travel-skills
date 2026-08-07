# WAR ROOM — STANDING DOCTRINE (Commander directive 2026-08-07)
**Status:** ⚡ STANDING / always-up · owner: all HALES · gate: none beyond the 3 standing gates

## Authority
- **War Room is 24/7 standing capability.** Not a one-off event — it is the default forum for cross-HALE work.
- **Commander directs WHEN it runs** (he says "use the war room for X").
- **ANY HALE may INVOKE it** — OC, CC, AG, or Grok (once logged in) can open an RT session for any task, any issue, any new provision or change. No permission needed to open a session; the Commander is always the arbiter in the room, never a seat.
- **Mandatory War Room subject:** the recurring **OC auto-logoff** issue, and **ALL new provisions and changes** to Wing systems/config.

## Session mechanics (per RT-RETRO doctrine)
- Per-seat point papers (BLUF-first, ≤300 words) → file-based `OpsCenter/meetroom/{session}/`
- Canonical order **AG → CC → OC**; two-seat convergence closes an item (third = one-liner)
- **BLUF pre-brief** generated before Commander opens the deck (0-token)
- Skip rule for consensus; recorder-owned transcript `{session}_transcript.md`
- Token doctrine: OC assembles ($0) · AG verifies (Gemini 3.6 Flash) · CC judgment (Sonnet 4.6) · playback/BLUF/recorder = 0 tokens

## Standing agenda (always live in the War Room)
1. **OC auto-logoff debug + repair** (MISSION-794) — in session now
2. OpenCode GO vs ZEN decoupling (GO funding must not gate ZEN free lane)
3. Any new provision / configuration change → open an RT session first
4. Weekly token-cost + limit review

## Record
- Sessions under `OpsCenter/meetroom/RT-*`
- Commander directives logged to `hale_decisions.md`
- Missions on board (`MISSION-786` base, `794` logoff, `795` telegram 24h)

— Victory · standing 2026-08-07
## HARD RULE — DOCUMENTATION MANDATORY (Commander 2026-08-07)
- Every War Room session MUST produce: brief · per-seat inputs · consolidated transcript · decision/verdict · committed to git. **Never** chat-scroll-only; a session with no durable artifact did not happen.
- Every new provision / configuration change MUST be documented (what, why, file:line, owner, date) before/with execution.
- Record all Commander directives and Weapons-Free decisions to `hale_decisions.md`.
