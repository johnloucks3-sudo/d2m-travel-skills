# RT-RETRO — War Room process retro (transcript)
**Seats:** CC ✅ AG ✅ ~~Grok~~ · **Date:** 2026-08-07 · **Commander adds:** point papers encouraged

## 1. How it's working for the HALES
- ✅ **Works:** pre-written async cards (zero-token playback), ≤300-word discipline, recorder→transcript, empty-seat-over-fabrication, cross-engine signal via contact_ag.
- ❌ **Friction:** replaying full static context each round burns windows; sequencing/order not explicit (anchor bias — first card sets the frame); no BLUF pre-brief (Commander reads cold); recorder ownership vague; no "skip" rule → consensus still spawns full cards.

## 2. Consensus changes (both seats converged)
1. **Canonical playback order:** AG (broadest sweep) → CC (precision) → OC (ops). Don't put OC-concurrence). Rule: two seats converging closes the item; third becomes one-liner.
2. **Point papers encouraged → mandatory BLUF pre-brief** before Commander opens the deck: a ≤150-word 1-page BLUF sheet (`{session}_bluf.md`, mechanical extract, 0-token) so he's oriented before cards hit. Point papers (BLUF-first) are the canonical card shape.
3. **Skip rule formalized:** card required only if (a) new finding not covered, or (b) direct disagreement; else one-liner "Seat X: concur, no addendum."
4. **Recorder ownership:** lock to `OpsCenter/meetroom/{session}_transcript.md`, auto by the launcher script (not a seat).

## 3. Token-minimization (consensus → doctrine)
- **Briefs, hard at artifact level:** card ≤300 words (reject at write); BLUF sheet ≤150; inter-engine dispatch ≤200 words.
- **Lanewire cheapest stage:** OC (DeepSeek, $0) = data assembly/drafting · AG (Gemini, cheap) = verification · CC (Claude, MAX) = ONLY final gated judgment. Playback + BLUF + recorder = 0 tokens.
- **De-dup:** shared context once in `shared_context/{topic}.md`; cards carry pointers not reprints; standing items = delta-only cards; reuse across sessions.
- **Skip logic:** consensus → one-liners, don't pay for third re-statement.

## Commander's additions
- **"Point papers encouraged"** → encode: every seat card IS a defense-style point paper (short BLUF first). Standing doctrine.

## Adopted process deltas (encoded into ROUND_TABLE_SPEC.md)
- Canonical order AG→CC→OC · BLUF pre-brief sheet auto-gen (0-token) · hard card/decode caps at write-time · skip rule · recorder owned by launcher · OC data-assembly-first, AG/CC only for judgment.

— Victory | RT-RETRO · committed to War Room doctrine