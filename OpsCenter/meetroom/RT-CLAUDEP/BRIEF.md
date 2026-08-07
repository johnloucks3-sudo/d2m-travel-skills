# RT-CLAUDEP — fix headless `claude -p` + `/ask` routing
**Opened:** 2026-08-07 · **Seats:** CC ✅ AG ✅ ~~Grok~~ · **Status:** IN SESSION
**Problem (known):**
- Headless `claude -p` (via `brain_bridge`, MCP `headless_claude_task`) HANGS on this box (documented: claude CLI hangs 48h+; MCP spawn just timed out). The MAX headless lane is effectively broken → blocks the OC→Haiku→Sonnet ladder.
- `/ask`-family confusion (ask/ask-opus/ask-haiku names vs actual routing; Sonnet 5 not exposed; agy only shows sonnet-4-6/opus-4-6).
**Ask each seat:**
1. Why does `claude -p` hang here (evidence: OAuth token? timeout? TTY? sandbox)? How to fix so headless Haiku/Sonnet reliably return (env, flags, timeout, spawn pattern)?
2. What is the correct `/ask` family (names → real destination) and how to make names match behaviour?
3. Best headless dispatch pattern on this box (given brain_bridge documented-broken): direct `claude -p`, cc-fleet, contact_ag Claude, or other.
4. Min fix set (file:line) with stdlib-only changes.
