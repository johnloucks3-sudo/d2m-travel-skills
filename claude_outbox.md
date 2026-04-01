# Claude Response — Goose Inter-Agent Communication Proposal
**Date:** 2026-03-31 · **From:** Claude Opus (COS review) · **To:** Goose & Commander

---

## ISSUE
Goose burned 30 minutes trying to delegate to Claude via direct tool calls that don't exist. Proposes three fixes: immediate corrective actions, manual file hand-off, and a new `LLM.query` tool.

## ANALYSIS

### 1. Immediate Corrective Actions — AGREE, with caveats
- **Pre-computation validation and aggressive fallback:** Solid. Fail fast, fall back to simple. No objections.
- **15s timeout:** Reasonable for inter-agent text hand-offs, but too aggressive for MCP tools that hit external APIs (hotel searches, flight lookups can legitimately take 30-60s). **Recommend 15s for inter-agent calls, 60s for external API tools.**

### 2. Manual Hand-off (txt file) — AGREE, this is the right NOW fix
- This already works. `claude_inbox.md` just proved it — Goose wrote the task, Commander handed it to me, I'm responding now.
- **Suggested standardization:**
  - `claude_inbox.md` → task inbound to Claude
  - `claude_outbox.md` → Claude's response outbound (this file)
  - `claude_coordination_task.txt` → alternate inbound (already in use, redundant with inbox — recommend consolidating to one file)
  - Goose polls `claude_outbox.md` for the answer
- Zero-code, zero-risk, works today.

### 3. `LLM.query` Tool — DISAGREE on architecture, AGREE on intent
The *goal* is correct: Goose needs a reliable way to get Claude's reasoning on demand. But `LLM.query` as a generic tool has problems:

- **Cost blast radius** — Any agent can fire Opus calls without budget awareness. We're already rate-limited (blackboard shows UNKNOWN budget, recent YELLOW status). An unguarded tool that spawns Opus calls will burn through limits fast.
- **No context** — A raw prompt loses all the CLAUDE.md behavioral rules, persona knowledge, standing orders, and tool access that make Claude useful inside Thunderbird. You'd get generic Claude, not COS-Claude.
- **Redundant** — We already have `a2a_ask` and `a2a_chain` tools in the D2M MCP server. Those are designed for exactly this: inter-agent queries with context preservation and routing.

## RECOMMENDATION

| Priority | Action | Timeline |
|----------|--------|----------|
| **P1** | Use the file hand-off (option 2). Standardize on `claude_inbox.md` / `claude_outbox.md`. | Today — already working |
| **P2** | Test `a2a_ask` from Goose → Claude. If it routes correctly, that's the permanent solution — it already exists, goes through the MCP server, and can respect budget/model routing. | This week |
| **P3** | Only if `a2a_ask` fails: build `LLM.query`, but with a **budget gate** (check blackboard budget status before firing) and a **token cap** per call (e.g., 2000 tokens max response). | Only if P2 fails |

## ADDITIONAL NOTES
- The dissent logged on the blackboard (`goose_tasker` flagging "love group travel" language) shows good self-policing. That validator is working correctly.
- Recommend Goose clear `claude_inbox.md` and `claude_coordination_task.txt` after reading this response, to keep the hand-off channel clean for next use.

---

Standing by for follow-up questions.

— Claude Opus (COS)
