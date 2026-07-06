# AgentMail Austerity Measures — Status
**Verified:** 2026-07-06 · Source doc: `docs/AGENTMAIL_AUSTERITY_MEASURES_20260706.md`

## Incident root cause
`c2-fabric-roundtrip`'s AgentMail leg fired on every CI health cycle (5–10 min timers) instead of respecting its intended cadence — consumed 61/90 of the daily buffer before being caught. Fix: internal 6-hour rate limit added in `scripts/ci_probe_c2_fabric_roundtrip.py` (`RATE_LIMIT_HOURS`, cached result served between windows). **Verified in place.**

## Three adopted measures

| # | Measure | Status |
|---|---|---|
| 1 | Responder frequency 5min → 15min | ✅ Active — installed timers verified 15min; **repo `deploy/*.timer` source files were still at 5min (drift), corrected this session** so a future redeploy won't silently revert to 5min |
| 2 | Hard circuit breaker at 95 sends | ✅ Implemented this session — `core/email/agentmail_quota.py` had only the 90-buffer check; added an independent, unconditional `DAILY_HARD_STOP = 95` check that fires even if `DAILY_BUFFER` is ever loosened. Tested: 94→95 blocked by the existing 90 buffer (normal path); hard stop verified to independently block at 95 even with the buffer artificially raised to 99. |
| 3 | Daily digest unchanged | ✅ Confirmed untouched — `deploy/agentmail-daily-digest.timer` still `OnCalendar=*-*-* 18:00:00 America/Denver`, once/day |

### Timer verification detail
- **Installed & live** (`~/.config/systemd/user/*.timer`, confirmed via `systemctl --user list-timers`): hale-email-responder, wind-email-responder, persona-email-responder, dani-email-responder, d2m-agentmail-bridge all firing every 15min.
- **Repo source** (`deploy/*.timer`): hale-email-responder, wind-email-responder, persona-email-responder, d2m-agentmail-bridge were still committed at `OnUnitActiveSec=5min` — corrected to 15min this session so the repo matches the live system and future deploys don't regress. (No `deploy/dani-email-responder.timer` exists in-repo; it's installed-only, already at 15min live.)

## Quota budget
- Working quota: **90/day** (buffer, existing behavior — first stop)
- Hard stop: **95/day** (new, unconditional — second stop)
- Absolute ceiling: **100/day** (free-tier hard cap) — leaves a **5-message emergency buffer** between the hard stop and the real wall
- Monthly: 2,800 buffer / 3,000 ceiling — unchanged

## Send-path coverage verification
Every AgentMail send in the codebase routes through `AgentMailClient.send_message()` (`core/email/agentmail_client.py`), which calls `check_and_record()` before any send. Confirmed callers: `d2m_agentmail_bridge.py`, `persona_email_responder.py`, `wind_email_responder.py`, `wf17_named_waivers.py` (→ used by `hale_email_responder.py` and `dani_email_responder.py` via `send_waived_client_email`), `cross_engine_mail.py`, `vendor_correspondence.py`, `rich_incident_email.py`, `agentmail_daily_digest.py`, `ci_probe_c2_fabric_roundtrip.py`. No path bypasses the guard.

## Not touched (per source doc)
- `agentmail-listener.service` — read-only WebSocket, no send quota impact
- Items 4–6 in the source doc (pause bridge/responders while away, drop buffer to 75) — proposed only, not adopted, Commander's call

## Next review
Monthly, in the Baldrige sweep (Sterling, A7).
