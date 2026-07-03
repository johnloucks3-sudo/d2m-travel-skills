The proposal file already exists at that path — authored earlier at 09:19 MT, same analysis I would have written. My independent investigation confirms its core findings:

- **Root cause verified in `overwatch.log`:** `KeyError: 'opencode'` at `core/watchtower/thunderbird_tasking_watcher.py:1208` — matches obs #439 filed today.
- **Current state verified:** Service is `active (running)` since 09:18:44 MDT under the `_fixed.py` stub (100-line file-change logger, no routing logic). Unit is no longer masked; auto_heal_succeeded=false in the event was stale.
- **Recommendation stands: RETIRE.** brain_bridge + `opencode-worker.service` own the routing function. The running stub is theater.

The one delta from my draft: the existing proposal correctly flags **QUEUE_FOR_COMMANDER** (not APPLY_AUTONOMOUSLY) because of the potential prod-timer gap (90s unclaimed → Telegram nudge) that needs verification before retirement. That's the better call — it belongs on Commander's desk, and it's already surfaced in today's `hale_brief.md`.

No overwrite needed. Proposal is durable, sound, and already in Hale's brief. Done.
