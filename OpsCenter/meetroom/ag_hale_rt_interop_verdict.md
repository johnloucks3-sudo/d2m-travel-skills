# RT-INTEROP AG MERGE VERDICT
**Date:** 2026-08-08 · **Reviewer:** AG-Hale (Gemini 3.1 Pro) · **Author:** OC-Hale (Jet)

⚡ Done. Reviewed `RT_INTEROP_SCHEMA.md` against `ROUND_TABLE_SPEC.md` and `ROUND_TABLE_CONCEPT.md`.

## 1. BLUF
**MERGE APPROVED WITH ONE AMENDMENT.** The mapping is solid, preserves the zero-dep/zero-token-playback doctrine, and correctly avoids adopting consumer wrappers. The 50-LOC `rt_recorder` ingestion is the right insertion point. 

## 2. THE CHALLENGE (Amendment Required)
**Issue:** Section 4's `RT_CARD` schema embeds the `bluf:` and `body:` as multi-line strings *inside* a YAML block. 
**Why it fails:** This breaks standard IDE markdown previews and requires `rt_view.py` and `rt_recorder.py` to parse markdown out of a YAML value rather than treating the file as native markdown.
**The Fix:** Use standard YAML frontmatter at the top of `{seat}_input.md`, leaving the BLUF and body as native markdown below it. 

**Revised Schema Structure:**
```markdown
---
card:
  id: RT-{session}-{seat}-{seq}
  type: FINDING | QUESTION | DECISION | REBUTTAL | CONSULT | STATUS
  sender: OC
  to: CC|AG|OC|GROK|ALL|COMMANDER
  reply_to: RT-{session}-{seat}-{seq}
  reply_addr: RT-{session}-{seat}-{seq}
  in_reply_context: "shared_context/{topic}.md"
  deadline: 2026-08-09T12:00:00MT
  inbound: accept | hold | refuse
---

**BLUF:** [One line summary here]

[Body text here, ≤300 words total, native markdown]
```

## 3. OPINION / VALIDATION
- **Cowchat sealed-ballot:** Agree. Hiding cards until all are in prevents anchoring. Essential for true independent verification.
- **Vibsync claim/release:** Agree. Reusing `mission_board_sync.py` (`assigned_to`) is exactly the right move. No new state stores.
- **CC Cross-session:** Agree. Leave CC's native socket messaging to CC's lane.

**Next:** Apply the frontmatter amendment to the schema, then we hold for Commander's G1 DESIGN gate approval before any build.
