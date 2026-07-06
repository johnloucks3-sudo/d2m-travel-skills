# AgentMail — Bold Uses & OBE Audit
**Date:** 2026-07-06 · Prompted by Commander: "let's be proactive... be bold. Then determine if any current capability becomes OBE."

---

## PART 1 — BOLD, PROACTIVE USES (not yet built, worth considering)

**Cross-engine native conversation.** CONDOR and WIND now have their own email identities. Instead of (or alongside) `brain_bridge.py`'s file-based claim board, they could literally email each other — "CONDOR: can you research X" / "WIND: here's what I found, attached the data." Richer than a claim-board entry, threads naturally, carries attachments. (ELON's caution below: don't replace the claim board's concurrency guarantee with this — use both, for different jobs.)

**Direct persona-to-Commander correspondence.** Once inbox capacity allows (Developer tier or a second provider), Sterling, Dembe, Harlan, Reyes could each get a real address. Commander emails "Dembe" directly and gets a genuinely researched reply in that persona's voice — not routed through a Claude Code session first. This is the multi-persona CC roster already flagged as a capacity/cost item, now with a concrete payoff worth naming.

**Rich incident/alert email instead of terse Telegram pings.** CI failures, credential expirations, fare-watch drops — anything currently a one-line Telegram alert could instead be a real email with the actual log excerpt, a screenshot, or the diff attached. Telegram stays for the "look now" ping; the substance rides email.

**Supplier/vendor correspondence for trusted relationships** — within Hale's existing vendor-contact authority (transactional/informational, not commitment-making). Caveat: `@agentmail.to` is a cold domain for external commercial correspondence; this is better suited to relationships that already trust the Wing (not cold outreach) until a verified custom domain exists.

**Extend the Bryana gift-tier pattern to other "friends I'd serve for free" relationships** — the mechanism (named-waiver + Hale-voice + real tool access) is now proven and reusable. Each new person is a small, known cost (WF-17 waiver entry + inbox capacity check), not a new build.

**Scheduled digests beyond daily** — the ROE's daily-Telegram-digest-of-AgentMail-activity pattern generalizes to weekly/monthly rollups, competitive intel summaries, anything currently manually compiled.

---

## PART 2 — OBE AUDIT (ELON, Weekly Kill Audit lens)

### Confirmed OBE — killed same session
- **`scripts/send_cruise_tool_v2.py`, `scripts/render_nancy_lyons_email.py`** — the original hand-rolled Lyons send scripts, superseded by `wf17_named_waivers.py`'s single enforcement point. **Archived to `archive/retired_scripts/`.**
- **Telegram long-form chunking (`tg_send_chunks`) for reports/briefs** — kill the *use case*, not the function. Long-form content (briefs, sitreps) has no reason to be sliced into 4096-char Telegram messages anymore; email carries it natively. Telegram chunking stays available for whatever still needs it, just isn't the default for long content going forward.

### NOT OBE — real traps, don't touch (ELON's explicit warning)
- **`core/hale_bus/brain_bridge.py` claim-board.** Looks replaceable by CONDOR/WIND emailing each other — it isn't. Email is a conversation channel; the claim-board is a concurrency primitive (atomic claim, no double-work, queryable ownership). Email has no lock semantics. Killing this because "they can just email" means two engines grab the same task and you find out when the diffs collide. Email can *notify* a claim; it can't *be* one.
- **Telegram as a channel entirely.** Already correctly scoped as a live bridge in the Channel Registry, but there's a sharper reason to keep it now: the confirmed-delivery auto-execute mechanism checks BOTH Telegram and email for a veto reply, in real time. Pulling Telegram halves the veto surface on the exact mechanism built today. Do not touch.
- **`core/email/d2m_agentmail_bridge.py` (Gmail→AgentMail relay for Lyons).** Not redundant with anything today — it's a patch for a real scope gap (no `gmail.settings.sharing` OAuth grant). Future kill candidate *only* once true Gmail-side forwarding is available, not now.

**Action items handed to Whetstone** (per ELON): confirm the two same-session kills are clean (no other references), fold the Telegram-chunking-for-long-content deprecation into CI doctrine this week.
