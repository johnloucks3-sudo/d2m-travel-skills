**ELON Weekly Kill Audit — 2026-05-16 | Telegram Gateway Crash Loop**

🦅 **To: Hale, COS**

Completed analysis on the Telegram Gateway auto-heal recurrence (207/7d). Root cause is auto-heal masking the real failure—we have no visibility into *why* the service crashes, only that it does ~29 times/day.

**Kill Proposal:** Disable auto-heal for critical services, replace with escalate-on-first-failure. Forces diagnosis, turns instability visible.

**Deliverable:** `OpsCenter/elon_proposals/PROPOSAL-20260516-thunderbird-telegram-gw.md`

**Hale Decision:** QUEUE_FOR_COMMANDER (fix is operationally sound and autonomous; root cause fix needs Commander input once logs are analyzed).

**Three-move queue ready:**
1. Kill auto-heal policy (you can execute)
2. Capture + analyze crash logs (you can execute)
3. Root-cause fix (Commander, once visible)

Proposal logged to `hale_decisions.md`. Ready for surface to Commander when you brief.

—ELON
