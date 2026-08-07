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

## STANDS — acquired from competitive scan (2026-08-06; adopt-ready, config-only)
Fold the best of the found tools INTO the War Room rather than importing their platforms:
1. **Receipts / attribution (from ATO):** every seat action carries a machine-readable receipt (seat, model, tool-calls, cost, file:line) appended to the session transcript — no claim without a receipt.
2. **Live shared room (from ATO):** when Commander wants real-time (not pre-write), allow a seat's card to append live during a session; tag `[LIVE]`; recorder still owns the final transcript.
3. **Kill-the-runaway (from ATO):** works in-scope on the playback deck — Commander `K` aborts the current card/session, `X` requests rebuttal. Documented in rt.html key map.
4. **Session replay/timeline (from AgentOps):** recorder emits a timeline of seat→model→tool per agenda item for diffing planned vs said.
5. **Structured debate rounds (from llm-war-room):** session may open a rebuttal round after all cards — Commander presides, seats re-file a `REBUTTAL` block on the card; recorder nets the disagree/agree.
6. **Web canvas fallback (from ChatDev):** if we want a maintained web WYSIWYG over our file deck, ChatDev 2.0 (already proto'd) is the backplane option. Do NOT adopt its platform wholesale.
Adopt = small config/code on our rtmp+R t deck; these are DOCTRINE, not new infra.

## 2026-08-07 ADDENDUM (Commander directives)
- **PREVIEW-MANDATORY:** every RT session (Commander- or HALE-invoked) MUST generate {session}_bluf.md preview BEFORE the playback deck opens. No preview = session not ready for playback.
- **DISPATCH LADDER (standing):** OC fills the standard form → **headless Haiku (MAX, lenient)** relays/synthesizes → **Sonnet** only for final judgment. OC data-assembles first (never sends raw work to Sonnet).
- **LIMIT GOVERNOR (per-seat):** each lane monitors its own TPM/RPH/RPD and, before dispatch, chooses REFUSE (hard if over) · ADVISE (proceed+flag) · GRACE (degrade to healthier lane / self-exclude). Wired via rt_dispatch.py.
- **BATCHING:** sequential seats share one brief round (shared context, ~15-25% dispatch-token savings); parallel seats share one parallel batch. Avoid N separate full re-briefs.
- **WAR ROOM to fix `claude -p` + `/ask`** routing (known broken: claude CLI hangs, ask-lane confusion) — OPEN RT-CLAUDEP.
