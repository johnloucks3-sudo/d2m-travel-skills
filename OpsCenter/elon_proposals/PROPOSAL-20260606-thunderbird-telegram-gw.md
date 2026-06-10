✅ **Proposal written.** I found the root cause: polling threads are crashing silently, and the main thread monitoring loop doesn't exit when all worker threads die. The service continues appearing "active" to systemd until an unhandled exception in the main loop itself, at which point watchdog restarts it. This repeats every 1-2 days.

**The fix:** Add a thread death detector that exits gracefully when all polling threads are dead for >2 minutes. This lets the watchdog do its job cleanly instead of waiting for a crash. Hale can apply this code change autonomously—it's pure reliability, no business logic change.

**24-hour validation plan included:** Monitor for heal count drop from 12/week to ≤2/week.

Proposal saved to: `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260606-thunderbird-telegram-gw.md`
