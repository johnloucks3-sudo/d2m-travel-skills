# Telegram vs AgentMail — Rules of Engagement
**Built:** 2026-07-06 · Staff: Sterling (dividing line + rules), Dembe (risk), ELON (adoption) · Commander examples incorporated and one race condition in them fixed

## The dividing line (Sterling)
**Durable artifact vs signal.** Anything with substance the Commander re-reads (proposal, research reply, draft) is an AgentMail artifact. Anything that's just a nudge (notify, ack, status, "look now") rides Telegram. Quota is a constraint on this, not the rule itself.

## The five rules

1. **Content on email, control on Telegram.** A deliverable with substance lives on AgentMail; Telegram carries a pointer to it, not a copy.
2. **Notify-and-wait is always Telegram** — matches your own example (b): "Hale here, sent a proposal to johnloucks3, executing in 5 min unless you object." Push beats poll for a latency-sensitive gate.
3. **One thread, one medium — hand off deliberately, never by accident.** Matches your example (a): if a live email exchange is running long, Hale says explicitly "continuing on Telegram" and stops opening new email threads. Silent channel-switching is the #1 confusion source.
4. **Daily digest rides Telegram, sourced from the AgentMail log** — matches your example (c). The summary is a signal; the underlying items stay retrievable in email.
5. **The five named-waiver correspondents never route through Telegram.** Quota there is mission-critical (real client/friend correspondence) — internal chatter can't be allowed to starve it.

**Metric:** cross-channel context-miss rate — Commander replies asking "where/what is this?", target <2% of messages. Reviewed weekly in the Baldrige sweep. Quota headroom is a secondary guardrail, not the success measure.

## The bug your own example (b) had — found and fixed, not just noted

Dembe's read: *"the riskiest pattern in all three examples, because it's the only one where a missed signal causes an action, not just a missed read."* If a proposal is sent by email and the countdown runs on Telegram, your natural instinct is to reply "no" **in the email thread** — that's where the content lives. A timer only listening on Telegram would never see it, and would execute anyway.

**Fixed in `core/ops/confirmed_auto_execute.py`:** the notify-and-wait timer now checks BOTH channels every poll cycle — a reply in the email thread kills the timer exactly as fast as a Telegram reply. Not an end-of-day digest catching it after the fact (Dembe rated that LOW-MODERATE confidence for a same-day 5-minute miss) — real-time, both listening posts, one clock.

## What did NOT need building
Nylas or a similar multi-provider tool (ELON's finding): Hale already has Google Calendar via the existing Workspace MCP tools, on a separate rail from AgentMail. AgentMail's whole value proposition over Nylas is "you don't have calendar access elsewhere" — we do. Adopting a second platform to solve an already-solved problem would be churn, not leverage. Not recommended.
