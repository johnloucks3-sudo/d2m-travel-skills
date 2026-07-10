**PROPOSAL COMPLETE** — `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260704-alsa-mic-restore.md`

---

## Summary (ELON)

**The problem:** Watchdog false positives. `alsa-mic-restore.service` is a **oneshot service** — it runs once at boot, completes successfully, and stays active indefinitely per design. The watchdog's logic (watch for crashes, restart failed services) is wrong for this service type. It's detecting normal oneshot behavior and calling unnecessary restarts.

**The fix:** Remove `alsa-mic-restore.service` from the watchdog baseline registry. A service that works correctly and by design doesn't need watchdog intervention.

**Why this is ELON's call:** Category error. The Wing is applying daemon-monitoring logic to a oneshot. First-principles fix: stop monitoring what doesn't need monitoring. Hale can execute autonomously.

**Next:** Proposal staged for Hale's review. She can apply Steps 1–3 immediately and verify via the 7-day audit log.

—2026-07-04 21:07 MT
