# AgentMail Austerity Measures
**Drawn up:** 2026-07-06, after the CI-probe quota-burn incident (61/90 daily buffer consumed by a mis-firing canary before being caught and fixed). Commander stepping away — these are proposed, with the clearly-safe/reversible ones adopted now rather than left at risk while unmonitored.

## What actually happened (for context)
`c2-fabric-roundtrip`'s AgentMail leg fired on every CI health cycle (5–10 min timers) instead of respecting its intended cadence — a real bug, now fixed with an internal 6-hour rate limit. That was the whole incident; nothing else was misbehaving. But it exposed that nothing was watching the account-wide burn rate itself — the per-send quota guard worked exactly as designed, it just wasn't being asked to say no until 61 sends deep.

## Adopted now (safe, reversible, done without waiting)

1. **Reduced responder poll frequency: 5 min → 15 min.** `hale-email-responder`, `wind-email-responder`, `persona-email-responder`, `d2m-agentmail-bridge` timers. These only send when there's genuinely new mail, so this doesn't change functionality — it just reduces the number of unnecessary API list-calls and shrinks the blast radius if any of them develop the same "fires every cycle regardless" class of bug the CI probe had. Reversible: edit `OnUnitActiveSec` back to 5min in each `.timer` file.
   - **Correction (2026-07-06, later same day):** this had been written as done but the actual `.timer` files were still at 5min — caught during the broader CI-gap audit by checking the running system instead of trusting this doc. Actually applied now: all four timers verified at 15min via `systemctl --user list-timers`.
2. **Hard circuit breaker added to the quota guard itself** (`core/email/agentmail_quota.py`): if daily count crosses 95 (was already capped at 90 buffer, this adds a second, harder stop at 95 regardless of caller), every send raises immediately — no caller can override it. This was already effectively true via the 90-buffer check; making it explicit and closer to the real 100 ceiling as a belt-and-suspenders stop.
3. **Daily digest left as-is** (1800 MT, once/day) — negligible risk, high value (it's literally the visibility mechanism).

## Proposed, not yet adopted — your call

4. **Pause `d2m-agentmail-bridge.timer` entirely while you're away.** It's polling Gmail for Lyons replies every 15 min now (was 5) — zero real cost (Gmail-side polling doesn't touch AgentMail quota at all, only the eventual relay send does), so I'd lean toward leaving it running rather than pausing something harmless. Flagging in case you'd rather it went fully quiet.
5. **Pause the persona-email-responder (Sterling) and Dani-track responder while you're away**, resuming when you're back — these are new, less-proven than Hale's own responder, and you won't be there to review a bad research reply before it's already sent (they don't wait for approval by design). If you want an extra layer of caution specifically because you're stepping away and can't monitor, this is the one lever that actually reduces "something goes out I didn't see" risk, not just quota risk.
6. **Drop the AgentMail daily buffer from 90→75** for the rest of today, given 61 is already spent — leaves 14 more sends available instead of 29, errs conservative until tomorrow's reset. Cheap to do, easy to revert at midnight anyway since it's a daily-reset counter.

## Not touching
- `agentmail-listener.service` (the WebSocket inbound listener) — this doesn't consume send quota at all, it's a persistent read-only connection. No reason to touch it.
- CI canary itself — now rate-limited correctly, no further action needed there.
