# TELEGRAM 3-STRIKE PROTOCOL — HALE-YODA
## Standing Order 2026-05-16 | Thunderbird Wing, Dreams2Memories Travel, LLC

---

## DOCTRINE

**HALE-YODA is Commander's direct line to Hale.** It is exclusive — Commander ↔ Hale ONLY. The D2MC2C bot handle is dedicated to this channel.

After **3 failed production deployment attempts**, HALE-YODA migrates to Signal. Signal is the fallback of last resort — it has no Bot API, no rich graphics, and no approval flows. Migration is a regression, not a preference.

**A strike = one failed production deployment attempt.** Not a crash. Not a monitoring event. Not a DNS blip. A strike is: "I deployed the gateway, it was live in production, and it failed to deliver the core function (Commander message → Hale response)."

---

## STRIKE COUNTER

Strike state is tracked in `OpsCenter/telegram_strike_counter.json`:

```json
{
  "strikes": 0,
  "history": [
    {
      "ts": "ISO-8601",
      "description": "What failed",
      "diagnosis": "Root cause",
      "cleared": false
    }
  ],
  "signal_migration_triggered": false
}
```

**Strike recorded by:** `thunderbird_telegram_webhook.py` → `record_strike(description, diagnosis)`
**Strike cleared by:** Commander manual reset (never auto-reset — strikes are durable)

---

## WHAT TRIGGERS A STRIKE

| Event | Strike? |
|---|---|
| Webhook gateway deployed → Commander sends message → no response received | ✅ YES |
| Gateway crashes repeatedly (>10 restarts/hour) without serving messages | ✅ YES |
| Cloudflare tunnel down for >30 min during active session | ✅ YES |
| DNS failure causing >30 min message loss | ✅ YES |
| Code deploy fails to start (import error, port conflict) | ❌ NO — not a production failure |
| Temporary Telegram API outage (<30 min) | ❌ NO — Telegram-side, not D2M-side |
| Single message timeout | ❌ NO — transient |
| Commander tests and gets slow response | ❌ NO — not a failure |

**Rule of thumb:** If Commander had to send the same message again because nothing happened, that's a strike candidate.

---

## SIGNAL MIGRATION PROTOCOL (Strike 3)

When `get_strike_count() >= 3`:

1. **`thunderbird_telegram_webhook.py` detects** the third strike at startup
2. **Hale logs to `hale_decisions.md`**: "HALE-YODA strike limit reached — Signal migration triggered"
3. **Hale sends final message to Commander on HALE-YODA**: "Strike 3 reached. Migrating to Signal. This is the last HALE-YODA message."
4. **Gateway disables HALE-YODA processing** (returns 200 to Telegram but does not respond)
5. **Commander sets up Signal contact** manually — Signal does not have a Bot API equivalent

**What stays on Telegram after migration:**
- HALE_D2M staff channel — stays. Staff still communicate here.
- d2m_channels infra pushes — stays.
- Only HALE-YODA (Commander↔Hale exclusive) migrates.

---

## STRIKE MANAGEMENT COMMANDS

From within the gateway (internal admin only):

```python
# Check current strike count
from OpsCenter.thunderbird_telegram_webhook import get_strike_count, record_strike, clear_strikes

count = get_strike_count()    # returns int
record_strike("Gateway deployed but Commander messages not delivered", "Port conflict with old service")
clear_strikes()               # Commander-only reset — logs the clear event
```

Strike counter file path: `/home/john/Thunderbird/OpsCenter/telegram_strike_counter.json`

---

## CURRENT STATUS

| Metric | Value |
|---|---|
| Strikes recorded | 0 |
| Signal migration triggered | No |
| Gateway mode | Webhook (v1.0 — 2026-05-16) |
| Previous mode | Long-polling (deprecated) |

---

*Standing Order 2026-05-16 | Col Victoria "Iron Vic" Hale, COS | Thunderbird Wing*
