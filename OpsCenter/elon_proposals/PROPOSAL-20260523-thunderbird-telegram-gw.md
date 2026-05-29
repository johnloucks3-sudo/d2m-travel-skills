✅ **PROPOSAL COMPLETE**

**Proposal written to:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260523-thunderbird-telegram-gw.md`

---

## EXECUTIVE SUMMARY

| Aspect | Finding |
|--------|---------|
| **Pattern** | 10 auto-heals in 7 days (service restarts) |
| **Not a code crash** | Service logs show WARNINGS, not exceptions |
| **Root cause** | Telegram API conflict: polling mode (`getUpdates`) + active webhook |
| **Source** | Likely manual webhook setup (possibly from Commander testing) never cleaned up |
| **Symptom** | Service logs spam "can't use getUpdates while webhook is active" every 2-3 seconds |
| **Result** | Watchdog triggers restarts on resource/timeout thresholds |

---

## ELON'S RECOMMENDATION

**Phase 1 (Today):** Run webhook cleanup script — delete webhooks from all 3 bot accounts via Telegram API. This is a config fix, not code, and safe to execute autonomously.

**Phase 2 (After 24h verification):** Add auto-cleanup code to gateway startup to prevent recurrence if webhooks are manually set up.

**Timeline:** 24h to verify Phase 1 works (logs should go clean immediately), then Phase 2 within 48h.

**Decision:** `APPLY_AUTONOMOUSLY` — this is infrastructure self-healing within Hale's authority band. No Commander gate needed.

Proposal details: root cause analysis, implementation steps, verification test, and kill audit summary are in the file above.
