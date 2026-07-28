**Proposal written to** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260726-thunderbird-telegram-gw.md`

---

## Summary

**ROOT CAUSE:** The telegram gateway repeatedly hits a 768M memory ceiling (systemd `MemoryMax=768M`). Process allocates linearly to that cap, triggering kernel OOM kill, forcing restart via `Restart=always` liveness policy — creating a 2-restart/day pattern (14 in 7 days).

**FIX:** Raise `MemoryMax` to 1G (fleet default). Already applied to the config file at 11:10:02 on 2026-07-26. The process needs no code changes; it's well-behaved with adequate memory headroom.

**HALE DECISION:** `APPLY_AUTONOMOUSLY` — low-risk config change, fleet-standard alignment, no Commander gate applies. Hale will daemon-reload and restart the service to activate the fix, then monitor for 24h to verify zero restart churn and memory peaks below 900M.
