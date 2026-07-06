# Channel Routing Reference — Telegram vs AgentMail
*Built 2026-07-06 · Implements `docs/TELEGRAM_AGENTMAIL_ROE_20260706.md` · Engine: `core/email/channel_router.py`*

## Decision tree

```
New message to send
        │
        ▼
Is the recipient a named-waiver correspondent?
(config/wf17_named_waivers.json — Nancy Lyons, Kim Westbrook,
 Stefanie Burcham, Bryana Jarboe, Susan Loucks)
        │
   YES ─┼─────────────────────────────► AgentMail. Always. No exception.
        │                                Quota there is mission-critical —
        │                                internal chatter can't starve it.
   NO   │
        ▼
What kind of message is this?
        │
        ├─ notify / ack / status nudge / "look now"
        │       └─► Telegram. Push beats poll for a latency-sensitive gate.
        │
        ├─ proposal (ELON, staff paper, anything Commander re-reads)
        │       └─► AgentMail. Durable artifact.
        │
        ├─ research reply (Dembe, multi-source synthesis)
        │       └─► AgentMail. Durable artifact.
        │
        ├─ daily digest / summary
        │       └─► Telegram carries the summary; underlying items stay
        │           retrievable in the AgentMail log. The summary is a
        │           signal, not the artifact itself.
        │
        ├─ gate veto (auto-execute countdown, WF-17 hold, etc.)
        │       └─► BOTH channels, monitored simultaneously. A reply on
        │           either kills the timer — see confirmed_auto_execute.py.
        │
        └─ anything else (ad hoc)
                └─► Apply the dividing line directly: does the Commander
                    re-read this later (has_substance=True) → AgentMail.
                    Is it just a nudge (has_substance=False) → Telegram.
```

## Worked examples

| Scenario | Message type | Recipient | Channel | Why |
|---|---|---|---|---|
| "Hale here, sent a proposal to johnloucks3, executing in 5 min unless you object." | `notify` | — | Telegram | Notify-and-wait is always Telegram (Rule 2) — the proposal itself already lives in AgentMail; this is the pointer. |
| ELON's tech-adoption proposal, full writeup | `proposal` | — | AgentMail | Durable artifact the Commander re-reads (Rule 1). |
| Dembe's Iran/Hormuz research brief | `research_reply` | — | AgentMail | Multi-source synthesis, re-read material. |
| Morning brief summary ping | `daily_digest` | — | Telegram | Signal only; full brief content sourced from AgentMail log (Rule 4). |
| A live email exchange with Commander running long, Hale wants to move faster | ad hoc | — | Stays on AgentMail **unless** Hale explicitly says "continuing on Telegram" first | Rule 3 — one thread, one medium; handoff must be announced, never silent. |
| Auto-execute countdown on a code deploy | `gate_veto` | — | Both (Telegram notify + AgentMail notify), either reply kills it | Cross-channel veto fix — Dembe's finding that a "no" typed in the email thread must be as fast as a Telegram reply. |
| Any message to Nancy Lyons, Susan Loucks, etc. | any | named-waiver email | AgentMail (or d2mconcierge per their `send_channel`) | Rule 5 — never Telegram, regardless of message type. |

## Exception handling

- **Named-waiver senders never route through Telegram** — checked first, overrides every other rule. If `channel_router._is_named_waiver_recipient()` returns True, the function returns `"agentmail"` immediately regardless of `message_type` or `has_substance`.
- **Unknown/ad-hoc message types** fall back to the `has_substance` heuristic (Rule 1) rather than raising — `route_by_content_type("some_new_type", has_substance=True)` returns AgentMail.
- **Silent channel switches are anomalies, not just skipped.** `check_thread_handoff()` raises `SilentSwitchError` and logs an entry to `OpsCenter/state/channel_context_miss.json` (the numerator for the context-miss-rate metric) whenever a channel change happens without `handoff_announced=True`.
- **`gate_veto` is the one message type that returns two channels**, not one — callers (e.g. `confirmed_auto_execute.notify_and_wait`) must monitor both, not pick one.

## Metric

**Cross-channel context-miss rate** = `miss_events / total_messages`, tracked in `OpsCenter/state/channel_context_miss.json`. Target **<2%**. `channel_router.log_weekly_context_miss_metric()` appends a dated entry to `hale_decisions.md`; reviewed in the weekly Baldrige sweep.

## Tests

- `core/email/test_channel_router.py` — 10 test messages (5 Telegram-type, 5 AgentMail-type) + a silent-switch anomaly simulation. Run: `python3 core/email/test_channel_router.py`.
- `core/ops/test_confirmed_auto_execute_veto.py` — mocked verification that an email-thread reply kills the auto-execute timer exactly as fast as a Telegram reply. Run: `python3 core/ops/test_confirmed_auto_execute_veto.py`.
