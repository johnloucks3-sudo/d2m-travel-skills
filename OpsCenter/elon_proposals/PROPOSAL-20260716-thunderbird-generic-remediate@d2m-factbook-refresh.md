Proposal generated and written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260716-thunderbird-generic-remediate@d2m-factbook-refresh.md`.

**Executive summary:**

The 6 auto-heals/week are caused by a **hardcoded 120-second timeout in the headless Claude spawn wrapper that ignores the caller's `timeout` parameter**. Every factbook refresh attempt times out at 120s (despite the script requesting 280s), exhausts retries, and exits non-zero. Watchdog restarts it, which briefly succeeds (likely from cache), then fails again when the next timer cycle fires.

The fix is surgical: make the spawn wrapper respect the caller's timeout parameter, clear Python bytecode cache, and restart. This is infrastructure-level work within Hale's authority—no Commander gate required.

Proposal structured for autonomous execution with concrete verification steps.

Thanks
