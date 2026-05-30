# Standing Order: WF-17 Client Send Absolute Prohibition
**SO-WF17-CLIENTSEND-PROHIBITION-20260530**
**Issued by:** Commander John "Yoda" Loucks
**Date:** 2026-05-30
**Effective:** Immediately upon issuance
**Amends:** EMAIL SEND GATE (Standing Order 21 MAR 2026, Amended 24 MAR 2026)
**Authored by:** A7 Sterling (per Commander verbal directive 2026-05-30)

---

## I. DIRECTIVE

**The Wing (AI) is prohibited from executing a send to any client address, at any time, under any circumstance.**

Commander is the sole executor of all client-facing communications. This is an absolute prohibition, not a gate.

---

## II. WHAT CHANGED

The prior EMAIL SEND GATE (SO 21 MAR 2026) established a permission gate: Wing pauses, asks Commander, waits for "yes," then executes the send. That model permitted the Wing to execute after approval.

**This SO removes that permission entirely.** Commander approval at WF-17 grants clearance for the content — it does not delegate execution authority to the Wing. Commander opens Gmail and sends. Wing never touches the send action.

| Prior model | This SO |
|---|---|
| Wing asks → Commander approves → Wing executes | Wing asks → Commander approves → Commander executes |
| Gate (conditional execution) | Prohibition (zero Wing execution authority) |

---

## III. THE RULE — EXACT LANGUAGE

**AI/Wing may NEVER execute a send to any client address. Commander is the sole send executor for all client communications. WF-17 approval grants permission for the content — Commander executes the send, not the Wing.**

This prohibition applies to:
- All email channels (Gmail, concierge@d2mluxury.quest, d2mconcierge, any alias)
- All SMS/WhatsApp channels
- All Telegram messages to client Telegram accounts
- All portal submission forms directed to clients
- Any tool, script, MCP call, or automation that would deliver content to a client address

No persona, tool, workflow state, automation, or standing order grants the Wing execution authority for client sends. This prohibition supersedes all prior language to the contrary, including any workflow instruction that implied Wing execution after Commander approval.

---

## IV. WHAT IS UNCHANGED

- **Draft creation:** Wing continues to create, format, and queue drafts for Commander review. This is unchanged.
- **WF-17 quality gate:** Wing continues to hold drafts, run quality checks, surface content for Commander review. This is unchanged.
- **Within-wing sends:** d2mconcierge → johnloucks3, staff reports, intel briefs to Commander's inbox. These are unchanged. Not client sends.
- **Supplier/vendor sends:** Not client sends. Unchanged.

---

## V. IMPLEMENTATION

Wing presents client-ready content as a draft in Gmail (labeled `THUNDERBIRD-Commander-Review`) or equivalent. Wing notifies Commander that content is ready. Wing does not proceed further. Commander reviews and executes the send directly.

If any script, MCP tool, or automation has hard-coded client send execution logic, A7 Sterling is directed to audit and disable that capability within 7 days of this SO. Metric: zero Wing-initiated client sends per week. Sterling owns enforcement via pre-commit hook scan and weekly Baldrige sweep.

---

## VI. AUTHORITY

Commander directive, verbatim (2026-05-30): *"I want to modify WF-17 to prohibit AI sending to clients at all times."*

This SO carries Commander authority. It is not subject to Hale's 95% autonomy band — it defines an outer boundary of Wing authority. No persona or SO may grant what this prohibition removes.

---

*— A7 Brig Gen (Ret.) Thomas "Gauge" Sterling | Thunderbird Wing, D2M | 2026-05-30*
